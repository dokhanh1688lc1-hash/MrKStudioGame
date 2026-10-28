"""Trung tâm CEO: gom mọi thứ cần chủ studio xử lý (kèm bước cần làm) để không bị sót."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import utcnow
from ..models import (Approval, Asset, Budget, CeoReview, Department, FileChange, Lesson, Project, ProviderConfig, Task)
from . import backup as bk
from .budget import spent
from .common import get_bool
from .guidance import explain_error

SEV = {"urgent": 0, "warn": 1, "info": 2}
STALE_RUNNING = timedelta(minutes=30)
BACKUP_STALE = timedelta(hours=48)
LIMIT_NAME = {"studio": "toàn studio", "project": "dự án", "department": "phòng ban", "provider": "AI", "model": "model", "task": "nhiệm vụ"}
PERIOD = {"daily": "hôm nay", "monthly": "tháng này", "total": "tổng cộng"}


def _item(key, sev, title, detail="", steps=None, page="", count=1, samples=None, action=""):
    return {"key": key, "severity": sev, "title": title, "detail": detail, "steps": steps or [], "page": page,
            "count": count, "samples": samples or [], "action": action}


def build(s: Session, registry, data_dir) -> dict:
    from ..routers.assets import _problems   # tránh vòng import khi nạp module
    items: list[dict] = []
    names = {d.key: d.name for d in s.scalars(select(Department))}

    if get_bool(s, "emergency_stop"):
        items.append(_item("emergency", "urgent", "Emergency Stop đang bật", "Mọi nhiệm vụ mới đang bị chặn.",
                           ["Kiểm tra lý do bạn đã bật.", "Vào Cài đặt & Bảo mật và tắt khi đã an toàn."], "settings", action="Mở Cài đặt"))

    cfgs = {c.name: c for c in s.scalars(select(ProviderConfig))}
    cli_on = [n for n in ("claude_cli", "codex_cli") if cfgs.get(n) and cfgs[n].enabled]
    for n in ("claude_cli", "codex_cli"):
        c = cfgs.get(n)
        label = "Claude Code" if n == "claude_cli" else "Codex (ChatGPT)"
        if not c or not c.enabled:
            continue
        if not registry.get(n).configured():
            g = explain_error("Không tìm thấy chương trình " + n)
            items.append(_item(f"prov_{n}", "urgent", f"{label} bật nhưng không tìm thấy chương trình trên máy", "", g["steps"], "providers", action="Mở AI Provider"))
        elif c.last_check_status == "failed":
            g = explain_error(c.last_check_message + " chưa đăng nhập" if "login" in (c.last_check_message or "").lower() else c.last_check_message or "chưa đăng nhập")
            items.append(_item(f"prov_{n}", "urgent", f"{label} kiểm tra kết nối thất bại", (c.last_check_message or "")[:200], g["steps"], "providers", action="Mở AI Provider"))
        elif c.last_check_status == "never":
            items.append(_item(f"prov_{n}", "warn", f"{label} đã bật nhưng chưa kiểm tra kết nối", "",
                               ["Vào AI Provider & Routing, bấm “Kiểm tra kết nối” để chắc chắn đã đăng nhập."], "providers", action="Kiểm tra ngay"))
    if not cli_on:
        items.append(_item("no_ai", "warn", "Chưa bật AI nào — đang dùng chế độ nội bộ (kết quả mẫu, không phải AI thật)", "",
                           ["Đăng nhập Claude Code (gõ `claude` trong CMD) và/hoặc Codex.", "Vào AI Provider & Routing → Kiểm tra kết nối → bật provider."], "providers", action="Mở AI Provider"))

    failed = s.scalars(select(Task).outerjoin(CeoReview, CeoReview.task_id == Task.id)
                       .where(Task.status == "Failed", Task.department_key != "ceo", CeoReview.id.is_(None))
                       .order_by(Task.finished_at.desc().nullslast(), Task.id.desc())).all()
    if failed:
        g0 = explain_error(failed[0].error)
        items.append(_item("failed", "urgent", f"{len(failed)} nhiệm vụ thất bại", "Mỗi việc kèm cách khắc phục bên dưới.",
                           g0["steps"] if len(failed) == 1 else ["Mở từng việc, đọc hướng dẫn khắc phục, rồi Chạy lại.", "Nếu cùng một lỗi lặp lại, hãy xử lý nguyên nhân chung (thường là đăng nhập hoặc hết lượt)."],
                           "ceo", len(failed),
                           [{"id": t.id, "title": t.title, "detail": f"{names.get(t.department_key, t.department_key)} — {explain_error(t.error)['title']}"} for t in failed[:5]],
                           "Mở Hộp thư CEO"))
    failed_ids = {t.id for t in failed}
    done = s.scalars(select(Task).outerjoin(CeoReview, CeoReview.task_id == Task.id)
                     .where(Task.status == "Completed", Task.department_key != "ceo", CeoReview.id.is_(None))
                     .order_by(Task.finished_at.desc().nullslast(), Task.id.desc())).all()
    if done:
        items.append(_item("ceo_inbox", "warn", f"{len(done)} kết quả chờ CEO quyết định", "Chấp nhận, yêu cầu sửa lại hoặc chuyển phòng khác.",
                           ["Mở Hộp thư CEO.", "Đọc kết quả, rồi bấm Chấp nhận / Yêu cầu sửa lại / Chuyển."], "ceo", len(done),
                           [{"id": t.id, "title": t.title, "detail": names.get(t.department_key, t.department_key)} for t in done[:5]], "Mở Hộp thư CEO"))

    n = s.scalar(select(func.count()).select_from(Approval).where(Approval.status == "pending")) or 0
    if n:
        rows = s.scalars(select(Approval).where(Approval.status == "pending").order_by(Approval.id.desc()).limit(5)).all()
        items.append(_item("approvals", "warn", f"{n} yêu cầu chờ phê duyệt", "Các nhiệm vụ đó sẽ không chạy cho đến khi bạn quyết định.",
                           ["Mở Approval Center.", "Xem nội dung rồi Duyệt hoặc Từ chối."], "approvals", n,
                           [{"id": a.id, "title": a.title, "detail": a.kind} for a in rows], "Mở Approval Center"))

    n = s.scalar(select(func.count()).select_from(FileChange).where(FileChange.status == "pending")) or 0
    if n:
        items.append(_item("file_changes", "warn", f"{n} đề xuất sửa file chờ bạn xem", "Chưa có gì được ghi vào máy cho đến khi bạn bấm Áp dụng.",
                           ["Vào Dự án → Mã nguồn → Sửa file trên máy.", "Xem so sánh (diff), rồi Áp dụng hoặc Từ chối."], "projects", n, [], "Mở Dự án"))

    now = utcnow()
    stale = [t for t in s.scalars(select(Task).where(Task.status == "Running")) if t.started_at and now - t.started_at > STALE_RUNNING]
    if stale:
        items.append(_item("stale", "warn", f"{len(stale)} nhiệm vụ chạy quá 30 phút", "Có thể bị treo.",
                           ["Mở Task Center, xem nhiệm vụ đang chạy.", "Nếu không có tiến triển: bấm Hủy rồi Chạy lại."], "tasks", len(stale),
                           [{"id": t.id, "title": t.title, "detail": names.get(t.department_key, t.department_key)} for t in stale[:5]], "Mở Task Center"))

    for b in s.scalars(select(Budget).where(Budget.enabled.is_(True))):
        used = spent(s, b.scope, b.scope_key, b.period)
        if used >= b.limit_runs or used >= b.limit_runs * b.warn_ratio:
            hit = used >= b.limit_runs
            where = LIMIT_NAME.get(b.scope, b.scope) + (f" {b.scope_key}" if b.scope_key else "")
            items.append(_item(f"budget_{b.id}", "urgent" if hit else "warn",
                               f"Giới hạn lượt chạy {PERIOD.get(b.period, b.period)} ({where}): {used}/{b.limit_runs}" + (" — ĐÃ ĐẦY" if hit else ""),
                               "Nhiệm vụ mới sẽ bị chặn." if hit else "Sắp chạm giới hạn.",
                               ["Vào Giới hạn lượt chạy.", "Tăng giới hạn nếu gói của bạn còn dư, hoặc chờ sang kỳ mới."], "budgets", 1, [], "Mở Giới hạn"))

    assets = s.scalars(select(Asset).where(Asset.status != "approved", Asset.status != "rejected")).all()
    prob = [a for a in assets if _problems(a)]
    if prob:
        pn = {p.id: p.name for p in s.scalars(select(Project).where(Project.id.in_({a.project_id for a in prob})))}
        items.append(_item("assets_problem", "warn", f"{len(prob)} tài sản có vấn đề bản quyền/nguồn gốc", "Không thể duyệt cho đến khi bổ sung thông tin.",
                           ["Mở Thư viện tài sản, chọn dự án.", "Bổ sung nguồn, giấy phép, tác giả (hoặc ghi chú công cụ AI), rồi Duyệt."], "assets", len(prob),
                           [{"id": a.id, "title": a.name, "detail": f"{pn.get(a.project_id, '')}: {'; '.join(_problems(a))}"} for a in prob[:5]], "Mở Thư viện tài sản"))
    ok_drafts = [a for a in assets if a.status == "draft" and not _problems(a)]
    if ok_drafts:
        items.append(_item("assets_review", "info", f"{len(ok_drafts)} tài sản hợp lệ đang chờ duyệt", "", ["Mở Thư viện tài sản và bấm Duyệt."], "assets", len(ok_drafts), [], "Mở Thư viện tài sản"))

    n = s.scalar(select(func.count()).select_from(Lesson).where(Lesson.status == "suggested")) or 0
    if n:
        items.append(_item("lessons", "info", f"{n} bài học chờ duyệt", "Duyệt để các phòng ban làm đúng ý bạn hơn ở các việc sau.",
                           ["Mở Sổ bài học.", "Duyệt, sửa hoặc xóa từng bài."], "lessons", n, [], "Mở Sổ bài học"))

    try:
        bks = bk.list_backups(data_dir)
        if not bks or datetime.now() - datetime.fromisoformat(bks[0]["created"]) > BACKUP_STALE:
            items.append(_item("backup", "info", "Chưa có bản sao lưu trong 48 giờ qua", "", ["Vào Cài đặt & Bảo mật → Sao lưu ngay."], "settings", 1, [], "Mở Cài đặt"))
    except Exception:
        pass

    items.sort(key=lambda i: (SEV[i["severity"]], -i["count"]))
    counts = {k: sum(1 for i in items if i["severity"] == k) for k in SEV}
    return {"items": items, "counts": counts, "total": len(items), "generated_at": now.isoformat()}

