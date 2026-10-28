import pytest

from .conftest import mk_project

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


def _make(client, pid, name="Hero", source="own", file=("hero.png", PNG, "image/png"), **extra):
    data = {"name": name, "source": source, **extra}
    files = {"file": file} if file else None
    return client.post(f"/api/projects/{pid}/assets", data=data, files=files)


def test_create_with_file_download_and_list(client):
    p = mk_project(client)
    r = _make(client, p["id"])
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["kind"] == "image" and a["has_file"] and a["file_size"] == len(PNG) and a["status"] == "draft" and a["problems"] == []
    d = client.get(f"/api/assets/{a['id']}/file")
    assert d.status_code == 200 and d.content == PNG and "attachment" in d.headers["content-disposition"]
    assert d.headers["x-content-type-options"] == "nosniff"
    lst = client.get(f"/api/projects/{p['id']}/assets").json()
    assert lst["summary"]["total"] == 1 and lst["items"][0]["name"] == "Hero"


def test_metadata_only_asset_and_problems(client):
    p = mk_project(client)
    a = _make(client, p["id"], "Nhạc nền", "unknown", file=None, kind="audio").json()
    assert not a["has_file"] and "Chưa rõ nguồn gốc" in a["problems"]
    b = _make(client, p["id"], "Font", "open_license", file=None, kind="font").json()
    assert set(b["problems"]) == {"Thiếu thông tin giấy phép", "Thiếu tác giả/nhà cung cấp"}
    c = _make(client, p["id"], "Bg", "ai_generated", file=None, kind="image").json()
    assert any("AI" in x for x in c["problems"])
    assert client.get(f"/api/projects/{p['id']}/assets").json()["summary"]["with_problems"] == 3


@pytest.mark.parametrize("fname", ["run.exe", "evil.svg", "x.bat", "a.py", "noext", "key.pem", ".env"])
def test_disallowed_files(client, fname):
    p = mk_project(client)
    r = _make(client, p["id"], file=(fname, b"xx", "application/octet-stream"))
    assert r.status_code in (415, 422), (fname, r.status_code)


def test_path_traversal_filename_is_flattened(client):
    p = mk_project(client)
    a = _make(client, p["id"], file=("../../../evil.png", PNG, "image/png")).json()
    f = client.get(f"/api/assets/{a['id']}/file")
    assert f.status_code == 200
    from pathlib import Path
    ws = Path(client.get(f"/api/projects/{p['id']}").json()["workspace_path"])
    assert (ws / "assets").is_dir() and not (ws.parent / "evil.png").exists() and not (ws.parent.parent / "evil.png").exists()


def test_approval_rules_and_permissions(client):
    p = mk_project(client)
    bad = _make(client, p["id"], "X", "unknown", file=None, kind="other").json()
    assert client.post(f"/api/assets/{bad['id']}/decision", json={"status": "approved"}).status_code == 422
    good = _make(client, p["id"]).json()
    assert client.post(f"/api/assets/{good['id']}/decision", json={"status": "approved"}).json()["status"] == "approved"
    # sửa nguồn gốc sau khi duyệt → quay về nháp
    assert client.patch(f"/api/assets/{good['id']}", json={"license": "CC0"}).json()["status"] == "draft"
    client.post("/api/users", json={"username": "mgr1", "password": "Passw0rd!x", "role": "manager"})
    tok = client.post("/api/auth/login", json={"username": "mgr1", "password": "Passw0rd!x"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert client.post(f"/api/assets/{good['id']}/decision", json={"status": "approved"}, headers=h).status_code == 403
    assert client.delete(f"/api/assets/{good['id']}", headers=h).status_code == 403
    assert client.patch(f"/api/assets/{good['id']}", json={"notes": "n"}, headers=h).status_code == 200


def test_delete_removes_file(client):
    p = mk_project(client)
    a = _make(client, p["id"]).json()
    assert client.delete(f"/api/assets/{a['id']}").status_code == 204
    assert client.get(f"/api/assets/{a['id']}/file").status_code == 404
    assert client.get(f"/api/projects/{p['id']}/assets").json()["summary"]["total"] == 0


def test_filters_validation_and_size(client, monkeypatch):
    p = mk_project(client)
    _make(client, p["id"], "A", "own")
    _make(client, p["id"], "B", "purchased", file=None, kind="font", license="Pro", author="Studio X")
    assert len(client.get(f"/api/projects/{p['id']}/assets", params={"kind": "font"}).json()["items"]) == 1
    assert len(client.get(f"/api/projects/{p['id']}/assets", params={"source": "own"}).json()["items"]) == 1
    assert client.post(f"/api/projects/{p['id']}/assets", data={"name": "x", "source": "bogus"}).status_code == 422
    assert client.post(f"/api/projects/{p['id']}/assets", data={"name": "", "source": "own"}).status_code == 422
    from app.routers import assets
    monkeypatch.setattr(assets, "MAX_ASSET_BYTES", 50)
    assert _make(client, p["id"], "Big").status_code == 413


def test_compliance_review_task(client):
    p = mk_project(client)
    assert client.post(f"/api/projects/{p['id']}/assets/review-task").status_code == 409
    _make(client, p["id"], "Hero", "unknown", file=None, kind="image")
    r = client.post(f"/api/projects/{p['id']}/assets/review-task")
    assert r.status_code == 201
    t = client.get(f"/api/tasks/{r.json()['task_id']}").json()
    assert t["department_key"] == "compliance" and "Hero" in t["context"] and "unknown" in t["context"]
