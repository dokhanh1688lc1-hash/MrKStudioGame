from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..deps import Principal, current_user, get_db, require
from ..models import Agent, CeoReview, Department, Project, Task, TaskDependency
from ..services.common import audit, get_bool

router = APIRouter(prefix="/api/ceo", tags=["ceo"])
EXCERPT = 700
DIGEST_MAX_ITEMS = 15
DIGEST_ITEM_CHARS = 1200
REPORTABLE = ("Completed", "Failed")


class DecideIn(BaseModel):
    decision: Literal["accepted", "rework", "forward", "dismissed"]
    note: str = Field(default="", max_length=4000)
    target_department: str = ""


def _pending_q():
    """Nhiệm vụ đã xong/thất bại của các phòng ban (trừ chính CEO) mà CEO chưa quyết định."""
    return (select(Task).outerjoin(CeoReview, CeoReview.task_id == Task.id)
            .where(Task.status.in_(REPORTABLE), Task.department_key != "ceo", CeoReview.id.is_(None)))


def _item(s: Session, t: Task, r: CeoReview | None) -> dict:
    p = s.get(Project, t.project_id)
    dept = s.scalar(select(Department).where(Department.key == t.department_key))
    text = t.result or t.error or ""
    return {"task_id": t.id, "title": t.title, "status": t.status, "department_key": t.department_key,
            "department": dept.name if dept else t.department_key, "project_id": t.project_id,
            "project": p.name if p else "", "source": t.result_source, "excerpt": text[:EXCERPT],
            "truncated": len(text) > EXCERPT, "finished_at": t.finished_at,
            "decision": r.decision if r else None, "note": r.note if r else "",
            "followup_task_id": r.followup_task_id if r else None,
            "decided_by": r.decided_by if r else None, "decided_at": r.decided_at if r else None}


@router.get("/inbox")
def inbox(view: Literal["pending", "decided"] = "pending", limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0),
          _: Principal = Depends(current_user), s: Session = Depends(get_db)):
    pending_n = s.scalar(select(func.count()).select_from(_pending_q().subquery()))
    if view == "pending":
        rows = s.scalars(_pending_q().order_by(Task.finished_at.desc().nullslast(), Task.id.desc()).limit(limit).offset(offset)).all()
        items = [_item(s, t, None) for t in rows]
    else:
        q = (select(Task, CeoReview).join(CeoReview, CeoReview.task_id == Task.id)
             .order_by(CeoReview.decided_at.desc()).limit(limit).offset(offset))
        items = [_item(s, t, r) for t, r in s.execute(q).all()]
    return {"pending": pending_n, "items": items}


def _agent(s: Session, dept_key: str) -> tuple[Department, Agent]:
    dept = s.scalar(select(Department).where(Department.key == dept_key))
    if not dept:
        raise HTTPException(422, f"Phòng ban không tồn tại: {dept_key}")
    agent = s.scalar(select(Agent).where(Agent.department_id == dept.id, Agent.enabled.is_(True)).order_by(Agent.id))
    if not agent:
        raise HTTPException(409, f"Phòng ban '{dept.name}' chưa có agent nào được bật.")
    return dept, agent


