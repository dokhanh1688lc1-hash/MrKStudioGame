from __future__ import annotations

import re
import unicodedata

from sqlalchemy.orm import Session

from ..models import AuditLog, SystemSetting


class EngineError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def audit(s: Session, actor: str, action: str, entity: str = "", entity_id: str | int = "", detail: str = "") -> None:
    s.add(AuditLog(actor=actor, action=action, entity=entity, entity_id=str(entity_id), detail=detail[:2000]))


DEFAULT_SETTINGS = {
    "emergency_stop": "0",
    "auto_run": "1",                   # tự chạy nhiệm vụ ngay khi được giao
    "fallback_enabled": "0",           # cho phép chuyển sang provider ngoài còn lại khi lỗi
}


def get_setting(s: Session, key: str) -> str:
    row = s.get(SystemSetting, key)
    return row.value if row else DEFAULT_SETTINGS.get(key, "")


def set_setting(s: Session, key: str, value: str) -> None:
    row = s.get(SystemSetting, key)
    if row:
        row.value = value
    else:
        s.add(SystemSetting(key=key, value=value))


def get_bool(s: Session, key: str) -> bool:
    return get_setting(s, key) == "1"


def slugify(s: str, default: str = "item", max_len: int = 50) -> str:
    """Bỏ dấu tiếng Việt, chỉ giữ a-z0-9 và dấu gạch ngang."""
    s = unicodedata.normalize("NFKD", s.replace("đ", "d").replace("Đ", "D")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:max_len] or default
