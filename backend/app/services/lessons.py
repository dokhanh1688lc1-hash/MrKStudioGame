"""Sổ bài học theo phòng ban: lưu các điều CEO đã chỉnh, chèn gọn vào prompt các nhiệm vụ sau để phòng ban làm đúng ý hơn.
Chỉ bài học đã duyệt (active) mới được chèn; giới hạn số lượng và độ dài để tiết kiệm token."""
from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..models import Lesson
from . import workspace as wsvc

MAX_INJECT = 8             # tối đa số bài chèn vào một prompt
MAX_INJECT_CHARS = 1500    # tổng độ dài tối đa
MAX_ACTIVE_PER_DEPT = 30
MAX_TEXT = 500


def clean(text: str) -> str:
    return " ".join(wsvc.redact(text or "").split())[:MAX_TEXT]


def active_for(s: Session, department_key: str, project_id: int | None) -> list[Lesson]:
    q = select(Lesson).where(Lesson.department_key == department_key, Lesson.status == "active")
    q = q.where(or_(Lesson.project_id.is_(None), Lesson.project_id == project_id)) if project_id else q.where(Lesson.project_id.is_(None))
    out, total = [], 0
    for l in s.scalars(q.order_by(Lesson.updated_at.desc(), Lesson.id.desc())):
        if len(out) >= MAX_INJECT or total + len(l.text) > MAX_INJECT_CHARS:
            break
        out.append(l)
        total += len(l.text)
    return out


def texts_and_mark_used(s: Session, department_key: str, project_id: int | None) -> list[str]:
    ls = active_for(s, department_key, project_id)
    for l in ls:
        l.uses += 1
    if ls:
        s.commit()
    return [l.text for l in ls]


def suggest(s: Session, *, department_key: str, project_id: int | None, text: str, task_id: int | None, by: str) -> Lesson | None:
    """Tạo bài học đề xuất (chờ duyệt) từ phản hồi của CEO; bỏ qua nếu trống/quá ngắn hoặc đã có bài giống hệt."""
    text = clean(text)
    if len(text) < 5:
        return None
    dup = s.scalar(select(Lesson).where(Lesson.department_key == department_key, Lesson.text == text,
                                        Lesson.status != "archived", Lesson.project_id.is_(None) if project_id is None else Lesson.project_id == project_id))
    if dup:
        return None
    l = Lesson(department_key=department_key, project_id=project_id, text=text, status="suggested", source="ceo",
               task_id=task_id, created_by=by)
    s.add(l)
    return l
