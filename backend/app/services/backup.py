"""Sao lưu database SQLite bằng API backup chính thức của SQLite (an toàn khi ứng dụng đang chạy)."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.engine import Engine

from .common import EngineError

KEEP = 14


def _db_path(engine: Engine) -> Path:
    if engine.url.get_backend_name() != "sqlite" or not engine.url.database or engine.url.database == ":memory:":
        raise EngineError(501, "Sao lưu tự động chỉ hỗ trợ SQLite dạng tệp.")
    return Path(engine.url.database)


def backup_dir(data_dir: Path) -> Path:
    d = data_dir / "backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_backups(data_dir: Path) -> list[dict]:
    d = backup_dir(data_dir)
    return [{"name": f.name, "size": f.stat().st_size, "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="seconds")}
            for f in sorted(d.glob("mrk-*.db"), reverse=True)]


def create_backup(engine: Engine, data_dir: Path) -> dict:
    src_path = _db_path(engine)
    d = backup_dir(data_dir)
    out = d / f"mrk-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.db"
    src = sqlite3.connect(src_path)
    dst = sqlite3.connect(out)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    for old in sorted(d.glob("mrk-*.db"), reverse=True)[KEEP:]:  # giữ KEEP bản mới nhất
        old.unlink(missing_ok=True)
    return {"name": out.name, "size": out.stat().st_size}


def needs_daily_backup(data_dir: Path) -> bool:
    items = list_backups(data_dir)
    if not items:
        return True
    return datetime.fromisoformat(items[0]["created"]) < datetime.now() - timedelta(hours=24)