@router.post("/tasks/{tid}/decide", status_code=201)
def decide(tid: int, body: DecideIn, user: Principal = Depends(require("owner")), s: Session = Depends(get_db)):
    t = s.get(Task, tid)
    if not t or t.status not in REPORTABLE or t.department_key == "ceo":
        raise HTTPException(404, "Không có nhiệm vụ này trong hộp thư CEO.")
    if s.scalar(select(CeoReview).where(CeoReview.task_id == tid)):
        raise HTTPException(409, "CEO đã quyết định về nhiệm vụ này.")
    p = s.get(Project, t.project_id)
    note = body.note.strip()
    follow: Task | None = None
    if body.decision in ("rework", "forward") and p and p.status == "Archived":
        raise HTTPException(409, "Dự án đã lưu trữ (Archived).")
    if body.decision == "rework":
        if not note:
            raise HTTPException(422, "Hãy ghi rõ cần sửa gì (phản hồi của CEO).")
        _, agent = _agent(s, t.department_key)
        follow = Task(project_id=t.project_id, department_key=t.department_key, agent_id=agent.id, status="Assigned",
                      title=f"Sửa lại: {t.title}"[:200],
                      objective=f"{t.objective}\n\nPHẢN HỒI CỦA CEO — hãy sửa theo các điểm sau:\n{note}",
                      context=t.context, constraints=t.constraints, expected_output=t.expected_output,
                      acceptance_criteria=t.acceptance_criteria, provider=t.provider, model=t.model, sensitive=t.sensitive,
                      max_output_tokens=t.max_output_tokens, timeout_s=t.timeout_s, max_retries=t.max_retries)
    elif body.decision == "forward":
        if not body.target_department:
            raise HTTPException(422, "Chọn phòng ban nhận việc.")
        dept, agent = _agent(s, body.target_department)
        src = s.scalar(select(Department).where(Department.key == t.department_key))
        follow = Task(project_id=t.project_id, department_key=dept.key, agent_id=agent.id, status="Assigned",
                      title=f"Tiếp nhận từ {src.name if src else t.department_key}: {t.title}"[:200],
                      objective=note or f"Tiếp nhận kết quả của nhiệm vụ “{t.title}” và thực hiện phần việc của phòng bạn (vận hành, kiểm thử, phát hành, sửa chữa…).",
                      sensitive=t.sensitive,
                      expected_output="Kết quả hành động rõ ràng kèm các bước tiếp theo.",
                      acceptance_criteria="Dựa đúng vào kết quả bước trước; nêu rõ phần nào còn thiếu thông tin.")
    if follow:
        s.add(follow)
        s.flush()
        s.add(TaskDependency(task_id=follow.id, depends_on_id=t.id))  # kết quả bước trước tự động chuyển sang
    r = CeoReview(task_id=t.id, decision=body.decision, note=note, followup_task_id=follow.id if follow else None,
                  decided_by=user.username)
    s.add(r)
    audit(s, user.username, f"ceo_{body.decision}", "task", t.id, f"{t.title}" + (f" → #{follow.id}" if follow else ""))
    s.commit()
    return {"decision": r.decision, "followup_task_id": r.followup_task_id}


@router.post("/digest", status_code=201)
def digest(user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    """Tạo nhiệm vụ cho CEO AI: tổng hợp các kết quả chưa quyết định và đề xuất quyết định cho từng mục."""
    if get_bool(s, "emergency_stop"):
        raise HTTPException(423, "Emergency Stop đang bật.")
    rows = s.scalars(_pending_q().order_by(Task.finished_at.desc().nullslast(), Task.id.desc()).limit(DIGEST_MAX_ITEMS)).all()
    if not rows:
        raise HTTPException(409, "Không có kết quả nào đang chờ CEO quyết định.")
    pid = rows[0].project_id
    same = [t for t in rows if t.project_id == pid]  # mỗi bản tổng hợp thuộc một dự án
    _, agent = _agent(s, "ceo")
    names = {d.key: d.name for d in s.scalars(select(Department))}
    blocks = []
    for t in same:
        text = (t.result or f"(THẤT BẠI) {t.error}")[:DIGEST_ITEM_CHARS]
        blocks.append(f"### #{t.id} — {t.title}\nPhòng ban: {names.get(t.department_key, t.department_key)} (key={t.department_key}) · "
                      f"Trạng thái: {t.status} · Nguồn: {t.result_source or '—'}\n{text}")
    p = s.get(Project, pid)
    keys = ", ".join(sorted(names))
    task = Task(project_id=pid, department_key="ceo", agent_id=agent.id, status="Assigned",
                title=f"Tổng hợp để CEO quyết định ({len(same)} kết quả)",
                objective=f"Đọc các kết quả dưới đây của dự án “{p.name if p else pid}” và giúp CEO ra quyết định.",
                context="\n\n".join(blocks),
                expected_output="1) Tóm tắt điều hành (≤10 dòng). 2) Rủi ro chính. 3) Với MỖI nhiệm vụ (#id): đề xuất MỘT trong "
                                "[Chấp nhận | Sửa lại (nêu cụ thể cần sửa gì) | Chuyển sang phòng <key> (nêu việc cần làm) | Bỏ qua] kèm lý do ngắn. "
                                f"4) Thứ tự ưu tiên hành động tiếp theo. Key phòng ban hợp lệ: {keys}.",
                acceptance_criteria="Mỗi nhiệm vụ có đúng một đề xuất; chỉ dựa trên nội dung đã cung cấp, không bịa số liệu; nói rõ chỗ thiếu thông tin.",
                max_output_tokens=3000, timeout_s=180)
    s.add(task)
    s.flush()
    audit(s, user.username, "ceo_digest_created", "task", task.id, f"{len(same)} kết quả")
    s.commit()
    skipped = len(rows) - len(same)
    return {"task_id": task.id, "items": len(same), "skipped_other_projects": skipped}
