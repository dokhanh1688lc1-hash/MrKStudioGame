from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..deps import Principal, current_user, get_db, require
from ..models import Department, Lesson, Project
from ..services import lessons as svc
from ..services.common import audit

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


class LessonIn(BaseModel):
    department_key: str
    text: str = Field(min_length=5, max_length=svc.MAX_TEXT * 2)
    project_id: int | None = None


class LessonPatch(BaseModel):
    text: str | None = Field(default=None, min_length=5, max_length=svc.MAX_TEXT * 2)
    project_id: int | None = None          # gửi null = áp dụng cho mọi dự án
    status: Literal["suggested", "active", "archived"] | None = None


def _out(l: Lesson, names: dict[int, str]) -> dict:
    return {"id": l.id, "department_key": l.department_key, "project_id": l.project_id,
            "project_name": names.get(l.project_id, "") if l.project_id else "", "text": l.text, "status": l.status,
            "source": l.source, "task_id": l.task_id, "uses": l.uses, "created_by": l.created_by, "created_at": l.created_at}


def _check_scope(s: Session, department_key: str | None, project_id: int | None) -> None:
    if department_key is not None and not s.scalar(select(Department).where(Department.key == department_key)):
        raise HTTPException(422, f"Phòng ban không tồn tại: {department_key}")
    if project_id is not None and not s.get(Project, project_id):
        raise HTTPException(422, "Dự án không tồn tại.")


def _check_cap(s: Session, department_key: str, exclude_id: int | None = None) -> None:
    n = s.scalar(select(func.count()).select_from(Lesson).where(Lesson.department_key == department_key, Lesson.status == "active",
                                                                 Lesson.id != (exclude_id or 0)))
    if n >= svc.MAX_ACTIVE_PER_DEPT:
        raise HTTPException(409, f"Phòng ban đã có {n} bài học đang dùng (tối đa {svc.MAX_ACTIVE_PER_DEPT}). Hãy lưu trữ bớt.")


@router.get("")
def list_lessons(department: str = "", status: str = "", project_id: int | None = None, limit: int = Query(500, ge=0, le=500),
                 _: Principal = Depends(current_user), s: Session = Depends(get_db)):
    q = select(Lesson)
    if department:
        q = q.where(Lesson.department_key == department)
    if status:
        q = q.where(Lesson.status == status)
    if project_id:
        q = q.where((Lesson.project_id == project_id) | Lesson.project_id.is_(None))
    rows = s.scalars(q.order_by(Lesson.id.desc()).limit(limit)).all()
    names = {p.id: p.name for p in s.scalars(select(Project).where(Project.id.in_([l.project_id for l in rows if l.project_id] or [0])))}
    counts = dict(s.execute(select(Lesson.status, func.count()).group_by(Lesson.status)).all())
    return {"items": [_out(l, names) for l in rows],
            "counts": {k: counts.get(k, 0) for k in ("suggested", "active", "archived")}}


@router.post("", status_code=201)
def create_lesson(body: LessonIn, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    _check_scope(s, body.department_key, body.project_id)
    text = svc.clean(body.text)
    if len(text) < 5:
        raise HTTPException(422, "Bài học quá ngắn.")
    _check_cap(s, body.department_key)
    l = Lesson(department_key=body.department_key, project_id=body.project_id, text=text, status="active", source="manual",
               created_by=user.username)
    s.add(l)
    s.flush()
    audit(s, user.username, "lesson_created", "lesson", l.id, f"{l.department_key}: {text[:80]}")
    s.commit()
    return _out(l, {})


@router.patch("/{lid}")
def patch_lesson(lid: int, body: LessonPatch, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    l = s.get(Lesson, lid)
    if not l:
        raise HTTPException(404, "Không tìm thấy bài học.")
    data = body.model_dump(exclude_unset=True)
    if "project_id" in data:
        _check_scope(s, None, data["project_id"])
        l.project_id = data["project_id"]
    if data.get("text") is not None:
        t = svc.clean(data["text"])
        if len(t) < 5:
            raise HTTPException(422, "Bài học quá ngắn.")
        l.text = t
    if data.get("status") and data["status"] != l.status:
        if data["status"] == "active":
            _check_cap(s, l.department_key, l.id)
        l.status = data["status"]
    audit(s, user.username, "lesson_updated", "lesson", l.id, f"{l.status}")
    s.commit()
    names = {l.project_id: s.get(Project, l.project_id).name} if l.project_id else {}
    return _out(l, names)


@router.delete("/{lid}", status_code=204)
def delete_lesson(lid: int, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    l = s.get(Lesson, lid)
    if not l:
        raise HTTPException(404, "Không tìm thấy bài học.")
    audit(s, user.username, "lesson_deleted", "lesson", l.id, l.text[:80])
    s.delete(l)
    s.commit()
