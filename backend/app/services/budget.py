"""Ước tính chi phí và kiểm tra ngân sách. Không bịa giá: giá chưa cấu hình → chi phí = None."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import utcnow
from ..models import Budget, ProviderConfig, UsageRecord


def estimate_tokens(text: str) -> int:
    """Ước lượng thô ~4 ký tự/token. Chỉ là ước tính."""
    return max(1, math.ceil(len(text) / 4))


def compute_cost(cfg: ProviderConfig, in_tok: int | None, out_tok: int | None) -> float | None:
    """CLI (gói thuê bao) và chế độ nội bộ không tính tiền theo token → 0 USD."""
    return 0.0


def _period_start(period: str) -> datetime | None:
    now = utcnow()
    if period == "daily":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "monthly":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return None


def spent(s: Session, scope: str, key: str, period: str) -> float:
    q = select(func.coalesce(func.sum(UsageRecord.cost_usd), 0.0))
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
    return float(s.scalar(q) or 0.0)


@dataclass
class Verdict:
    ok: bool = True
    message: str = ""
    warnings: list[str] = field(default_factory=list)


def check_budget(s: Session, *, project_id: int, department_key: str, provider: str, model: str,
                 task_id: int, est_cost: float | None, external: bool, task_limit: float | None,
                 task_spent: float) -> Verdict:
    v = Verdict()
    if task_limit is not None:
        if external and est_cost is None:
            return Verdict(False, "Nhiệm vụ có giới hạn ngân sách nhưng chưa cấu hình giá cho provider này.")
        if est_cost is not None and task_spent + est_cost > task_limit:
            return Verdict(False, f"Vượt hạn mức nhiệm vụ: đã dùng {task_spent:.4f} + ước tính {est_cost:.4f} > {task_limit:.4f} USD.")
    keys = {"studio": "", "project": str(project_id), "department": department_key,
            "provider": provider, "model": model, "task": str(task_id)}
    rows = s.scalars(select(Budget).where(Budget.enabled.is_(True))).all()
    for b in rows:
        if b.scope not in keys or (b.scope != "studio" and b.scope_key != keys[b.scope]):
            continue
        if external and est_cost is None:
            return Verdict(False, f"Có ngân sách ({b.scope}/{b.period}) nhưng chưa cấu hình giá cho '{provider}' nên không thể kiểm soát chi phí. Hãy cấu hình giá hoặc dùng chế độ nội bộ.")
        used = spent(s, b.scope, b.scope_key or "0", b.period)
        add = est_cost or 0.0
        if used + add > b.limit_usd:
            return Verdict(False, f"Vượt ngân sách {b.scope} {b.scope_key} ({b.period}): đã dùng {used:.4f} + ước tính {add:.4f} > {b.limit_usd:.4f} USD.")
        if used + add >= b.limit_usd * b.warn_ratio:
            v.warnings.append(f"Ngân sách {b.scope} {b.scope_key} ({b.period}) đã dùng ≥ {int(b.warn_ratio*100)}%.")
    return v
