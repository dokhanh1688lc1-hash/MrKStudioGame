from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import Principal, current_user, get_db, require
from ..models import (ASSET_KINDS, ASSET_SOURCES, Agent, Asset, Department, Project, Task)
from ..services import workspace as wsvc
from ..services.common import audit, slugify
from .projects import _ws

router = APIRouter(prefix="/api", tags=["assets"])

MAX_ASSET_BYTES = 50 * 1024 * 1024
# Chỉ các định dạng tài sản thông dụng; không script/tệp thực thi/SVG (SVG có thể chứa mã)
ALLOWED = {
    "image": {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"},
    "audio": {".wav", ".ogg", ".mp3", ".flac"},
    "font": {".ttf", ".otf", ".woff", ".woff2"},
    "model": {".glb", ".gltf", ".obj", ".fbx"},
    "data": {".json", ".csv", ".txt", ".md"},
}
EXT_KIND = {e: k for k, exts in ALLOWED.items() for e in exts}
Kind = Literal["image", "audio", "font", "model", "data", "other"]
Source = Literal["own", "purchased", "open_license", "ai_generated", "unknown"]


class AssetPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    kind: Kind | None = None
    source: Source | None = None
    license: str | None = Field(default=None, max_length=200)
    license_url: str | None = Field(default=None, max_length=400)
    author: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=4000)


class DecisionIn(BaseModel):
    status: Literal["draft", "approved", "rejected"]


def _out(a: Asset) -> dict:
    return {"id": a.id, "project_id": a.project_id, "name": a.name, "kind": a.kind, "source": a.source, "license": a.license,
            "license_url": a.license_url, "author": a.author, "notes": a.notes, "has_file": bool(a.file_path),
            "file_name": Path(a.file_path).name if a.file_path else "", "file_size": a.file_size, "status": a.status,
            "created_by": a.created_by, "created_at": a.created_at, "problems": _problems(a)}


def _problems(a: Asset) -> list[str]:
    """Vấn đề bản quyền/nguồn gốc cần xử lý trước khi duyệt."""
    out = []
    if a.source == "unknown":
        out.append("Chưa rõ nguồn gốc")
    if a.source in ("purchased", "open_license") and not (a.license.strip() or a.license_url.strip()):
        out.append("Thiếu thông tin giấy phép")
    if a.source in ("purchased", "open_license") and not a.author.strip():
        out.append("Thiếu tác giả/nhà cung cấp")
    if a.source == "ai_generated" and not a.notes.strip():
        out.append("Tài sản do AI tạo: ghi công cụ/prompt vào ghi chú")
    return out


def _get(s: Session, aid: int) -> Asset:
    a = s.get(Asset, aid)
    if not a:
        raise HTTPException(404, "Không tìm thấy tài sản.")
    return a


def _file(request: Request, s: Session, a: Asset) -> Path:
    _, ws = _ws(request, s, a.project_id)
    p = (ws / a.file_path).resolve()
    if ws.resolve() not in p.parents or not p.is_file():
        raise HTTPException(404, "Tệp tài sản không còn.")
    return p


@router.get("/projects/{pid}/assets")
def list_assets(pid: int, kind: str = "", status: str = "", source: str = "", _: Principal = Depends(current_user),
                s: Session = Depends(get_db)):
    if not s.get(Project, pid):
        raise HTTPException(404, "Không tìm thấy dự án.")
    q = select(Asset).where(Asset.project_id == pid)
    for col, val in ((Asset.kind, kind), (Asset.status, status), (Asset.source, source)):
        if val:
            q = q.where(col == val)
    items = [_out(a) for a in s.scalars(q.order_by(Asset.id.desc()).limit(500))]
    allrows = s.scalars(select(Asset).where(Asset.project_id == pid)).all()
    return {"items": items, "summary": {"total": len(allrows), "approved": sum(a.status == "approved" for a in allrows),
                                        "with_problems": sum(bool(_problems(a)) for a in allrows),
                                        "ai_generated": sum(a.source == "ai_generated" for a in allrows)}}


