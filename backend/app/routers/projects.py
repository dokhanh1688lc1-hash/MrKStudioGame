from __future__ import annotations

import re

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..deps import Principal, current_user, get_db, require
from ..models import Agent, Department, Project, Task
from ..schemas import AgentOut, AgentPatch, DepartmentOut, DepartmentPatch, ProjectIn, ProjectOut, ProjectPatch
from ..services.common import EngineError, audit, slugify
from ..db import utcnow
from ..services import sources as src
from ..services import workspace as wsvc

router = APIRouter(prefix="/api", tags=["projects"])


def _slug(name: str) -> str:
    return slugify(name, "game")


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


# ---------- Workspace: nhập / xem mã nguồn dự án cũ ----------
def _ws(request: Request, s: Session, pid: int) -> tuple[Project, Path]:
    p = s.get(Project, pid)
    if not p:
        raise HTTPException(404, "Không tìm thấy dự án.")
    games = request.app.state.settings.games_dir.resolve()
    ws = Path(p.workspace_path).resolve() if p.workspace_path else None
    if not ws or games not in ws.parents:  # workspace phải nằm trong thư mục games/
        raise HTTPException(409, "Dự án chưa có workspace hợp lệ.")
    ws.mkdir(parents=True, exist_ok=True)
    return p, ws


