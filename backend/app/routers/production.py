"""Sản xuất: tài liệu dự án (có phiên bản), test case/test run, build + checklist phát hành, tài chính, analytics, tổng quan studio."""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import utcnow
from ..deps import Principal, current_user, get_db, require
from ..models import (BUILD_PLATFORMS, DOC_KINDS, SEVERITIES, AnalyticsReport, Asset, ChecklistState, FinanceRecord,
                      GameBuild, Project, ProjectDocument, Task, TestCase, TestRun, UsageRecord)
from ..services import workspace as wsvc
from ..services.common import audit
from .assets import _problems
from .projects import _ws

router = APIRouter(prefix="/api", tags=["production"])
MAX_DOC = 200_000


def _project(s: Session, pid: int) -> Project:
    p = s.get(Project, pid)
    if not p:
        raise HTTPException(404, "Không tìm thấy dự án.")
    return p


def _writable(p: Project) -> None:
    if p.status == "Archived":
        raise HTTPException(409, "Dự án đã lưu trữ (Archived).")


def _date(v: str, what: str) -> str:
    try:
        return date.fromisoformat(v).isoformat()
    except ValueError:
        raise HTTPException(422, f"{what} phải có dạng YYYY-MM-DD.")


# ======================= Tài liệu =======================
class DocIn(BaseModel):
    kind: Literal[tuple(DOC_KINDS)] = "other"  # type: ignore[valid-type]
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(default="", max_length=MAX_DOC)


class DocFromTask(BaseModel):
    kind: Literal[tuple(DOC_KINDS)] = "other"  # type: ignore[valid-type]
    title: str = Field(default="", max_length=200)


def _doc_out(d: ProjectDocument, versions: int = 1, full: bool = False) -> dict:
    out = {"id": d.id, "project_id": d.project_id, "kind": d.kind, "title": d.title, "version": d.version, "versions": versions,
           "status": d.status, "task_id": d.task_id, "created_by": d.created_by, "created_at": d.created_at, "size": len(d.content)}
    if full:
        out["content"] = d.content
    return out


def _new_version(s: Session, p: Project, kind: str, title: str, content: str, task_id: int | None, by: str) -> ProjectDocument:
    last = s.scalar(select(func.max(ProjectDocument.version)).where(ProjectDocument.project_id == p.id, ProjectDocument.title == title)) or 0
    d = ProjectDocument(project_id=p.id, kind=kind, title=title, version=last + 1, content=wsvc.redact(content), task_id=task_id, created_by=by)
    s.add(d)
    s.flush()
    audit(s, by, "document_saved", "document", d.id, f"{p.name}: {title} v{d.version}")
    return d


@router.get("/projects/{pid}/documents")
def list_documents(pid: int, kind: str = "", _: Principal = Depends(current_user), s: Session = Depends(get_db)):
    _project(s, pid)
    q = select(ProjectDocument).where(ProjectDocument.project_id == pid)
    if kind:
        q = q.where(ProjectDocument.kind == kind)
    rows = s.scalars(q.order_by(ProjectDocument.title, ProjectDocument.version.desc())).all()
    latest: dict[str, ProjectDocument] = {}
    count: dict[str, int] = {}
    for d in rows:
        count[d.title] = count.get(d.title, 0) + 1
        latest.setdefault(d.title, d)
    items = sorted(latest.values(), key=lambda d: d.created_at, reverse=True)
    return {"items": [_doc_out(d, count[d.title]) for d in items]}


