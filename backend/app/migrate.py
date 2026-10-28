"""Chạy Alembic khi khởi động. Database cũ (tạo bằng create_all, chưa có alembic_version) được 'stamp' về baseline."""
from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

SCRIPTS = Path(__file__).resolve().parents[1] / "migrations"


def make_config(connection) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(SCRIPTS))
    cfg.attributes["connection"] = connection
    return cfg


def migrate(engine) -> str:
    """Trả về 'stamped' (DB cũ), 'upgraded' (đã chạy upgrade head)."""
    with engine.begin() as conn:
        cfg = make_config(conn)
        tables = set(inspect(conn).get_table_names())
        if "alembic_version" not in tables and "projects" in tables:
            command.stamp(cfg, "head")
            return "stamped"
        command.upgrade(cfg, "head")
        return "upgraded"
