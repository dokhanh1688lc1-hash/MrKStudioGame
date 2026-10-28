from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import utcnow
from ..deps import Principal, current_user, get_db, require
from ..models import FileChange, Project, Task
from ..services import changes as ch
from ..services import sources as src
from ..services.common import EngineError, audit, get_bool

router = APIRouter(prefix="/api", tags=["changes"])


class WriteIn(BaseModel):
    enabled: bool


class ManualIn(BaseModel):
    path: str = Field(min_length=1, max_length=400)
    content: str = Field(max_length=2_000_000)


def _project(s: Session, pid: int) -> Project:
    p = s.get(Project, pid)
    if not p:
        raise HTTPException(404, "Không tìm thấy dự án.")
    return p


def _root(s: Session, p: Project):
    """Thư mục dự án trên máy; phải là dự án liên kết thư mục và vẫn nằm trong vùng được phép."""
    if p.source_type != "folder":
        raise HTTPException(409, "Chỉ sửa file được với dự án đã liên kết thư mục trên máy (Mã nguồn → Từ thư mục trên máy).")
    try:
        return src.resolve_allowed(s, p.source_ref)
    except EngineError as e:
        raise HTTPException(e.status, e.message)


def _row(s: Session, p: Project, c: FileChange, with_diff: bool = True) -> dict:
    d = {"id": c.id, "project_id": c.project_id, "task_id": c.task_id, "path": c.path, "status": c.status, "source": c.source,
         "is_new": c.base_sha == "", "created_by": c.created_by, "decided_by": c.decided_by,
         "created_at": c.created_at, "decided_at": c.decided_at}
    if with_diff and c.status == "pending":
        try:
            cur = ch.read_current(_root(s, p), c.path)
            old = None if cur is None else cur.decode("utf-8", errors="replace")
            d["diff"] = ch.make_diff(c.path, old, c.new_content)
            d["stale"] = (cur is not None) if c.base_sha == "" else (cur is None or ch.sha(cur) != c.base_sha)
        except (EngineError, HTTPException) as e:
            d["diff"], d["stale"] = "", True
            d["error"] = e.message if isinstance(e, EngineError) else str(e.detail)
    return d


@router.put("/projects/{pid}/write-access")
def set_write_access(pid: int, body: WriteIn, user: Principal = Depends(require("owner")), s: Session = Depends(get_db)):
    p = _project(s, pid)
    if body.enabled:
        _root(s, p)  # phải liên kết thư mục hợp lệ trong vùng cho phép
    p.allow_write = body.enabled
    audit(s, user.username, "project_write_access", "project", p.id, "bật" if body.enabled else "tắt")
    s.commit()
    return {"allow_write": p.allow_write}