@router.post("/projects/{pid}/documents", status_code=201)
def create_document(pid: int, body: DocIn, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    p = _project(s, pid)
    _writable(p)
    d = _new_version(s, p, body.kind, body.title.strip(), body.content, None, user.username)
    s.commit()
    return _doc_out(d)


@router.post("/projects/{pid}/documents/from-task/{tid}", status_code=201)
def document_from_task(pid: int, tid: int, body: DocFromTask, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    p = _project(s, pid)
    _writable(p)
    t = s.get(Task, tid)
    if not t or t.project_id != pid:
        raise HTTPException(404, "Không tìm thấy nhiệm vụ trong dự án này.")
    if t.status != "Completed" or not t.result:
        raise HTTPException(409, "Nhiệm vụ chưa hoàn thành nên chưa có kết quả để lưu.")
    d = _new_version(s, p, body.kind, (body.title or t.title).strip()[:200], t.result[:MAX_DOC], tid, user.username)
    s.commit()
    return _doc_out(d)


@router.get("/documents/{did}")
def get_document(did: int, _: Principal = Depends(current_user), s: Session = Depends(get_db)):
    d = s.get(ProjectDocument, did)
    if not d:
        raise HTTPException(404, "Không tìm thấy tài liệu.")
    vs = s.scalars(select(ProjectDocument).where(ProjectDocument.project_id == d.project_id, ProjectDocument.title == d.title)
                   .order_by(ProjectDocument.version.desc())).all()
    out = _doc_out(d, len(vs), full=True)
    out["history"] = [{"id": v.id, "version": v.version, "status": v.status, "created_by": v.created_by, "created_at": v.created_at} for v in vs]
    return out


@router.post("/documents/{did}/status")
def set_document_status(did: int, body: dict, user: Principal = Depends(require("owner")), s: Session = Depends(get_db)):
    d = s.get(ProjectDocument, did)
    if not d:
        raise HTTPException(404, "Không tìm thấy tài liệu.")
    if body.get("status") not in ("draft", "approved"):
        raise HTTPException(422, "Trạng thái không hợp lệ.")
    d.status = body["status"]
    audit(s, user.username, f"document_{d.status}", "document", d.id, f"{d.title} v{d.version}")
    s.commit()
    return _doc_out(d)


@router.delete("/documents/{did}", status_code=204)
def delete_document(did: int, user: Principal = Depends(require("owner")), s: Session = Depends(get_db)):
    d = s.get(ProjectDocument, did)
    if not d:
        raise HTTPException(404, "Không tìm thấy tài liệu.")
    audit(s, user.username, "document_deleted", "document", d.id, f"{d.title} v{d.version}")
    s.delete(d)
    s.commit()


# ======================= Kiểm thử =======================
class CaseIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    area: str = Field(default="", max_length=60)
    steps: str = Field(default="", max_length=8000)
    expected: str = Field(default="", max_length=4000)


class CaseImport(BaseModel):
    lines: str = Field(min_length=1, max_length=40000)   # mỗi dòng: tiêu đề | các bước | kết quả mong đợi


class RunIn(BaseModel):
    status: Literal["passed", "failed", "blocked"]
    severity: Literal["", "low", "medium", "high", "critical"] = ""
    notes: str = Field(default="", max_length=8000)
    build_id: int | None = None


def _case_out(c: TestCase, last_run: TestRun | None = None) -> dict:
    return {"id": c.id, "project_id": c.project_id, "title": c.title, "area": c.area, "steps": c.steps, "expected": c.expected,
            "status": c.status, "last_run_at": c.last_run_at,
            "severity": last_run.severity if last_run and c.status == "failed" else "",
            "last_notes": last_run.notes if last_run else ""}


def _last_runs(s: Session, ids: list[int]) -> dict[int, TestRun]:
    out: dict[int, TestRun] = {}
    for r in s.scalars(select(TestRun).where(TestRun.test_case_id.in_(ids or [0])).order_by(TestRun.id)):
        out[r.test_case_id] = r
    return out


def test_summary(s: Session, pid: int) -> dict:
    cases = s.scalars(select(TestCase).where(TestCase.project_id == pid)).all()
    last = _last_runs(s, [c.id for c in cases])
    c = {k: sum(1 for x in cases if x.status == k) for k in ("passed", "failed", "blocked", "not_run")}
    sev = {k: 0 for k in SEVERITIES}
    for x in cases:
        if x.status == "failed" and x.id in last and last[x.id].severity:
            sev[last[x.id].severity] += 1
    return {"total": len(cases), **c, "open_bugs": c["failed"], "bugs_by_severity": sev}


@router.get("/projects/{pid}/test-cases")
def list_cases(pid: int, status: str = "", _: Principal = Depends(current_user), s: Session = Depends(get_db)):
    _project(s, pid)
    q = select(TestCase).where(TestCase.project_id == pid)
    if status:
        q = q.where(TestCase.status == status)
    rows = s.scalars(q.order_by(TestCase.id.desc()).limit(500)).all()
    last = _last_runs(s, [c.id for c in rows])
    return {"items": [_case_out(c, last.get(c.id)) for c in rows], "summary": test_summary(s, pid)}


@router.post("/projects/{pid}/test-cases", status_code=201)
def create_case(pid: int, body: CaseIn, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    p = _project(s, pid)
    _writable(p)
    c = TestCase(project_id=pid, title=body.title.strip(), area=body.area.strip(), steps=body.steps, expected=body.expected, created_by=user.username)
    s.add(c)
    s.flush()
    audit(s, user.username, "testcase_created", "test_case", c.id, c.title)
    s.commit()
    return _case_out(c)


@router.post("/projects/{pid}/test-cases/import", status_code=201)
def import_cases(pid: int, body: CaseImport, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    p = _project(s, pid)
    _writable(p)
    made = 0
    for line in body.lines.splitlines():
        parts = [x.strip() for x in line.split("|")]
        if not parts or not parts[0]:
            continue
        if made >= 100:
            raise HTTPException(422, "Tối đa 100 test case mỗi lần nhập.")
        s.add(TestCase(project_id=pid, title=parts[0][:200], steps=parts[1] if len(parts) > 1 else "", expected=parts[2] if len(parts) > 2 else "",
                       area=parts[3][:60] if len(parts) > 3 else "", created_by=user.username))
        made += 1
    if not made:
        raise HTTPException(422, "Không có dòng hợp lệ (định dạng: tiêu đề | các bước | kết quả mong đợi).")
    audit(s, user.username, "testcases_imported", "project", pid, f"{made} test case")
    s.commit()
    return {"created": made}


@router.post("/test-cases/{cid}/runs", status_code=201)
def record_run(cid: int, body: RunIn, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    """Ghi kết quả một lần chạy test (do người hoặc công cụ test thật thực hiện). Trạng thái chỉ đổi qua đây."""
    c = s.get(TestCase, cid)
    if not c:
        raise HTTPException(404, "Không tìm thấy test case.")
    if body.status in ("failed", "blocked") and not body.notes.strip():
        raise HTTPException(422, "Cần ghi mô tả lỗi/lý do bị chặn.")
    if body.status == "failed" and not body.severity:
        raise HTTPException(422, "Cần chọn mức độ nghiêm trọng của lỗi.")
    if body.status != "failed" and body.severity:
        raise HTTPException(422, "Mức độ nghiêm trọng chỉ dùng cho test thất bại.")
    if body.build_id and (not s.get(GameBuild, body.build_id) or s.get(GameBuild, body.build_id).project_id != c.project_id):
        raise HTTPException(422, "Bản build không thuộc dự án này.")
    r = TestRun(test_case_id=cid, status=body.status, severity=body.severity, notes=wsvc.redact(body.notes.strip()), build_id=body.build_id,
                run_by=user.username)
    s.add(r)
    c.status, c.last_run_at = body.status, utcnow()
    audit(s, user.username, f"testrun_{body.status}", "test_case", cid, c.title)
    s.commit()
    return {"id": r.id, "status": r.status, "case_status": c.status}


@router.get("/test-cases/{cid}/runs")
def list_runs(cid: int, _: Principal = Depends(current_user), s: Session = Depends(get_db)):
    if not s.get(TestCase, cid):
        raise HTTPException(404, "Không tìm thấy test case.")
    rows = s.scalars(select(TestRun).where(TestRun.test_case_id == cid).order_by(TestRun.id.desc()).limit(100)).all()
    return {"items": [{"id": r.id, "status": r.status, "severity": r.severity, "notes": r.notes, "build_id": r.build_id,
                       "run_by": r.run_by, "created_at": r.created_at} for r in rows]}


@router.delete("/test-cases/{cid}", status_code=204)
def delete_case(cid: int, user: Principal = Depends(require("owner")), s: Session = Depends(get_db)):
    c = s.get(TestCase, cid)
    if not c:
        raise HTTPException(404, "Không tìm thấy test case.")
    for r in s.scalars(select(TestRun).where(TestRun.test_case_id == cid)):
        s.delete(r)
    audit(s, user.username, "testcase_deleted", "test_case", cid, c.title)
    s.delete(c)
    s.commit()


# ======================= Build =======================
class BuildIn(BaseModel):
    version: str = Field(min_length=1, max_length=40, pattern=r"^[0-9A-Za-z][0-9A-Za-z._+\-]*$")
    platform: Literal[tuple(BUILD_PLATFORMS)] = "windows"  # type: ignore[valid-type]
    status: Literal["planned", "ready", "failed"] = "planned"
    file_path: str = Field(default="", max_length=300)
    changelog: str = Field(default="", max_length=8000)
    notes: str = Field(default="", max_length=4000)


def _build_out(b: GameBuild) -> dict:
    return {"id": b.id, "project_id": b.project_id, "version": b.version, "platform": b.platform, "status": b.status,
            "file_path": b.file_path, "changelog": b.changelog, "notes": b.notes, "created_by": b.created_by, "created_at": b.created_at}


@router.get("/projects/{pid}/builds")
def list_builds(pid: int, _: Principal = Depends(current_user), s: Session = Depends(get_db)):
    _project(s, pid)
    return {"items": [_build_out(b) for b in s.scalars(select(GameBuild).where(GameBuild.project_id == pid).order_by(GameBuild.id.desc()))]}


@router.post("/projects/{pid}/builds", status_code=201)
def create_build(pid: int, body: BuildIn, request: Request, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    p, ws = _ws(request, s, pid)
    _writable(p)
    fp = body.file_path.strip().replace("\\", "/")
    if fp:
        try:
            f = wsvc.safe_resolve(ws, fp)
        except Exception:
            raise HTTPException(422, "Đường dẫn tệp build không hợp lệ.")
        if not f.is_file():
            raise HTTPException(422, "Không tìm thấy tệp build trong workspace dự án.")
    elif body.status == "ready":
        raise HTTPException(422, "Build 'ready' cần có tệp build trong workspace (đường dẫn tương đối).")
    if s.scalar(select(GameBuild).where(GameBuild.project_id == pid, GameBuild.version == body.version, GameBuild.platform == body.platform)):
        raise HTTPException(409, "Phiên bản này cho nền tảng này đã tồn tại.")
    b = GameBuild(project_id=pid, version=body.version, platform=body.platform, status=body.status, file_path=fp,
                  changelog=body.changelog, notes=body.notes, created_by=user.username)
    s.add(b)
    s.flush()
    audit(s, user.username, "build_created", "build", b.id, f"{p.name} {b.version} {b.platform} ({b.status})")
    s.commit()
    return _build_out(b)


@router.post("/builds/{bid}/status")
def set_build_status(bid: int, body: dict, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    b = s.get(GameBuild, bid)
    if not b:
        raise HTTPException(404, "Không tìm thấy build.")
    new = body.get("status")
    if new not in ("planned", "ready", "failed", "released"):
        raise HTTPException(422, "Trạng thái không hợp lệ.")
    if new == "ready" and not b.file_path:
        raise HTTPException(422, "Build 'ready' cần có tệp build.")
    if new == "released":
        if user.role != "owner":
            raise HTTPException(403, "Chỉ chủ studio được đánh dấu đã phát hành.")
        if b.status not in ("ready", "released"):
            raise HTTPException(409, "Chỉ build 'ready' mới được đánh dấu đã phát hành.")
        cl = checklist(s, b.project_id)
        if not cl["ready"]:
            raise HTTPException(409, "Checklist phát hành chưa đạt: " + "; ".join(i["label"] for i in cl["items"] if not i["done"]))
    b.status = new
    audit(s, user.username, f"build_{new}", "build", b.id, f"{b.version} {b.platform}")
    s.commit()
    return _build_out(b)


# ======================= Checklist phát hành =======================
# (key, nhãn, tự động?)  — mục tự động tính từ dữ liệu thật; mục còn lại do người xác nhận.
CHECKLIST = [
    ("docs_approved", "Có GDD đã được chủ studio duyệt", True),
    ("assets_approved", "Mọi tài sản của dự án đã được duyệt (không còn nháp/bị từ chối)", True),
    ("tests_pass", "Có test case và tất cả đều Passed", True),
    ("no_serious_bugs", "Không còn lỗi mức High/Critical chưa sửa", True),
    ("build_ready", "Có ít nhất một bản build sẵn sàng", True),
    ("licenses_reviewed", "Giấy phép/nguồn gốc đã được người có chuyên môn rà soát (AI không thay thế được)", False),
    ("store_metadata", "Metadata cửa hàng sẵn sàng (mô tả, ảnh chụp màn hình, phân loại độ tuổi)", False),
    ("privacy_policy", "Chính sách quyền riêng tư và điều khoản phù hợp nền tảng", False),
    ("monetization_tested", "Quảng cáo/mua hàng đã thử trong môi trường test (nếu có)", False),
    ("owner_approval", "Chủ studio phê duyệt phát hành", False),
]
CHECK_KEYS = {k: (label, auto) for k, label, auto in CHECKLIST}


def checklist(s: Session, pid: int) -> dict:
    states = {c.key: c for c in s.scalars(select(ChecklistState).where(ChecklistState.project_id == pid))}
    assets = s.scalars(select(Asset).where(Asset.project_id == pid)).all()
    ts = test_summary(s, pid)
    auto = {
        "docs_approved": (bool(s.scalar(select(func.count()).select_from(ProjectDocument).where(
            ProjectDocument.project_id == pid, ProjectDocument.kind == "gdd", ProjectDocument.status == "approved"))), "chưa có GDD được duyệt"),
        "assets_approved": (all(a.status == "approved" and not _problems(a) for a in assets),
                            f"{sum(1 for a in assets if a.status != 'approved')} tài sản chưa duyệt" if assets else ""),
        "tests_pass": (ts["total"] > 0 and ts["passed"] == ts["total"], f"{ts['passed']}/{ts['total']} Passed" if ts["total"] else "chưa có test case"),
        "no_serious_bugs": (ts["bugs_by_severity"]["high"] + ts["bugs_by_severity"]["critical"] == 0,
                            f"{ts['bugs_by_severity']['high'] + ts['bugs_by_severity']['critical']} lỗi nghiêm trọng"),
        "build_ready": (bool(s.scalar(select(func.count()).select_from(GameBuild).where(
            GameBuild.project_id == pid, GameBuild.status.in_(("ready", "released"))))), "chưa có build sẵn sàng"),
    }
    items = []
    for key, label, is_auto in CHECKLIST:
        if is_auto:
            done, detail = auto[key]
            items.append({"key": key, "label": label, "auto": True, "done": done, "detail": "" if done else detail, "note": "", "by": "", "at": None})
        else:
            st = states.get(key)
            items.append({"key": key, "label": label, "auto": False, "done": bool(st and st.done), "detail": "", "note": st.note if st else "",
                          "by": st.by if st and st.done else "", "at": st.at if st and st.done else None})
    return {"items": items, "done": sum(i["done"] for i in items), "total": len(items), "ready": all(i["done"] for i in items)}


@router.get("/projects/{pid}/release-checklist")
def get_checklist(pid: int, _: Principal = Depends(current_user), s: Session = Depends(get_db)):
    _project(s, pid)
    return checklist(s, pid)


@router.put("/projects/{pid}/release-checklist/{key}")
def set_check(pid: int, key: str, body: dict, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    p = _project(s, pid)
    _writable(p)
    if key not in CHECK_KEYS:
        raise HTTPException(404, "Không có mục checklist này.")
    if CHECK_KEYS[key][1]:
        raise HTTPException(422, "Mục này tự động tính từ dữ liệu thật, không đánh dấu tay được.")
    if key == "owner_approval" and user.role != "owner":
        raise HTTPException(403, "Chỉ chủ studio được phê duyệt phát hành.")
    done = bool(body.get("done"))
    st = s.scalar(select(ChecklistState).where(ChecklistState.project_id == pid, ChecklistState.key == key))
    if not st:
        st = ChecklistState(project_id=pid, key=key)
        s.add(st)
    st.done, st.note, st.by, st.at = done, str(body.get("note", ""))[:300], user.username, utcnow()
    audit(s, user.username, "checklist_set", "project", pid, f"{key}={done}")
    s.commit()
    return checklist(s, pid)


# ======================= Tài chính =======================
FIN_CATEGORIES = ["ai_subscription", "tool", "asset_purchase", "ads", "iap", "store_fee", "contractor", "other"]


class FinanceIn(BaseModel):
    kind: Literal["cost", "revenue"]
    category: Literal[tuple(FIN_CATEGORIES)] = "other"  # type: ignore[valid-type]
    amount: str = Field(min_length=1, max_length=20)     # số thập phân, tối đa 2 chữ số sau dấu phẩy
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    occurred_on: str
    note: str = Field(default="", max_length=300)
    estimated: bool = False
    project_id: int | None = None


def _cents(v: str) -> int:
    try:
        d = Decimal(v.replace(",", "."))
    except InvalidOperation:
        raise HTTPException(422, "Số tiền không hợp lệ.")
    if d <= 0 or d > Decimal("1000000000") or d != d.quantize(Decimal("0.01")):
        raise HTTPException(422, "Số tiền phải > 0, tối đa 2 chữ số thập phân.")
    return int(d * 100)


def _fin_out(r: FinanceRecord) -> dict:
    return {"id": r.id, "project_id": r.project_id, "kind": r.kind, "category": r.category, "amount": f"{r.amount_cents / 100:.2f}",
            "currency": r.currency, "occurred_on": r.occurred_on, "note": r.note, "estimated": r.estimated, "confirmed": r.confirmed,
            "created_by": r.created_by, "confirmed_by": r.confirmed_by}


@router.get("/finance/records")
def list_finance(project_id: int | None = None, kind: str = "", limit: int = Query(100, ge=1, le=500),
                 _: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    q = select(FinanceRecord)
    if project_id:
        q = q.where(FinanceRecord.project_id == project_id)
    if kind:
        q = q.where(FinanceRecord.kind == kind)
    return {"items": [_fin_out(r) for r in s.scalars(q.order_by(FinanceRecord.occurred_on.desc(), FinanceRecord.id.desc()).limit(limit))]}


@router.post("/finance/records", status_code=201)
def create_finance(body: FinanceIn, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    if body.project_id:
        _writable(_project(s, body.project_id))
    if body.kind == "revenue" and body.estimated:
        raise HTTPException(422, "Doanh thu không được ghi là ước tính — chỉ ghi doanh thu thật đã nhận.")
    r = FinanceRecord(project_id=body.project_id, kind=body.kind, category=body.category, amount_cents=_cents(body.amount),
                      currency=body.currency, occurred_on=_date(body.occurred_on, "Ngày"), note=body.note.strip(),
                      estimated=body.estimated, confirmed=False, created_by=user.username)
    s.add(r)
    s.flush()
    audit(s, user.username, f"finance_{r.kind}_created", "finance", r.id, f"{r.amount_cents / 100:.2f} {r.currency} {r.category}")
    s.commit()
    return _fin_out(r)


@router.post("/finance/records/{rid}/confirm")
def confirm_finance(rid: int, user: Principal = Depends(require("owner")), s: Session = Depends(get_db)):
    r = s.get(FinanceRecord, rid)
    if not r:
        raise HTTPException(404, "Không tìm thấy bản ghi.")
    r.confirmed, r.confirmed_by = True, user.username
    audit(s, user.username, "finance_confirmed", "finance", r.id, f"{r.kind} {r.amount_cents / 100:.2f} {r.currency}")
    s.commit()
    return _fin_out(r)


@router.delete("/finance/records/{rid}", status_code=204)
def delete_finance(rid: int, user: Principal = Depends(require("owner")), s: Session = Depends(get_db)):
    r = s.get(FinanceRecord, rid)
    if not r:
        raise HTTPException(404, "Không tìm thấy bản ghi.")
    audit(s, user.username, "finance_deleted", "finance", r.id, f"{r.kind} {r.amount_cents / 100:.2f} {r.currency}")
    s.delete(r)
    s.commit()


@router.get("/finance/summary")
def finance_summary(project_id: int | None = None, _: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    """Tổng hợp theo từng loại tiền (không quy đổi). Chỉ tính doanh thu đã xác nhận; chi phí ước tính tách riêng."""
    q = select(FinanceRecord)
    if project_id:
        q = q.where(FinanceRecord.project_id == project_id)
    cur: dict[str, dict] = {}
    for r in s.scalars(q):
        c = cur.setdefault(r.currency, {"currency": r.currency, "cost_actual": 0, "cost_estimated": 0, "revenue_confirmed": 0, "revenue_pending": 0})
        if r.kind == "cost":
            c["cost_estimated" if r.estimated else "cost_actual"] += r.amount_cents
        else:
            c["revenue_confirmed" if r.confirmed else "revenue_pending"] += r.amount_cents
    out = []
    for c in cur.values():
        out.append({**{k: (v / 100 if k != "currency" else v) for k, v in c.items()}, "profit": (c["revenue_confirmed"] - c["cost_actual"]) / 100})
    start = utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    uq = select(UsageRecord.provider, UsageRecord.department_key, func.count()).where(UsageRecord.created_at >= start)
    if project_id:
        uq = uq.where(UsageRecord.project_id == project_id)
    runs = [{"provider": p, "department_key": d, "runs": n} for p, d, n in s.execute(uq.group_by(UsageRecord.provider, UsageRecord.department_key))]
    return {"currencies": sorted(out, key=lambda x: x["currency"]), "ai_runs_this_month": runs,
            "note": "AI chạy qua gói thuê bao Claude/ChatGPT nên chỉ đếm số lượt chạy, không quy ra tiền. Hãy nhập phí gói thuê bao như một khoản chi phí nếu cần."}


# ======================= Analytics =======================
class AnalyticsIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=3, max_length=200)
    period_start: str
    period_end: str
    metrics: dict[str, float] = {}
    limitations: str = Field(min_length=3, max_length=4000)
    summary: str = Field(default="", max_length=20000)


def _rep_out(r: AnalyticsReport, full: bool = True) -> dict:
    return {"id": r.id, "project_id": r.project_id, "title": r.title, "source": r.source, "period_start": r.period_start,
            "period_end": r.period_end, "metrics": json.loads(r.metrics or "{}"), "limitations": r.limitations,
            "summary": r.summary if full else "", "created_by": r.created_by, "created_at": r.created_at}


@router.get("/projects/{pid}/analytics")
def list_reports(pid: int, _: Principal = Depends(current_user), s: Session = Depends(get_db)):
    _project(s, pid)
    return {"items": [_rep_out(r) for r in s.scalars(select(AnalyticsReport).where(AnalyticsReport.project_id == pid).order_by(AnalyticsReport.id.desc()))]}


@router.post("/projects/{pid}/analytics", status_code=201)
def create_report(pid: int, body: AnalyticsIn, user: Principal = Depends(require("manager")), s: Session = Depends(get_db)):
    p = _project(s, pid)
    _writable(p)
    a, b = _date(body.period_start, "Ngày bắt đầu"), _date(body.period_end, "Ngày kết thúc")
    if a > b:
        raise HTTPException(422, "Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.")
    if len(body.metrics) > 40 or any(not re.match(r"^[\w .%/\-()]{1,60}$", k) for k in body.metrics):
        raise HTTPException(422, "Tên chỉ số không hợp lệ hoặc quá nhiều chỉ số (tối đa 40).")
    r = AnalyticsReport(project_id=pid, title=body.title.strip(), source=body.source.strip(), period_start=a, period_end=b,
                        metrics=json.dumps(body.metrics, ensure_ascii=False), limitations=body.limitations.strip(),
                        summary=wsvc.redact(body.summary), created_by=user.username)
    s.add(r)
    s.flush()
    audit(s, user.username, "analytics_report_created", "analytics", r.id, f"{p.name}: {r.title}")
    s.commit()
    return _rep_out(r)


@router.delete("/analytics/{rid}", status_code=204)
def delete_report(rid: int, user: Principal = Depends(require("owner")), s: Session = Depends(get_db)):
    r = s.get(AnalyticsReport, rid)
    if not r:
        raise HTTPException(404, "Không tìm thấy báo cáo.")
    audit(s, user.username, "analytics_report_deleted", "analytics", rid, r.title)
    s.delete(r)
    s.commit()


# ======================= Studio Manager =======================
@router.get("/studio/overview")
def studio_overview(_: Principal = Depends(current_user), s: Session = Depends(get_db)):
    """Tổng quan mọi dự án: tiến độ, tài sản, kiểm thử, build, checklist phát hành."""
    out = []
    for p in s.scalars(select(Project).order_by(Project.id.desc())):
        by = dict(s.execute(select(Task.status, func.count()).where(Task.project_id == p.id).group_by(Task.status)).all())
        total = sum(by.values())
        active = total - by.get("Cancelled", 0)
        assets = s.scalars(select(Asset).where(Asset.project_id == p.id)).all()
        ts = test_summary(s, p.id)
        cl = checklist(s, p.id)
        out.append({"id": p.id, "name": p.name, "status": p.status, "genre": p.genre, "platform": p.platform,
                    "tasks": {"total": total, "done": by.get("Completed", 0), "running": by.get("Running", 0), "failed": by.get("Failed", 0),
                              "pct": round(100 * by.get("Completed", 0) / active) if active else 0},
                    "assets": {"total": len(assets), "approved": sum(a.status == "approved" for a in assets), "problems": sum(bool(_problems(a)) for a in assets)},
                    "tests": ts, "builds_ready": s.scalar(select(func.count()).select_from(GameBuild).where(GameBuild.project_id == p.id, GameBuild.status.in_(("ready", "released")))),
                    "docs": s.scalar(select(func.count(func.distinct(ProjectDocument.title))).where(ProjectDocument.project_id == p.id)),
                    "release": {"done": cl["done"], "total": cl["total"], "ready": cl["ready"]}})
    return {"items": out}
