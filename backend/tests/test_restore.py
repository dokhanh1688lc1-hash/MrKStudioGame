from .conftest import mk_project


def test_restore_brings_back_old_state_and_keeps_safety_copy(client):
    mk_project(client, name="Giữ lại")
    name = client.post("/api/system/backups").json()["name"]
    p2 = mk_project(client, name="Tạo sau backup")
    assert len(client.get("/api/projects").json()["items"]) == 2
    r = client.post(f"/api/system/backups/{name}/restore")
    assert r.status_code == 200 and r.json()["restored"] == name
    names = [x["name"] for x in client.get("/api/projects").json()["items"]]
    assert names == ["Giữ lại"] and p2["name"] not in names
    # bản an toàn của trạng thái trước khi khôi phục tồn tại và khôi phục lại được
    safety = r.json()["safety_backup"]
    assert safety in [b["name"] for b in client.get("/api/system/backups").json()]
    assert client.post(f"/api/system/backups/{safety}/restore").status_code == 200
    assert len(client.get("/api/projects").json()["items"]) == 2


def test_restore_rejections(client, tmp_path):
    assert client.post("/api/system/backups/nope.db/restore").status_code == 400
    assert client.post("/api/system/backups/mrk-0.db/restore").status_code == 404
    bad = tmp_path / "data" / "backups" / "mrk-bad.db"
    bad.write_bytes(b"not a database at all" * 50)
    assert client.post("/api/system/backups/mrk-bad.db/restore").status_code == 422
    assert client.post("/api/system/backups/..%2Fx/restore").status_code in (400, 404)


def test_restore_is_owner_only(client):
    name = client.post("/api/system/backups").json()["name"]
    client.post("/api/users", json={"username": "viewer3", "password": "viewerpass1", "role": "viewer"})
    tok = client.post("/api/auth/login", json={"username": "viewer3", "password": "viewerpass1"}).json()["token"]
    r = client.post(f"/api/system/backups/{name}/restore", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403
