import sqlite3

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.config import Settings
from app.db import Base
from app.main import create_app
from app.migrate import migrate

from .conftest import make_client, mk_project


def test_migration_matches_models(tmp_path):
    """Nếu sửa models mà quên tạo migration, test này sẽ fail."""
    e = create_engine(f"sqlite:///{tmp_path/'m.db'}")
    assert migrate(e) == "upgraded"
    with e.connect() as c:
        diff = compare_metadata(MigrationContext.configure(c, opts={"compare_type": True, "render_as_batch": True}), Base.metadata)
    assert diff == [], diff


def _legacy_db(url):
    """DB do phiên bản cũ: schema baseline 0001 (còn cột giá), chưa có bảng alembic_version."""
    from alembic import command
    from app.migrate import make_config
    e = create_engine(url)
    with e.begin() as c:
        command.upgrade(make_config(c), "0001")
        c.exec_driver_sql("DROP TABLE alembic_version")
        c.exec_driver_sql("INSERT INTO projects (name, description, genre, platform, target_market, status, workspace_path, created_at, updated_at) "
                          "VALUES ('Cũ','','','','','Research','', '2026-01-01', '2026-01-01')")
    return e


def test_legacy_db_without_alembic_is_stamped_upgraded_and_keeps_data(tmp_path):
    e = _legacy_db(f"sqlite:///{tmp_path/'old.db'}")
    assert migrate(e) == "stamped"
    assert migrate(e) == "upgraded"  # lần sau chỉ upgrade head (không làm gì)
    with e.connect() as c:
        assert c.exec_driver_sql("SELECT name FROM projects").scalar() == "Cũ"
        cols = {r["name"] for r in inspect(c).get_columns("provider_configs")}
        assert "price_in_per_mtok" not in cols and "allow_sensitive" in cols


def test_app_starts_on_legacy_db_and_removes_old_api_providers(tmp_path):
    from fastapi.testclient import TestClient
    url = f"sqlite:///{tmp_path/'old.db'}"
    e = _legacy_db(url)
    with e.begin() as c:  # provider API của bản cũ, kèm giá
        c.exec_driver_sql("INSERT INTO provider_configs (name, enabled, default_model, allow_sensitive, last_check_status, last_check_message, price_in_per_mtok, price_out_per_mtok) "
                          "VALUES ('openai', 1, 'm', 0, 'ok', '', 1.0, 2.0)")
    app = create_app(Settings(database_url=url, secret_key="s", admin_password="Passw0rd!x", data_dir=tmp_path / "d",
                              games_dir=tmp_path / "g", frontend_dist=tmp_path / "x"))
    c = TestClient(app)
    c.headers["Authorization"] = "Bearer " + c.post("/api/auth/login", json={"username": "owner", "password": "Passw0rd!x"}).json()["token"]
    assert {p["name"] for p in c.get("/api/providers").json()} == {"claude_cli", "codex_cli", "internal"}
    assert c.get("/api/projects").json()["items"][0]["name"] == "Cũ"
    assert any(b["name"].startswith("mrk-") for b in c.get("/api/system/backups").json())  # đã sao lưu trước khi migrate


def test_manual_backup_is_valid_sqlite_with_data_and_listed(client, tmp_path):
    mk_project(client, "Backup Me")
    r = client.post("/api/system/backups")
    assert r.status_code == 201
    name = r.json()["name"]
    listed = client.get("/api/system/backups").json()
    assert name in [b["name"] for b in listed]
    path = client.app.state.settings.data_dir / "backups" / name
    con = sqlite3.connect(path)
    try:
        assert con.execute("SELECT name FROM projects").fetchone()[0] == "Backup Me"
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        con.close()


def test_backup_requires_owner_and_retention(client):
    from fastapi.testclient import TestClient
    client.post("/api/users", json={"username": "mgr1", "password": "managerpass1", "role": "manager"})
    m = TestClient(client.app)
    m.headers["Authorization"] = "Bearer " + m.post("/api/auth/login", json={"username": "mgr1", "password": "managerpass1"}).json()["token"]
    assert m.post("/api/system/backups").status_code == 403
    assert m.get("/api/system/backups").status_code == 403
    for _ in range(17):
        client.post("/api/system/backups")
    assert len(client.get("/api/system/backups").json()) == 14
