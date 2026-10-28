from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..deps import Principal, current_user, get_db, require
from ..models import Agent, Department, Project
from ..schemas import AgentOut, AgentPatch, DepartmentOut, DepartmentPatch, ProjectIn, ProjectOut, ProjectPatch
from ..services.common import audit

router = APIRouter(prefix="/api", tags=["projects"])


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "game"


@router.get("/projects")
def list_projects(q: str = "", status: str = "", limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                  _: Principal = Depends(current_user), s: Session = Depends(get_db)):
    where = []
    if q:
        like = f"%{q}%"
        where.append(or_(Project.name.ilike(like), Project.description.ilike(like), Project.genre.ilike(like)))
    if status:
        where.append(Project.status == status)
    total = s.scalar(select(func.count()).select_from(Project).where(*where))
    rows = s.scalars(select(Project).where(*where).order_by(Project.id.desc()).limit(limit).offset(offset)).all()
    return {"items": [ProjectOut.model_validate(r) for r in rows], "total": total}


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectIn, request: Request, user: Principal = Depends(require("manager")),
                   s: Session = Depends(get_db)):
    p = Project(**body.model_dump())
    s.add(p)
    try:
        s.flush()
    except IntegrityError:
        s.rollback()
        raise HTTPException(409, "Tên dự án đã tồn tại.")
    # Workspace riêng cho mỗi game, cô lập khỏi dự án khác.
    ws = request.app.state.settings.games_dir / f"{p.id}-{_slug(p.name)}"
    ws.mkdir(parents=True, exist_ok=True)
    p.workspace_path = str(ws)
    audit(s, user.username, "project_created", "project", p.id, p.name)
    s.commit()
    return p


@router.get("/projects/{pid}", response_model=ProjectOut)
def get_project(pid: int, _: Principal = Depends(current_user), s: Session = Depends(get_db)):
    p = s.get(Project, pid)
    if not p:
        raise HTTPException(404, "Không tìm thấy dự án.")
    return p


@router.patch("/projects/{pid}", response_model=ProjectOut)
def patch_project(pid: int, body: ProjectPatch, user: Principal = Depends(require("manager")),
                  s: Session = Depends(get_db)):
    p = s.get(Project, pid)
    if not p:
        raise HTTPException(404, "Không tìm thấy dự án.")
    changes = body.model_dump(exclude_unset=True)
    for k, v in changes.items():
        if v is not None:
            setattr(p, k, v)
    try:
        audit(s, user.username, "project_updated", "project", p.id, ", ".join(changes))
        s.commit()
    except IntegrityError:
        s.rollback()
        raise HTTPException(409, "Tên dự án đã tồn tại.")
    return p


@router.get("/departments", response_model=list[DepartmentOut])
def departments(_: Principal = Depends(current_user), s: Session = Depends(get_db)):
    return s.scalars(select(Department).order_by(Department.id)).all()


@router.patch("/departments/{key}", response_model=DepartmentOut)
def patch_department(key: str, body: DepartmentPatch, user: Principal = Depends(require("owner")),
                     s: Session = Depends(get_db)):
    d = s.scalar(select(Department).where(Department.key == key))
    if not d:
        raise HTTPException(404, "Không tìm thấy phòng ban.")
    d.preferred_provider = body.preferred_provider
    audit(s, user.username, "department_routing_changed", "department", key, body.preferred_provider)
    s.commit()
    return d


@router.get("/agents", response_model=list[AgentOut])
def agents(_: Principal = Depends(current_user), s: Session = Depends(get_db)):
    return s.scalars(select(Agent).order_by(Agent.id)).all()


@router.patch("/agents/{aid}", response_model=AgentOut)
def patch_agent(aid: int, body: AgentPatch, user: Principal = Depends(require("owner")), s: Session = Depends(get_db)):
    a = s.get(Agent, aid)
    if not a:
        raise HTTPException(404, "Không tìm thấy agent.")
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(a, k, v)
    audit(s, user.username, "agent_updated", "agent", aid)
    s.commit()
    return a
