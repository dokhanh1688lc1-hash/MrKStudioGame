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


def test_legacy_db_without_alembic_is_stamped_and_keeps_data(tmp_path):
    url = f"sqlite:///{tmp_path/'old.db'}"
    e = create_engine(url)
    Base.metadata.create_all(e)  # giống DB cũ tạo bằng create_all
    with e.begin() as c:
        c.exec_driver_sql("INSERT INTO projects (name, description, genre, platform, target_market, status, workspace_path, created_at, updated_at) "
                          "VALUES ('Cũ','','','','','Research','', '2026-01-01', '2026-01-01')")
    assert migrate(e) == "stamped"
    assert migrate(e) == "upgraded"  # lần sau là upgrade head (không làm gì)
    with e.connect() as c:
        assert c.exec_driver_sql("SELECT name FROM projects").scalar() == "Cũ"
        assert "alembic_version" in inspect(c).get_table_names()


def test_app_starts_on_legacy_db(tmp_path, fake=None):
    url = f"sqlite:///{tmp_path/'old.db'}"
    Base.metadata.create_all(create_engine(url))
    app = create_app(Settings(database_url=url, secret_key="s", admin_password="Passw0rd!x", data_dir=tmp_path / "d",
                              games_dir=tmp_path / "g", frontend_dist=tmp_path / "x"))
    from fastapi.testclient import TestClient
    assert TestClient(app).get("/api/health").status_code == 200


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
