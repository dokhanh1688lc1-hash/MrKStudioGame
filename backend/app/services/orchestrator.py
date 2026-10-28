"""AI Orchestrator: định tuyến provider, kiểm soát ngân sách/phê duyệt, chạy nhiệm vụ bền vững.

Nguyên tắc: không lưu chain-of-thought; không retry vô hạn; không tự gọi API khi vượt ngân sách,
khi Emergency Stop đang bật hoặc khi chưa được phê duyệt.
"""
from __future__ import annotations

import threading
import time

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from ..db import utcnow
from ..models import (Agent, Approval, Department, ProviderConfig, Task, TaskAttempt,
                      TaskDependency, UsageRecord)
from ..providers.base import ProviderError
from ..providers.registry import FAMILY_TO_PROVIDER, ProviderRegistry
from .budget import check_limits
from . import lessons as lessons_svc
from .common import EngineError, audit, get_bool, get_setting, set_setting

RUNNABLE = {"Pending", "Planned", "Assigned", "Blocked", "Failed"}
FINAL = {"Completed", "Cancelled"}


MAX_UPSTREAM_CHARS = 6000


def upstream_results(s: Session, t: Task) -> list[tuple[str, str]]:
    """Kết quả (đã hoàn thành) của các nhiệm vụ phụ thuộc, để truyền sang bước sau."""
    out = []
    for d in s.scalars(select(TaskDependency).where(TaskDependency.task_id == t.id)):
        dt = s.get(Task, d.depends_on_id)
        if dt and dt.status == "Completed" and dt.result:
            out.append((dt.title, dt.result[:MAX_UPSTREAM_CHARS]))
    return out


def build_prompt(t: Task, upstream: list[tuple[str, str]] | None = None, lessons: list[str] | None = None) -> str:
    parts = [f"# Nhiệm vụ: {t.title}", f"## Mục tiêu\n{t.objective}"]
    if lessons:
        parts.append("## Bài học của phòng ban (chủ studio đã duyệt — hãy tuân thủ)\n" + "\n".join(f"- {x}" for x in lessons))
    for title, res in upstream or []:
        parts.append(f"## Kết quả từ bước trước: {title}\n{res}")
    for label, val in (("Bối cảnh / đầu vào", t.context), ("Ràng buộc", t.constraints),
                       ("Đầu ra mong đợi", t.expected_output), ("Tiêu chí nghiệm thu", t.acceptance_criteria)):
        if val.strip():
            parts.append(f"## {label}\n{val}")
    return "\n\n".join(parts)


def plan_route(s: Session, registry: ProviderRegistry, *, department_key: str, provider: str | None,
               model: str | None, sensitive: bool) -> tuple[list[tuple[str, str]], str]:
    """Trả về (chuỗi [(provider, model)], lý do định tuyến). Chỉ dùng chương trình trên máy hoặc chế độ nội bộ."""
    cfgs = {c.name: c for c in s.scalars(select(ProviderConfig)) if c.name in registry.names()}
    provider = FAMILY_TO_PROVIDER.get(provider or "", provider)  # nhiệm vụ cũ lưu 'openai'/'anthropic'

    def usable(name: str) -> tuple[bool, str]:
        c, p = cfgs.get(name), registry.get(name)
        if c is None or not c.enabled:
            return False, f"provider '{name}' đang tắt"
        if not p.configured():
            return False, f"provider '{name}' chưa cài/không tìm thấy chương trình trên máy"
        if sensitive and not c.allow_sensitive:
            return False, f"provider '{name}' chưa được cấp quyền nhận dữ liệu nhạy cảm"
        return True, ""

    def model_of(name: str) -> str:
        return (model if provider == name and model else cfgs[name].default_model) or ""

    if provider:  # chỉ định rõ → không âm thầm đổi provider
        if provider not in cfgs:
            raise EngineError(422, f"Provider không tồn tại: {provider}")
        if provider == "internal":
            return [("internal", "internal")], "chỉ định chế độ nội bộ"
        ok, why = usable(provider)
        if not ok:
            raise EngineError(422, f"Không thể dùng provider đã chỉ định: {why}.")
        return [(provider, model_of(provider))], f"chỉ định {provider}"

    dept = s.scalar(select(Department).where(Department.key == department_key))
    pref = dept.preferred_provider if dept else "openai"
    other = "anthropic" if pref == "openai" else "openai"
    order = [FAMILY_TO_PROVIDER[pref], FAMILY_TO_PROVIDER[other]]
    good = [n for n in order if n in cfgs and usable(n)[0]]
    if not good:
        return [("internal", "internal")], "không có chương trình AI nào khả dụng trên máy → chế độ nội bộ (không gọi AI)"
    chain = [(n, model_of(n)) for n in good]
    if not get_bool(s, "fallback_enabled"):
        chain = chain[:1]
    reason = f"phòng ban ưu tiên {FAMILY_TO_PROVIDER[pref]}" + ("" if good[0] == order[0] else f"; {order[0]} không khả dụng nên dùng {good[0]}")
    return chain, reason


