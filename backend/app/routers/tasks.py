from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..deps import Principal, current_user, get_db, require
from ..models import Agent, Department, Project, Task, TaskDependency
from ..schemas import BulkTaskIn, TaskDetail, TaskIn, TaskOut
from ..services.common import EngineError, audit, slugify
from ..services.templates import all_templates
from ..services.pipeline import TEMPLATE, create_pipeline, pipeline_tasks

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _detail(s: Session, t: Task) -> TaskDetail:
    d = TaskDetail.model_validate(t)
    d.depends_on = [x.depends_on_id for x in s.scalars(select(TaskDependency).where(TaskDependency.task_id == t.id))]
    return d


@router.get("")
def list_tasks(project_id: int | None = None, status: str = "", department: str = "", q: str = "",
               limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
               _: Principal = Depends(current_user), s: Session = Depends(get_db)):
    where = []
    if project_id:
        where.append(Task.project_id == project_id)
    if status:
        where.append(Task.status == status)
    if department:
        where.append(Task.department_key == department)
    if q:
        where.append(or_(Task.title.ilike(f"%{q}%"), Task.objective.ilike(f"%{q}%")))
    total = s.scalar(select(func.count()).select_from(Task).where(*where))
    rows = s.scalars(select(Task).where(*where).order_by(Task.id.desc()).limit(limit).offset(offset)).all()
    return {"items": [TaskOut.model_validate(r) for r in rows], "total": total}


