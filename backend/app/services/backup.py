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


def restore_backup(engine: Engine, data_dir: Path, name: str) -> dict:
    """Khôi phục DB đang chạy từ một bản sao lưu. Luôn tạo bản an toàn của trạng thái hiện tại trước."""
    if "/" in name or "\\" in name or not (name.startswith("mrk-") and name.endswith(".db")):
        raise EngineError(400, "Tên bản sao lưu không hợp lệ.")
    src_path = backup_dir(data_dir) / name
    if not src_path.is_file():
        raise EngineError(404, "Không tìm thấy bản sao lưu.")
    live = _db_path(engine)
    try:
        chk = sqlite3.connect(f"file:{src_path.as_posix()}?mode=ro", uri=True)
        try:
            ok = chk.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            has = chk.execute("SELECT 1 FROM sqlite_master WHERE name='alembic_version'").fetchone() is not None
        finally:
            chk.close()
    except sqlite3.DatabaseError:
        ok = has = False
    if not (ok and has):
        raise EngineError(422, "Bản sao lưu bị hỏng hoặc không phải DB của MrK Studio.")
    safety = create_backup(engine, data_dir)  # cho phép hoàn tác việc khôi phục
    src = sqlite3.connect(f"file:{src_path.as_posix()}?mode=ro", uri=True)
    dst = sqlite3.connect(live, timeout=30)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    engine.dispose()
    return {"restored": name, "safety_backup": safety["name"]}
