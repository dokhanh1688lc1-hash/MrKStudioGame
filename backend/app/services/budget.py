"""Ước tính token và giới hạn số lượt chạy AI.

Dùng gói thuê bao (Claude Code / Codex) nên không tính tiền theo token; thay vào đó giới hạn SỐ LƯỢT CHẠY
(mỗi lần AI trả kết quả thành công = 1 lượt) theo phạm vi và kỳ, để không dùng hết hạn mức gói của bạn.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import utcnow
from ..models import Budget, UsageRecord


def estimate_tokens(text: str) -> int:
    """Ước lượng thô ~4 ký tự/token. Chỉ là ước tính."""
    return max(1, math.ceil(len(text) / 4))


def _period_start(period: str) -> datetime | None:
    now = utcnow()
    if period == "daily":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "monthly":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return None


def spent(s: Session, scope: str, key: str, period: str) -> int:
    """Số lượt chạy đã dùng trong phạm vi/kỳ."""
    q = select(func.count(UsageRecord.id))
    if scope == "project":
        q = q.where(UsageRecord.project_id == int(key))
    elif scope == "department":
        q = q.where(UsageRecord.department_key == key)
    elif scope == "provider":
        q = q.where(UsageRecord.provider == key)
    elif scope == "model":
        q = q.where(UsageRecord.model == key)
    elif scope == "task":
        q = q.where(UsageRecord.task_id == int(key))
    start = _period_start(period)
    if start:
        q = q.where(UsageRecord.created_at >= start)
    return int(s.scalar(q) or 0)


@dataclass
class Verdict:
    ok: bool = True
    message: str = ""
    warnings: list[str] = field(default_factory=list)


def check_limits(s: Session, *, project_id: int, department_key: str, provider: str, model: str,
                 task_id: int) -> Verdict:
    """Kiểm tra trước mỗi lượt gọi: lượt đã dùng + 1 không được vượt giới hạn."""
    v = Verdict()
    keys = {"studio": "", "project": str(project_id), "department": department_key,
            "provider": provider, "model": model, "task": str(task_id)}
    for b in s.scalars(select(Budget).where(Budget.enabled.is_(True))).all():
        if b.scope not in keys or (b.scope != "studio" and b.scope_key != keys[b.scope]):
            continue
        used = spent(s, b.scope, b.scope_key or "0", b.period)
        if used + 1 > b.limit_runs:
            return Verdict(False, f"Hết giới hạn lượt chạy {b.scope} {b.scope_key} ({b.period}): đã dùng {used}/{b.limit_runs}.")
        if used + 1 >= b.limit_runs * b.warn_ratio:
            v.warnings.append(f"Giới hạn {b.scope} {b.scope_key} ({b.period}) đã dùng ≥ {int(b.warn_ratio*100)}%.")
    return v
