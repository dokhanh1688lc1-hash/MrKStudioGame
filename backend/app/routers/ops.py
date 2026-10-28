from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import utcnow
from ..deps import Principal, current_user, get_db, require
from ..models import (Agent, Approval, CeoReview, AuditLog, Budget, Department, Project, ProviderConfig, Task, UsageRecord)
from ..schemas import (ApprovalIn, ApprovalOut, AuditOut, BudgetIn, BudgetOut, DecisionIn, ProviderOut,
                       ProviderPatch, SettingsPatch, StopIn, UsageOut)
from ..services.budget import spent
from ..services.common import audit, get_bool, get_setting, set_setting
from ..services.orchestrator import plan_route
from ..services import backup as bk
from ..services.common import EngineError

router = APIRouter(prefix="/api", tags=["ops"])


# ---------- providers ----------
def _prov_out(request: Request, c: ProviderConfig) -> ProviderOut:
    p = request.app.state.registry.get(c.name)
    return ProviderOut(name=c.name, kind="internal" if c.name == "internal" else "cli", enabled=c.enabled,
                       configured=p.configured(), program_path=p.masked_key(), default_model=c.default_model,
                       allow_sensitive=c.allow_sensitive, last_check_status=c.last_check_status,
                       last_check_message=c.last_check_message, last_check_at=c.last_check_at)


@router.get("/providers", response_model=list[ProviderOut])
def providers(request: Request, _: Principal = Depends(current_user), s: Session = Depends(get_db)):
    return [_prov_out(request, c) for c in s.scalars(select(ProviderConfig).order_by(ProviderConfig.id))
            if c.name in request.app.state.registry.names()]


@router.patch("/providers/{name}", response_model=ProviderOut)
def patch_provider(name: str, body: ProviderPatch, request: Request, user: Principal = Depends(require("owner")),
                   s: Session = Depends(get_db)):
    c = s.scalar(select(ProviderConfig).where(ProviderConfig.name == name))
    if not c:
        raise HTTPException(404, "Không tìm thấy provider.")
    if name not in request.app.state.registry.names():
        raise HTTPException(404, "Không tìm thấy provider.")
    if name == "internal" and body.model_dump(exclude_unset=True).keys() - {"enabled"}:
        raise HTTPException(422, "Chế độ nội bộ chỉ có thể bật/tắt.")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    audit(s, user.username, "provider_updated", "provider", name, ", ".join(body.model_dump(exclude_unset=True)))
    s.commit()
    return _prov_out(request, c)


@router.post("/providers/{name}/check", response_model=ProviderOut)
def check_provider(name: str, request: Request, user: Principal = Depends(require("manager")),
                   s: Session = Depends(get_db)):
    c = s.scalar(select(ProviderConfig).where(ProviderConfig.name == name))
    if not c:
        raise HTTPException(404, "Không tìm thấy provider.")
    ok, msg = request.app.state.registry.get(name).check()
    c.last_check_status, c.last_check_message, c.last_check_at = ("ok" if ok else "failed"), msg, utcnow()
    audit(s, user.username, "provider_checked", "provider", name, c.last_check_status)
    s.commit()
    return _prov_out(request, c)


@router.get("/routing/preview")
def routing_preview(department: str, provider: str | None = None, sensitive: bool = False, request: Request = None,
                    _: Principal = Depends(current_user), s: Session = Depends(get_db)):
    try:
        chain, reason = plan_route(s, request.app.state.registry, department_key=department, provider=provider,
                                   model=None, sensitive=sensitive)
    except EngineError as e:
        raise HTTPException(e.status, e.message)
    return {"chain": [{"provider": p, "model": m} for p, m in chain], "reason": reason}


# ---------- approvals ----------
@router.get("/approvals")
def approvals(status: str = "", limit: int = Query(50, ge=1, le=200), _: Principal = Depends(current_user),
              s: Session = Depends(get_db)):
    q = select(Approval).order_by(Approval.id.desc()).limit(limit)
    if status:
        q = q.where(Approval.status == status)
    return [ApprovalOut.model_validate(a) for a in s.scalars(q)]