@router.post("/projects/{pid}/files")
async def upload_files(pid: int, request: Request, files: list[UploadFile] = File(...),
                       user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    p, ws = _ws(request, s, pid)
    if p.status == "Archived":
        raise HTTPException(409, "Dự án đã lưu trữ (Archived).")
    uploads = []
    total = 0
    for f in files:
        data = await f.read(wsvc.MAX_UPLOAD_BYTES + 1)
        total += len(data)
        if total > wsvc.MAX_UPLOAD_BYTES:
            raise HTTPException(413, f"Quá lớn (tối đa {wsvc.MAX_UPLOAD_BYTES // 1024 // 1024} MB mỗi lần).")
        uploads.append((f.filename or "file", data))
    try:
        res = wsvc.import_uploads(ws, uploads)
    except EngineError as e:
        raise HTTPException(e.status, e.message)
    if not p.source_type:
        p.source_type, p.source_synced_at = "zip", utcnow()
    audit(s, user.username, "project_files_imported", "project", p.id,
          f"{res['import']}: {res['files_saved']} tệp, bỏ qua {len(res['skipped'])}")
    s.commit()
    return res


class GithubIn(BaseModel):
    url: str = Field(min_length=10, max_length=300)
    branch: str = Field(default="", max_length=100)


class FolderIn(BaseModel):
    path: str = Field(min_length=1, max_length=500)


class RootsIn(BaseModel):
    paths: list[str] = Field(max_length=20)


def _record_source(s: Session, p: Project, user: Principal, kind: str, ref: str, branch: str, res: dict) -> dict:
    p.source_type, p.source_ref, p.source_branch, p.source_synced_at = kind, ref, branch, utcnow()
    extra = f", commit {res['commit'][:8]}" if res.get("commit") else ""
    audit(s, user.username, f"project_import_{kind}", "project", p.id,
          f"{ref}: {res['files_saved']} tệp, bỏ qua {len(res['skipped'])}{extra}")
    s.commit()
    return res


def _guard_import(p: Project) -> None:
    if p.status == "Archived":
        raise HTTPException(409, "Dự án đã lưu trữ (Archived).")


@router.post("/projects/{pid}/import/github", status_code=201)
def import_github(pid: int, body: GithubIn, request: Request, user: Principal = Depends(require("manager")),
                  s: Session = Depends(get_db)):
    p, ws = _ws(request, s, pid)
    _guard_import(p)
    try:
        res = src.import_github(ws, body.url, body.branch)
    except EngineError as e:
        raise HTTPException(e.status, e.message)
    return _record_source(s, p, user, "github", res["source"], body.branch.strip(), res)


@router.post("/projects/{pid}/import/folder", status_code=201)
def import_folder(pid: int, body: FolderIn, request: Request, user: Principal = Depends(require("manager")),
                  s: Session = Depends(get_db)):
    p, ws = _ws(request, s, pid)
    _guard_import(p)
    try:
        res = src.import_folder(s, ws, body.path)
    except EngineError as e:
        raise HTTPException(e.status, e.message)
    return _record_source(s, p, user, "folder", res["source"], "", res)


@router.post("/projects/{pid}/sync", status_code=201)
def sync_source(pid: int, request: Request, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    """Lấy lại bản mới nhất từ nguồn đã nhập (GitHub / thư mục). Tạo thư mục imports/ mới, không ghi đè bản cũ."""
    p, ws = _ws(request, s, pid)
    _guard_import(p)
    if p.source_type not in ("github", "folder"):
        raise HTTPException(409, "Dự án chưa liên kết GitHub hoặc thư mục trên máy.")
    try:
        res = (src.import_github(ws, p.source_ref, p.source_branch) if p.source_type == "github"
               else src.import_folder(s, ws, p.source_ref))
    except EngineError as e:
        raise HTTPException(e.status, e.message)
    return _record_source(s, p, user, p.source_type, p.source_ref, p.source_branch, res)


@router.get("/system/import-roots")
def get_import_roots(_: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    return {"paths": src.get_roots(s)}


@router.put("/system/import-roots")
def put_import_roots(body: RootsIn, user: Principal = Depends(require("owner")), s: Session = Depends(get_db)):
    try:
        paths = src.set_roots(s, body.paths)
    except EngineError as e:
        raise HTTPException(e.status, e.message)
    audit(s, user.username, "import_roots_changed", "system", "", "; ".join(paths))
    s.commit()
    return {"paths": paths}


@router.get("/system/browse")
def browse_folders(path: str = "", _: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    try:
        return src.browse(s, path)
    except EngineError as e:
        raise HTTPException(e.status, e.message)


@router.get("/projects/{pid}/files")
def list_files(pid: int, request: Request, _: Principal = Depends(current_user), s: Session = Depends(get_db)):
    _, ws = _ws(request, s, pid)
    return wsvc.list_tree(ws)


@router.get("/projects/{pid}/files/content")
def file_content(pid: int, path: str, request: Request, _: Principal = Depends(current_user),
                 s: Session = Depends(get_db)):
    _, ws = _ws(request, s, pid)
    try:
        return wsvc.read_text(ws, path)
    except EngineError as e:
        raise HTTPException(e.status, e.message)


class UpgradeIn(BaseModel):
    goal: str = Field(min_length=3)
    provider: str | None = None
    sensitive: bool = False


@router.post("/projects/{pid}/upgrade-task", status_code=201)
def upgrade_task(pid: int, body: UpgradeIn, request: Request, user: Principal = Depends(require("manager")),
                 s: Session = Depends(get_db)):
    """Tạo nhiệm vụ cho Game Development AI: phân tích mã nguồn đã nhập và đề xuất sửa/nâng cấp."""
    p, ws = _ws(request, s, pid)
    if p.status == "Archived":
        raise HTTPException(409, "Dự án đã lưu trữ (Archived).")
    if body.provider not in (None, "openai", "anthropic", "internal"):
        raise HTTPException(422, "Provider không hợp lệ.")
    ctx = wsvc.build_context(ws)
    if ctx.startswith("(Workspace chưa"):
        raise HTTPException(409, "Dự án chưa có mã nguồn. Hãy tải mã nguồn lên trước.")
    dept = s.scalar(select(Department).where(Department.key == "game_dev"))
    agent = s.scalar(select(Agent).where(Agent.department_id == dept.id, Agent.enabled.is_(True)).order_by(Agent.id))
    if not agent:
        raise HTTPException(409, "Phòng ban Game Development chưa có agent nào được bật.")
    t = Task(project_id=p.id, department_key="game_dev", agent_id=agent.id, status="Assigned",
             title=f"Phân tích & nâng cấp: {body.goal[:80]}", objective=body.goal,
             context=f"Game: {p.name} ({p.genre or 'chưa rõ thể loại'}, {p.platform or 'chưa rõ nền tảng'})\n\n{ctx}",
             expected_output="1) Hiện trạng. 2) Lỗi/rủi ro (theo mức nghiêm trọng, ghi rõ tệp). "
                             "3) Kế hoạch sửa/nâng cấp theo thứ tự ưu tiên. 4) Đoạn mã đề xuất cụ thể cho từng thay đổi quan trọng. "
                             "Chỉ dựa trên mã nguồn đã cung cấp; nêu rõ phần nào chưa đủ thông tin.",
             acceptance_criteria="Mỗi nhận định nêu tệp liên quan; không bịa tệp hoặc hàm không có trong ngữ cảnh.",
             provider=body.provider, sensitive=body.sensitive, max_output_tokens=4000, timeout_s=180)
    s.add(t)
    s.flush()
    audit(s, user.username, "upgrade_task_created", "task", t.id, p.name)
    s.commit()
    return {"task_id": t.id, "context_chars": len(t.context)}
