from __future__ import annotations

import json
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import Principal, get_db, require
from ..models import Asset, Project, ProjectDocument, TestCase
from ..services.common import audit, slugify

router = APIRouter(prefix="/api/samples", tags=["samples"])

SAMPLE = Path(__file__).resolve().parents[3] / "samples" / "godot-coin-dash"
BASE_NAME = "Coin Dash (game mẫu Godot)"
SKIP_DIRS = {".godot", "__pycache__"}
SAMPLE_DOCS = {"GDD.md": ("gdd", "GDD — Coin Dash"), "COPYRIGHT.md": ("legal", "Hồ sơ bản quyền — Coin Dash"),
               "MONETIZATION.md": ("monetization", "Kế hoạch kiếm tiền — Coin Dash"), "BUILD.md": ("tech", "Hướng dẫn build — Coin Dash"),
               "BUG_REPORT_TEMPLATE.md": ("qa_report", "Mẫu báo cáo lỗi — Coin Dash")}


def sample_dir() -> Path:
    return SAMPLE


@router.get("")
def list_samples(_: Principal = Depends(require("viewer"))):
    return [{"key": "godot-coin-dash", "name": "Coin Dash — platformer 2D (Godot 4)", "available": SAMPLE.is_dir(),
             "description": "Game hoàn chỉnh nhỏ: mã nguồn GDScript, tài sản tự tạo (CC0), GDD và hồ sơ bản quyền."}]


@router.post("/godot-coin-dash", status_code=201)
def create_sample(request: Request, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    """Tạo dự án mới từ game mẫu: chép mã nguồn vào workspace và đăng ký tài sản (nguồn 'own', CC0) vào Thư viện tài sản."""
    if not SAMPLE.is_dir():
        raise HTTPException(503, "Không tìm thấy thư mục samples/godot-coin-dash trên máy chủ.")
    manifest = json.loads((SAMPLE / "asset-manifest.json").read_text(encoding="utf-8"))
    name, n = BASE_NAME, 1
    while s.scalar(select(Project).where(Project.name == name)):
        n += 1
        name = f"{BASE_NAME} {n}"
    p = Project(name=name, genre="platformer 2D", platform="PC (Godot 4)", status="Prototype",
                description="Game mẫu Coin Dash: nhặt đủ 12 xu trong 60 giây. Dùng để thử quy trình sửa file, tài sản và bản quyền.",
                target_market="casual")
    s.add(p)
    s.flush()
    ws = request.app.state.settings.games_dir / f"{p.id}-{slugify(p.name, 'game')}"
    shutil.copytree(SAMPLE, ws, ignore=lambda d, names: [x for x in names if x in SKIP_DIRS or x.endswith(".import")], dirs_exist_ok=True)
    p.workspace_path = str(ws)
    count = 0
    for a in manifest["assets"]:
        f = ws / a["file"]
        if not f.is_file():
            continue
        s.add(Asset(project_id=p.id, name=a["name"], kind=a["kind"], source="own", license=manifest["license"],
                    license_url=manifest["license_url"], author=manifest["author"], notes=manifest["notes"],
                    file_path=a["file"], file_size=f.stat().st_size, status="draft", created_by=user.username))
        count += 1
    docs = 0
    for fname, (kind, title) in SAMPLE_DOCS.items():
        f = ws / "docs" / fname
        if f.is_file():
            s.add(ProjectDocument(project_id=p.id, kind=kind, title=title, version=1, content=f.read_text(encoding="utf-8")[:200_000],
                                  status="draft", created_by=user.username))
            docs += 1
    cases = 0
    tc = ws / "tests" / "test-cases.txt"
    if tc.is_file():
        for line in tc.read_text(encoding="utf-8").splitlines():
            parts = [x.strip() for x in line.split("|")]
            if parts and parts[0]:   # trạng thái luôn là "chưa chạy" — chưa ai chạy thử
                s.add(TestCase(project_id=p.id, title=parts[0][:200], steps=parts[1] if len(parts) > 1 else "",
                               expected=parts[2] if len(parts) > 2 else "", area=parts[3][:60] if len(parts) > 3 else "", created_by=user.username))
                cases += 1
    audit(s, user.username, "sample_created", "project", p.id, f"{p.name}: {count} tài sản, {docs} tài liệu, {cases} test case")
    s.commit()
    return {"project_id": p.id, "name": p.name, "assets": count, "documents": docs, "test_cases": cases}