@router.post("/tasks/{tid}/extract-changes", status_code=201)
def extract_changes(tid: int, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    """Trích các khối sửa tệp từ kết quả AI thành đề xuất chờ duyệt (chưa ghi gì vào máy)."""
    t = s.get(Task, tid)
    if not t:
        raise HTTPException(404, "Không tìm thấy nhiệm vụ.")
    if t.status != "Completed" or not t.result:
        raise HTTPException(409, "Nhiệm vụ chưa hoàn thành.")
    if t.result_source == "internal":
        raise HTTPException(409, "Kết quả này do chế độ nội bộ dựng sẵn, không phải đề xuất của AI.")
    p = _project(s, t.project_id)
    if p.status == "Archived":
        raise HTTPException(409, "Dự án đã lưu trữ (Archived).")
    root = _root(s, p)
    proposals, errors = ch.parse_ai_output(t.result, root)
    if not proposals and not errors:
        raise HTTPException(422, "Kết quả không có khối sửa tệp nào (AI cần dùng định dạng <<<FILE …>>>).")
    ids = []
    for pr in proposals:
        c = FileChange(project_id=p.id, task_id=t.id, path=pr.rel, new_content=pr.new_content, base_sha=pr.base_sha,
                       source="ai", created_by=user.username)
        s.add(c)
        s.flush()
        ids.append(c.id)
    audit(s, user.username, "changes_proposed", "task", t.id, f"{len(ids)} đề xuất, {len(errors)} lỗi")
    s.commit()
    return {"created": ids, "errors": errors}


@router.post("/projects/{pid}/changes", status_code=201)
def propose_manual(pid: int, body: ManualIn, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    p = _project(s, pid)
    if p.status == "Archived":
        raise HTTPException(409, "Dự án đã lưu trữ (Archived).")
    root = _root(s, p)
    try:
        pr = ch.propose_manual(root, body.path, body.content)
    except EngineError as e:
        raise HTTPException(e.status, e.message)
    c = FileChange(project_id=p.id, path=pr.rel, new_content=pr.new_content, base_sha=pr.base_sha, source="manual",
                   created_by=user.username)
    s.add(c)
    s.flush()
    audit(s, user.username, "changes_proposed", "project", p.id, f"thủ công: {pr.rel}")
    s.commit()
    return _row(s, p, c)


@router.get("/projects/{pid}/source-file")
def source_file(pid: int, path: str, _: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    """Nội dung hiện tại của tệp trong thư mục dự án (để soạn sửa tay). Không đọc tệp bí mật/loại không cho phép."""
    p = _project(s, pid)
    root = _root(s, p)
    try:
        rel = ch.normalize_rel(path)
        txt = ch.current_text(root, rel)
    except EngineError as e:
        raise HTTPException(e.status, e.message)
    return {"path": rel, "exists": txt is not None, "content": txt or ""}


@router.get("/projects/{pid}/changes")
def list_changes(pid: int, status: str = Query("", max_length=12), _: Principal = Depends(current_user),
                 s: Session = Depends(get_db)):
    p = _project(s, pid)
    q = select(FileChange).where(FileChange.project_id == pid)
    if status:
        q = q.where(FileChange.status == status)
    rows = s.scalars(q.order_by(FileChange.id.desc()).limit(200)).all()
    return {"allow_write": p.allow_write, "items": [_row(s, p, c) for c in rows]}


def _get(s: Session, cid: int) -> tuple[FileChange, Project]:
    c = s.get(FileChange, cid)
    if not c:
        raise HTTPException(404, "Không tìm thấy đề xuất.")
    return c, _project(s, c.project_id)


@router.post("/changes/{cid}/reject")
def reject(cid: int, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    c, p = _get(s, cid)
    if c.status != "pending":
        raise HTTPException(409, "Đề xuất không còn ở trạng thái chờ duyệt.")
    c.status, c.decided_by, c.decided_at = "rejected", user.username, utcnow()
    audit(s, user.username, "change_rejected", "file_change", c.id, c.path)
    s.commit()
    return _row(s, p, c, False)


@router.post("/changes/{cid}/apply")
def apply(cid: int, request: Request, user: Principal = Depends(require("owner")), s: Session = Depends(get_db)):
    c, p = _get(s, cid)
    if get_bool(s, "emergency_stop"):
        raise HTTPException(423, "Emergency Stop đang bật.")
    if c.status != "pending":
        raise HTTPException(409, "Đề xuất không còn ở trạng thái chờ duyệt.")
    if not p.allow_write:
        raise HTTPException(403, "Dự án chưa bật quyền ghi vào thư mục trên máy (chủ studio bật trong Mã nguồn).")
    root = _root(s, p)
    bdir = request.app.state.settings.data_dir / "file-backups" / str(p.id) / f"{c.id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    try:
        res = ch.apply_change(root, c.path, c.new_content, c.base_sha, bdir)
    except EngineError as e:
        raise HTTPException(e.status, e.message)
    except OSError as e:
        raise HTTPException(500, f"Không ghi được tệp: {e.strerror or e}")
    c.status, c.backup_path, c.applied_sha = "applied", res["backup"], res["applied_sha"]
    c.decided_by, c.decided_at = user.username, utcnow()
    audit(s, user.username, "change_applied", "file_change", c.id, f"{p.name}: {c.path}")
    s.commit()
    return _row(s, p, c, False)


@router.post("/changes/{cid}/revert")
def revert(cid: int, user: Principal = Depends(require("owner")), s: Session = Depends(get_db)):
    c, p = _get(s, cid)
    if get_bool(s, "emergency_stop"):
        raise HTTPException(423, "Emergency Stop đang bật.")
    if c.status != "applied":
        raise HTTPException(409, "Chỉ hoàn tác được thay đổi đã áp dụng.")
    root = _root(s, p)
    try:
        ch.revert_change(root, c.path, c.applied_sha, c.backup_path)
    except EngineError as e:
        raise HTTPException(e.status, e.message)
    except OSError as e:
        raise HTTPException(500, f"Không khôi phục được tệp: {e.strerror or e}")
    c.status, c.decided_by, c.decided_at = "reverted", user.username, utcnow()
    audit(s, user.username, "change_reverted", "file_change", c.id, f"{p.name}: {c.path}")
    s.commit()
    return _row(s, p, c, False)