@router.post("/approvals", response_model=ApprovalOut, status_code=201)
def create_approval(body: ApprovalIn, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    a = Approval(**body.model_dump())
    s.add(a)
    s.flush()
    audit(s, user.username, "approval_requested", "approval", a.id, a.kind)
    s.commit()
    return a


@router.post("/approvals/{aid}/decision", response_model=ApprovalOut)
def decide(aid: int, body: DecisionIn, user: Principal = Depends(require("owner")), s: Session = Depends(get_db)):
    a = s.get(Approval, aid)
    if not a:
        raise HTTPException(404, "Không tìm thấy yêu cầu phê duyệt.")
    if a.status != "pending":
        raise HTTPException(409, "Yêu cầu đã được xử lý.")
    a.status = "approved" if body.approve else "rejected"
    a.decided_by, a.decided_at = user.username, utcnow()
    if a.task_id:
        t = s.get(Task, a.task_id)
        if t and t.status == "Awaiting Approval":
            t.status = "Assigned" if body.approve else "Cancelled"
            if not body.approve:
                t.error, t.finished_at = "Bị từ chối phê duyệt.", utcnow()
    audit(s, user.username, f"approval_{a.status}", "approval", a.id, a.title)
    s.commit()
    return a


# ---------- budgets / usage ----------
@router.get("/budgets")
def budgets(_: Principal = Depends(current_user), s: Session = Depends(get_db)):
    out = []
    for b in s.scalars(select(Budget).order_by(Budget.id)):
        used = spent(s, b.scope, b.scope_key or "0", b.period)
        out.append({**BudgetOut.model_validate(b).model_dump(), "used_runs": used,
                    "ratio": used / b.limit_runs})
    return out


@router.post("/budgets", response_model=BudgetOut, status_code=201)
def create_budget(body: BudgetIn, user: Principal = Depends(require("owner")), s: Session = Depends(get_db)):
    if body.scope in ("project", "task"):
        if not body.scope_key.isdigit():
            raise HTTPException(422, "scope_key phải là ID số cho phạm vi project/task.")
        if body.scope == "project" and not s.get(Project, int(body.scope_key)):
            raise HTTPException(422, "Dự án không tồn tại.")
    elif body.scope != "studio" and not body.scope_key:
        raise HTTPException(422, "Thiếu scope_key.")
    key = "" if body.scope == "studio" else body.scope_key
    b = Budget(**{**body.model_dump(), "scope_key": key})
    s.add(b)
    try:
        s.flush()
    except IntegrityError:
        s.rollback()
        raise HTTPException(409, "Ngân sách cho phạm vi/kỳ này đã tồn tại.")
    audit(s, user.username, "budget_created", "budget", b.id, f"{b.scope}/{b.scope_key}/{b.period}={b.limit_runs}")
    s.commit()
    return b


@router.delete("/budgets/{bid}", status_code=204)
def delete_budget(bid: int, user: Principal = Depends(require("owner")), s: Session = Depends(get_db)):
    b = s.get(Budget, bid)
    if not b:
        raise HTTPException(404, "Không tìm thấy ngân sách.")
    audit(s, user.username, "budget_deleted", "budget", bid, f"{b.scope}/{b.scope_key}/{b.period}")
    s.delete(b)
    s.commit()


@router.get("/usage", response_model=list[UsageOut])
def usage(limit: int = Query(50, ge=1, le=500), _: Principal = Depends(current_user), s: Session = Depends(get_db)):
    return s.scalars(select(UsageRecord).order_by(UsageRecord.id.desc()).limit(limit)).all()


# ---------- audit / system ----------
@router.get("/audit")
def audit_logs(action: str = "", limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
               _: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    where = [AuditLog.action == action] if action else []
    total = s.scalar(select(func.count()).select_from(AuditLog).where(*where))
    rows = s.scalars(select(AuditLog).where(*where).order_by(AuditLog.id.desc()).limit(limit).offset(offset)).all()
    return {"items": [AuditOut.model_validate(r) for r in rows], "total": total}


def _system_state(s: Session) -> dict:
    return {"emergency_stop": get_bool(s, "emergency_stop"), "fallback_enabled": get_bool(s, "fallback_enabled")}


@router.get("/system/state")
def system_state(_: Principal = Depends(current_user), s: Session = Depends(get_db)):
    return _system_state(s)


@router.post("/system/emergency-stop")
def emergency_stop(body: StopIn, request: Request, user: Principal = Depends(require("owner")),
                   s: Session = Depends(get_db)):
    n = request.app.state.orch.emergency_stop(body.active, user.username)
    s.expire_all()
    return {**_system_state(s), "tasks_stopped": n}


@router.patch("/system/settings")
def patch_settings(body: SettingsPatch, user: Principal = Depends(require("owner")), s: Session = Depends(get_db)):
    d = body.model_dump(exclude_unset=True)
    if "fallback_enabled" in d and d["fallback_enabled"] is not None:
        set_setting(s, "fallback_enabled", "1" if d["fallback_enabled"] else "0")
    audit(s, user.username, "settings_changed", "system", "", ", ".join(d))
    s.commit()
    return _system_state(s)


@router.get("/dashboard")
def dashboard(request: Request, _: Principal = Depends(current_user), s: Session = Depends(get_db)):
    by_status = dict(s.execute(select(Task.status, func.count()).group_by(Task.status)).all())
    projects = dict(s.execute(select(Project.status, func.count()).group_by(Project.status)).all())
    provs = [_prov_out(request, c) for c in s.scalars(select(ProviderConfig))]
    return {
        "projects_total": sum(projects.values()), "projects_by_status": projects,
        "tasks_total": sum(by_status.values()), "tasks_by_status": by_status,
        "ceo_pending": s.scalar(select(func.count()).select_from(Task).outerjoin(CeoReview, CeoReview.task_id == Task.id).where(Task.status.in_(("Completed", "Failed")), Task.department_key != "ceo", CeoReview.id.is_(None))),
        "pending_approvals": s.scalar(select(func.count()).select_from(Approval).where(Approval.status == "pending")),
        "runs_today": spent(s, "studio", "", "daily"), "runs_month": spent(s, "studio", "", "monthly"),
        "providers": [{"name": p.name, "configured": p.configured, "enabled": p.enabled,
                       "last_check_status": p.last_check_status} for p in provs],
        "system": _system_state(s),
    }


@router.get("/office")
def office(_: Principal = Depends(current_user), s: Session = Depends(get_db)):
    """Trạng thái từng phòng ban cho màn hình 'Văn phòng studio' (cập nhật theo thời gian thực)."""
    counts: dict[str, dict[str, int]] = {}
    for dk, st, n in s.execute(select(Task.department_key, Task.status, func.count()).group_by(Task.department_key, Task.status)):
        counts.setdefault(dk, {})[st] = n
    running = {}
    for t in s.scalars(select(Task).where(Task.status == "Running").order_by(Task.id)):
        running.setdefault(t.department_key, t.title)
    out = []
    for d in s.scalars(select(Department).order_by(Department.id)):
        c = counts.get(d.key, {})
        agents = s.scalar(select(func.count()).select_from(Agent).where(Agent.department_id == d.id, Agent.enabled.is_(True))) or 0
        out.append({"key": d.key, "name": d.name, "description": d.description, "family": d.preferred_provider,
                    "agents": agents, "running_title": running.get(d.key, ""),
                    "running": c.get("Running", 0),
                    "waiting": c.get("Awaiting Approval", 0) + c.get("Blocked", 0),
                    "queued": c.get("Assigned", 0) + c.get("Planned", 0) + c.get("Pending", 0),
                    "done": c.get("Completed", 0), "failed": c.get("Failed", 0)})
    return out


@router.get("/system/backups")
def backups(request: Request, _: Principal = Depends(require("owner"))):
    return bk.list_backups(request.app.state.settings.data_dir)


@router.post("/system/backups", status_code=201)
def make_backup(request: Request, user: Principal = Depends(require("owner")), s: Session = Depends(get_db)):
    try:
        res = bk.create_backup(request.app.state.engine, request.app.state.settings.data_dir)
    except EngineError as e:
        raise HTTPException(e.status, e.message)
    audit(s, user.username, "backup_created", "system", "", res["name"])
    s.commit()
    return res