@router.post("", response_model=TaskDetail, status_code=201)
def create_task(body: TaskIn, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    p = s.get(Project, body.project_id)
    if not p:
        raise HTTPException(404, "Không tìm thấy dự án.")
    if p.status in ("Archived",):
        raise HTTPException(409, "Dự án đã lưu trữ (Archived).")
    dept = s.scalar(select(Department).where(Department.key == body.department_key))
    if not dept:
        raise HTTPException(422, f"Phòng ban không tồn tại: {body.department_key}")
    for dep_id in body.depends_on:
        dt = s.get(Task, dep_id)
        if not dt or dt.project_id != p.id:  # cô lập dự án
            raise HTTPException(422, f"Nhiệm vụ phụ thuộc #{dep_id} không thuộc dự án này.")
    agent = s.scalar(select(Agent).where(Agent.department_id == dept.id, Agent.enabled.is_(True)).order_by(Agent.id))
    if not agent:
        raise HTTPException(409, "Phòng ban chưa có agent nào được bật.")
    data = body.model_dump(exclude={"depends_on"})
    t = Task(**data, agent_id=agent.id, status="Assigned")
    s.add(t)
    s.flush()
    for dep_id in set(body.depends_on):
        s.add(TaskDependency(task_id=t.id, depends_on_id=dep_id))
    audit(s, user.username, "task_created", "task", t.id, t.title)
    s.commit()
    return _detail(s, t)


@router.post("/bulk", status_code=201)
def create_bulk(body: BulkTaskIn, request: Request, user: Principal = Depends(require("manager")),
                s: Session = Depends(get_db)):
    """Tạo mỗi phòng ban một nhiệm vụ. Kiểm tra tất cả trước; có lỗi thì không tạo gì (tất cả hoặc không)."""
    p = s.get(Project, body.project_id)
    if not p:
        raise HTTPException(404, "Không tìm thấy dự án.")
    if p.status == "Archived":
        raise HTTPException(409, "Dự án đã lưu trữ (Archived).")
    keys = list(dict.fromkeys(body.department_keys))  # bỏ trùng, giữ thứ tự
    unknown = [k for k in body.notes if k not in keys]
    if unknown:
        raise HTTPException(422, f"Ghi chú cho phòng ban không nằm trong danh sách chọn: {unknown}")
    agents: dict[str, Agent] = {}
    for k in keys:
        dept = s.scalar(select(Department).where(Department.key == k))
        if not dept:
            raise HTTPException(422, f"Phòng ban không tồn tại: {k}")
        agent = s.scalar(select(Agent).where(Agent.department_id == dept.id, Agent.enabled.is_(True)).order_by(Agent.id))
        if not agent:
            raise HTTPException(409, f"Phòng ban '{dept.name}' chưa có agent nào được bật.")
        agents[k] = agent
    base = body.model_dump(exclude={"department_keys", "notes", "run_now"})
    created: list[Task] = []
    for k in keys:
        data = dict(base)
        if body.notes.get(k, "").strip():
            data["objective"] = f"{body.objective}\n\nGhi chú riêng cho phòng ban này:\n{body.notes[k].strip()}"
        t = Task(**data, department_key=k, agent_id=agents[k].id, status="Assigned")
        s.add(t)
        created.append(t)
    s.flush()
    audit(s, user.username, "tasks_bulk_created", "project", p.id, f"{len(created)} nhiệm vụ: {', '.join(keys)}")
    for t in created:
        audit(s, user.username, "task_created", "task", t.id, t.title)
    s.commit()
    ids = [t.id for t in created]
    started, errors = [], {}
    if body.run_now:
        orch = request.app.state.orch
        for tid in ids:
            try:
                chain = orch.prepare_run(tid, user.username)
                orch.run_async(tid, chain, user.username)
                started.append(tid)
            except EngineError as e:
                errors[tid] = e.message
    return {"task_ids": ids, "started": started, "run_errors": errors}


@router.get("/templates/all")
def task_templates(_: Principal = Depends(current_user)):
    """Mẫu nhiệm vụ theo phòng ban (key phòng ban → danh sách mẫu)."""
    return all_templates()


@router.get("/{tid}", response_model=TaskDetail)
def get_task(tid: int, _: Principal = Depends(current_user), s: Session = Depends(get_db)):
    t = s.get(Task, tid)
    if not t:
        raise HTTPException(404, "Không tìm thấy nhiệm vụ.")
    return _detail(s, t)


@router.post("/{tid}/run", response_model=TaskDetail)
def run_task(tid: int, request: Request, wait: bool = False, user: Principal = Depends(require("manager")),
             s: Session = Depends(get_db)):
    orch = request.app.state.orch
    try:
        chain = orch.prepare_run(tid, user.username)
    except EngineError as e:
        raise HTTPException(e.status, e.message)
    if wait:
        orch.execute_run(tid, chain, user.username)
    else:
        orch.run_async(tid, chain, user.username)
    s.expire_all()
    return _detail(s, s.get(Task, tid))


@router.post("/{tid}/cancel", response_model=TaskDetail)
def cancel_task(tid: int, request: Request, user: Principal = Depends(require("manager")),
                s: Session = Depends(get_db)):
    try:
        request.app.state.orch.cancel(tid, user.username)
    except EngineError as e:
        raise HTTPException(e.status, e.message)
    s.expire_all()
    return _detail(s, s.get(Task, tid))


# ---------- Pipeline sản xuất game ----------
pipe = APIRouter(prefix="/api", tags=["pipeline"])


class PipelineIn(BaseModel):
    brief: str = ""


@pipe.get("/pipeline/template")
def pipeline_template(_: Principal = Depends(current_user)):
    return [{"index": i, "key": s.key, "department": s.dept, "title": s.title, "depends_on": list(s.deps),
             "needs_owner_approval": s.gate} for i, s in enumerate(TEMPLATE, 1)]


@pipe.get("/projects/{pid}/pipeline")
def get_pipeline(pid: int, _: Principal = Depends(current_user), s: Session = Depends(get_db)):
    if not s.get(Project, pid):
        raise HTTPException(404, "Không tìm thấy dự án.")
    return [_detail(s, t) for t in pipeline_tasks(s, pid)]


@pipe.post("/projects/{pid}/pipeline", status_code=201)
def make_pipeline(pid: int, body: PipelineIn, user: Principal = Depends(require("manager")),
                  s: Session = Depends(get_db)):
    try:
        tasks = create_pipeline(s, pid, body.brief.strip(), user.username)
    except EngineError as e:
        raise HTTPException(e.status, e.message)
    return [_detail(s, t) for t in tasks]


@pipe.post("/projects/{pid}/pipeline/run-ready")
def run_ready(pid: int, request: Request, wait: bool = False, user: Principal = Depends(require("manager")),
              s: Session = Depends(get_db)):
    """Chạy các bước đã đủ điều kiện (phụ thuộc xong). Bước cần phê duyệt sẽ tạo yêu cầu thay vì chạy."""
    if not s.get(Project, pid):
        raise HTTPException(404, "Không tìm thấy dự án.")
    orch = request.app.state.orch
    report: list[dict] = []
    seen: set[int] = set()
    for _round in range(len(TEMPLATE) if wait else 1):
        progressed = False
        s.expire_all()
        for t in pipeline_tasks(s, pid):
            if t.status not in ("Assigned", "Blocked") or t.id in seen:
                continue
            ready = all(s.get(Task, d.depends_on_id).status == "Completed" for d in
                        s.scalars(select(TaskDependency).where(TaskDependency.task_id == t.id)))
            if not ready:
                continue
            seen.add(t.id)
            try:
                chain = orch.prepare_run(t.id, user.username)
            except EngineError as e:
                report.append({"task_id": t.id, "title": t.title, "outcome": "not_started", "reason": e.message})
                if e.status in (402, 423):  # ngân sách / Emergency Stop: dừng cả pipeline
                    return report
                continue
            if wait:
                orch.execute_run(t.id, chain, user.username)
            else:
                orch.run_async(t.id, chain, user.username)
            report.append({"task_id": t.id, "title": t.title, "outcome": "started" if not wait else "finished"})
            progressed = True
        if not progressed:
            break
    return report


@router.post("/{tid}/save-to-workspace")
def save_result(tid: int, request: Request, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    """Lưu kết quả nhiệm vụ đã hoàn thành thành tệp .md trong workspace dự án (ai-output/)."""
    import re
    from pathlib import Path
    t = s.get(Task, tid)
    if not t:
        raise HTTPException(404, "Không tìm thấy nhiệm vụ.")
    if t.status != "Completed" or not t.result:
        raise HTTPException(409, "Chỉ lưu được kết quả của nhiệm vụ đã hoàn thành.")
    p = s.get(Project, t.project_id)
    games = request.app.state.settings.games_dir.resolve()
    ws = Path(p.workspace_path).resolve() if p.workspace_path else None
    if not ws or games not in ws.parents:
        raise HTTPException(409, "Dự án chưa có workspace hợp lệ.")
    out = ws / "ai-output"
    out.mkdir(parents=True, exist_ok=True)
    slug = slugify(t.title, "task")
    f = out / f"{t.id}-{slug}.md"
    f.write_text(f"<!-- nguồn: {t.result_source}; nhiệm vụ #{t.id} -->\n\n{t.result}", encoding="utf-8")
    audit(s, user.username, "task_result_saved", "task", t.id, f.name)
    s.commit()
    return {"path": f"ai-output/{f.name}"}