class Orchestrator:
    def __init__(self, session_factory: sessionmaker, registry: ProviderRegistry, retry_delay: float = 1.0):
        self.sf = session_factory
        self.registry = registry
        self.retry_delay = retry_delay

    # ---------- chuẩn bị (đồng bộ, trả lỗi ngay cho người dùng) ----------
    def prepare_run(self, task_id: int, actor: str) -> list[tuple[str, str]]:
        with self.sf() as s:
            t = s.get(Task, task_id)
            if not t:
                raise EngineError(404, "Không tìm thấy nhiệm vụ.")
            if get_bool(s, "emergency_stop"):
                raise EngineError(423, "Emergency Stop đang bật. Tắt trước khi chạy nhiệm vụ.")
            if t.status == "Running":
                raise EngineError(409, "Nhiệm vụ đang chạy (chống chạy trùng).")
            if t.status not in RUNNABLE:
                raise EngineError(409, f"Không thể chạy nhiệm vụ ở trạng thái '{t.status}'.")

            unmet = [d.depends_on_id for d in s.scalars(select(TaskDependency).where(TaskDependency.task_id == t.id))
                     if s.get(Task, d.depends_on_id).status != "Completed"]
            if unmet:
                t.status, t.error = "Blocked", f"Đang chờ nhiệm vụ phụ thuộc hoàn thành: {unmet}"
                s.commit()
                raise EngineError(409, t.error)

            chain, reason = plan_route(s, self.registry, department_key=t.department_key,
                                       provider=t.provider, model=t.model, sensitive=t.sensitive)
            primary, model = chain[0]

            if t.requires_approval:
                appr = s.scalar(select(Approval).where(Approval.task_id == t.id, Approval.kind == "task_run")
                                .order_by(Approval.id.desc()))
                if not (appr and appr.status == "approved"):
                    t.status = "Awaiting Approval"
                    if not appr or appr.status != "pending":
                        s.add(Approval(kind="task_run", task_id=t.id, title=f"Chạy nhiệm vụ #{t.id}: {t.title}",
                                       detail=f"Provider: {primary}/{model}."))
                        audit(s, actor, "approval_requested", "task", t.id)
                    s.commit()
                    raise EngineError(409, "Nhiệm vụ cần phê duyệt trước khi chạy. Xem Approval Center.")

            v = check_limits(s, project_id=t.project_id, department_key=t.department_key, provider=primary,
                             model=model, task_id=t.id)
            if not v.ok:
                t.status, t.error = "Blocked", v.message
                audit(s, actor, "task_blocked_budget", "task", t.id, v.message)
                s.commit()
                raise EngineError(402, v.message)

            res = s.execute(update(Task).where(Task.id == t.id, Task.status.in_(RUNNABLE))
                            .values(status="Running", error=None, started_at=utcnow(), finished_at=None))
            if res.rowcount == 0:
                raise EngineError(409, "Nhiệm vụ vừa được chạy bởi tiến trình khác.")
            audit(s, actor, "task_run_started", "task", t.id, f"{primary}/{model} — {reason}")
            s.commit()
            return chain

    # ---------- thực thi ----------
    def _status(self, s: Session, task_id: int) -> str:
        s.expire_all()
        return s.scalar(select(Task.status).where(Task.id == task_id))

    def execute_run(self, task_id: int, chain: list[tuple[str, str]], actor: str) -> None:
        try:
            self._execute(task_id, chain, actor)
        except Exception as e:  # không để nhiệm vụ kẹt ở Running
            with self.sf() as s:
                t = s.get(Task, task_id)
                if t and t.status == "Running":
                    t.status, t.error, t.finished_at = "Failed", f"Lỗi nội bộ: {type(e).__name__}: {e}", utcnow()
                    s.commit()

    def _execute(self, task_id: int, chain: list[tuple[str, str]], actor: str) -> None:
        with self.sf() as s:
            t = s.get(Task, task_id)
            agent = s.get(Agent, t.agent_id) if t.agent_id else None
            system = agent.system_prompt if agent else ""
            prompt = build_prompt(t, upstream_results(s, t), lessons_svc.texts_and_mark_used(s, t.department_key, t.project_id))
            last_error, first = "Không có lần gọi nào được thực hiện.", True

            for pname, model in chain:
                prov = self.registry.get(pname)
                for n in range(t.max_retries + 1):
                    if self._status(s, task_id) != "Running" or get_bool(s, "emergency_stop"):
                        return self._abort(task_id)
                    if not first:
                        v = check_limits(s, project_id=t.project_id, department_key=t.department_key,
                                         provider=pname, model=model, task_id=t.id)
                        if not v.ok:
                            return self._fail(s, t, v.message)
                        time.sleep(self.retry_delay * n)
                    first = False

                    att = TaskAttempt(task_id=t.id, provider=pname, model=model)
                    s.add(att)
                    t.attempts_made += 1
                    s.commit()
                    try:
                        res = prov.complete(system=system, prompt=prompt, model=model,
                                            max_tokens=t.max_output_tokens,
                                            timeout=max(t.timeout_s, 180) if getattr(prov, "subscription", False) else t.timeout_s)
                    except ProviderError as e:
                        att.status, att.error, att.finished_at = "error", str(e), utcnow()
                        last_error = f"{pname}: {e}"
                        s.commit()
                        if e.retryable:
                            continue
                        break
                    except Exception as e:  # noqa: BLE001
                        att.status, att.error, att.finished_at = "error", f"{type(e).__name__}", utcnow()
                        last_error = f"{pname}: lỗi không mong đợi ({type(e).__name__})"
                        s.commit()
                        break

                    att.status, att.finished_at = "ok", utcnow()
                    att.input_tokens, att.output_tokens = res.input_tokens, res.output_tokens
                    s.add(UsageRecord(task_id=t.id, project_id=t.project_id, department_key=t.department_key,
                                      provider=pname, model=model, input_tokens=res.input_tokens,
                                      output_tokens=res.output_tokens))
                    s.commit()
                    if self._status(s, task_id) != "Running" or get_bool(s, "emergency_stop"):
                        return self._abort(task_id)
                    t = s.get(Task, task_id)
                    t.status, t.result, t.result_source = "Completed", res.text, pname
                    t.error, t.finished_at = None, utcnow()
                    audit(s, actor, "task_completed", "task", t.id, f"{pname}/{model}")
                    s.commit()
                    return
            self._fail(s, t, last_error)

    def _fail(self, s: Session, t: Task, msg: str) -> None:
        s.expire_all()
        t = s.get(Task, t.id)
        if t.status == "Running":
            t.status, t.error, t.finished_at = "Failed", msg, utcnow()
            audit(s, "system", "task_failed", "task", t.id, msg)
            s.commit()

    def _abort(self, task_id: int) -> None:
        with self.sf() as s:
            t = s.get(Task, task_id)
            if t.status == "Running":
                t.status, t.error, t.finished_at = "Cancelled", "Bị dừng (Emergency Stop).", utcnow()
                s.commit()

    def run_async(self, task_id: int, chain, actor: str) -> None:
        threading.Thread(target=self.execute_run, args=(task_id, chain, actor), daemon=True).start()

    # ---------- hủy / dừng khẩn cấp ----------
    def cancel(self, task_id: int, actor: str) -> Task:
        with self.sf() as s:
            t = s.get(Task, task_id)
            if not t:
                raise EngineError(404, "Không tìm thấy nhiệm vụ.")
            if t.status in FINAL:
                raise EngineError(409, f"Nhiệm vụ đã ở trạng thái '{t.status}'.")
            t.status, t.finished_at = "Cancelled", utcnow()
            t.error = "Đã hủy bởi người dùng."
            for a in s.scalars(select(Approval).where(Approval.task_id == t.id, Approval.status == "pending")):
                a.status, a.decided_by, a.decided_at = "rejected", actor, utcnow()
            audit(s, actor, "task_cancelled", "task", t.id)
            s.commit()
            return t

    def emergency_stop(self, active: bool, actor: str) -> int:
        with self.sf() as s:
            set_setting(s, "emergency_stop", "1" if active else "0")
            n = 0
            if active:
                for t in s.scalars(select(Task).where(Task.status == "Running")):
                    t.status, t.error, t.finished_at = "Cancelled", "Bị dừng (Emergency Stop).", utcnow()
                    n += 1
            audit(s, actor, "emergency_stop_on" if active else "emergency_stop_off", "system", "", f"tasks_stopped={n}")
            s.commit()
            return n