@router.post("/projects/{pid}/assets", status_code=201)
async def create_asset(pid: int, request: Request, name: str = Form("", max_length=160), kind: str = Form(""),
                       source: str = Form("unknown"), license: str = Form("", max_length=200),
                       license_url: str = Form("", max_length=400), author: str = Form("", max_length=160),
                       notes: str = Form("", max_length=4000), file: UploadFile | None = File(None),
                       user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    p, ws = _ws(request, s, pid)
    if p.status == "Archived":
        raise HTTPException(409, "Dự án đã lưu trữ (Archived).")
    if source not in ASSET_SOURCES:
        raise HTTPException(422, "Nguồn không hợp lệ.")
    data, ext, base = b"", "", ""
    if file is not None and file.filename:
        base = Path(file.filename.replace("\\", "/")).name
        ext = Path(base).suffix.lower()
        if ext not in EXT_KIND:
            raise HTTPException(415, f"Định dạng '{ext or base}' không được phép (chỉ ảnh, âm thanh, phông, mô hình 3D, dữ liệu thông dụng).")
        if wsvc.is_secret_file(base):
            raise HTTPException(422, "Không nhận tệp bí mật.")
        data = await file.read(MAX_ASSET_BYTES + 1)
        if len(data) > MAX_ASSET_BYTES:
            raise HTTPException(413, f"Quá lớn (tối đa {MAX_ASSET_BYTES // 1024 // 1024} MB).")
        if not data:
            raise HTTPException(422, "Tệp rỗng.")
    if kind and kind not in ASSET_KINDS:
        raise HTTPException(422, "Loại không hợp lệ.")
    kind = kind or (EXT_KIND.get(ext, "other"))
    name = name.strip() or (Path(base).stem if base else "")
    if not name:
        raise HTTPException(422, "Cần tên tài sản hoặc tệp.")
    a = Asset(project_id=pid, name=name, kind=kind, source=source, license=license.strip(), license_url=license_url.strip(),
              author=author.strip(), notes=notes.strip(), created_by=user.username)
    s.add(a)
    s.flush()
    if data:
        d = ws / "assets"
        d.mkdir(parents=True, exist_ok=True)
        fname = f"{a.id}-{slugify(Path(base).stem, 'asset')}{ext}"
        (d / fname).write_bytes(data)
        a.file_path, a.file_size = f"assets/{fname}", len(data)
    audit(s, user.username, "asset_created", "asset", a.id, f"{p.name}: {a.name} ({a.source})")
    s.commit()
    return _out(a)


@router.patch("/assets/{aid}")
def patch_asset(aid: int, body: AssetPatch, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    a = _get(s, aid)
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(a, k, v.strip() if isinstance(v, str) else v)
    if a.status == "approved":  # sửa nguồn gốc/giấy phép sau khi duyệt → phải duyệt lại
        a.status = "draft"
    audit(s, user.username, "asset_updated", "asset", a.id, a.name)
    s.commit()
    return _out(a)


@router.post("/assets/{aid}/decision")
def decide(aid: int, body: DecisionIn, user: Principal = Depends(require("owner")), s: Session = Depends(get_db)):
    a = _get(s, aid)
    if body.status == "approved" and _problems(a):
        raise HTTPException(422, "Chưa thể duyệt: " + "; ".join(_problems(a)) + ".")
    a.status = body.status
    audit(s, user.username, f"asset_{body.status}", "asset", a.id, a.name)
    s.commit()
    return _out(a)


@router.delete("/assets/{aid}", status_code=204)
def delete_asset(aid: int, request: Request, user: Principal = Depends(require("owner")), s: Session = Depends(get_db)):
    a = _get(s, aid)
    try:
        f = _file(request, s, a)
        f.unlink(missing_ok=True)
    except HTTPException:
        pass
    audit(s, user.username, "asset_deleted", "asset", a.id, a.name)
    s.delete(a)
    s.commit()


@router.get("/assets/{aid}/file")
def download(aid: int, request: Request, _: Principal = Depends(current_user), s: Session = Depends(get_db)):
    a = _get(s, aid)
    f = _file(request, s, a)
    return FileResponse(f, filename=f.name, headers={"X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox"},
                        content_disposition_type="attachment")


@router.post("/projects/{pid}/assets/review-task", status_code=201)
def review_task(pid: int, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    """Giao phòng Bản quyền & Pháp lý rà soát danh sách tài sản (nhiệm vụ chờ chạy)."""
    p = s.get(Project, pid)
    if not p:
        raise HTTPException(404, "Không tìm thấy dự án.")
    rows = s.scalars(select(Asset).where(Asset.project_id == pid).order_by(Asset.id)).all()
    if not rows:
        raise HTTPException(409, "Dự án chưa có tài sản nào.")
    dept = s.scalar(select(Department).where(Department.key == "compliance"))
    agent = s.scalar(select(Agent).where(Agent.department_id == dept.id, Agent.enabled.is_(True)).order_by(Agent.id))
    if not agent:
        raise HTTPException(409, "Phòng Bản quyền & Pháp lý chưa có agent nào được bật.")
    lines = ["| ID | Tên | Loại | Nguồn | Giấy phép | Tác giả | Ghi chú | Trạng thái |", "|---|---|---|---|---|---|---|---|"]
    for a in rows[:300]:
        cell = lambda x: (x or "—").replace("|", "/").replace("\n", " ")[:120]  # noqa: E731
        lines.append(f"| {a.id} | {cell(a.name)} | {a.kind} | {a.source} | {cell(a.license or a.license_url)} | {cell(a.author)} | {cell(a.notes)} | {a.status} |")
    t = Task(project_id=pid, department_key="compliance", agent_id=agent.id, status="Assigned",
             title=f"Rà soát bản quyền tài sản ({len(rows)})", objective=f"Rà soát nguồn gốc và giấy phép tài sản của dự án “{p.name}”.",
             context="\n".join(lines),
             expected_output="Bảng: ID, rủi ro (Thấp/Vừa/Cao), lý do, hành động cần làm. Cuối cùng: danh sách tài sản chưa nên phát hành.",
             acceptance_criteria="Chỉ dựa trên thông tin trong bảng; không khẳng định pháp lý chắc chắn, nêu rõ chỗ cần xác minh; không gợi ý sao chép tác phẩm có bản quyền.",
             max_output_tokens=3000, timeout_s=180)
    s.add(t)
    s.flush()
    audit(s, user.username, "asset_review_task_created", "task", t.id, p.name)
    s.commit()
    return {"task_id": t.id, "assets": len(rows)}
