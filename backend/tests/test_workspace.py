import io
import stat
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from .conftest import mk_project


def make_zip(entries: dict[str, str | bytes], symlink: dict[str, str] | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in entries.items():
            z.writestr(name, data)
        for name, target in (symlink or {}).items():
            zi = zipfile.ZipInfo(name)
            zi.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(zi, target)
    return buf.getvalue()


def up(c, pid, name, data):
    return c.post(f"/api/projects/{pid}/files", files=[("files", (name, data, "application/octet-stream"))])


GAME = {"MyGame/project.godot": "config_version=5\n", "MyGame/player.gd": "extends Node\nvar speed = 5\n",
        "MyGame/README.md": "# My game\n", "MyGame/.env": "OPENAI_API_KEY=sk-realsecretvalue1234567890",
        "MyGame/.git/config": "x", "MyGame/node_modules/a.js": "x"}


def test_import_zip_skips_secrets_git_and_versions_imports(client):
    p = mk_project(client)
    r = up(client, p["id"], "game.zip", make_zip(GAME, {"MyGame/link": "/etc/passwd"}))
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["files_saved"] == 3 and j["import"].startswith("1-")
    assert any(".env" in s for s in j["skipped"]) and any("symlink" in s for s in j["skipped"])
    r2 = up(client, p["id"], "game2.zip", make_zip({"a/x.gd": "extends Node"})).json()
    assert r2["import"].startswith("2-")  # không ghi đè bản trước
    tree = client.get(f"/api/projects/{p['id']}/files").json()
    paths = [f["path"] for f in tree["files"]]
    assert any(x.endswith("MyGame/player.gd") for x in paths)
    assert not any(".env" in x or ".git" in x or "node_modules" in x or x.endswith("link") for x in paths)
    assert len(tree["imports"]) == 2
    assert not list(Path(p["workspace_path"]).rglob(".env"))


def test_zip_slip_rejected_and_nothing_written(client, tmp_path):
    p = mk_project(client)
    for bad in ("../evil.txt", "/abs/evil.txt", "a/../../evil.txt", "C:/evil.txt"):
        r = up(client, p["id"], "bad.zip", make_zip({bad: "x"}))
        assert r.status_code == 400, bad
    assert not (Path(p["workspace_path"]).parent / "evil.txt").exists()
    assert not (Path(p["workspace_path"]) / "imports").exists() or not list((Path(p["workspace_path"]) / "imports").iterdir())


def test_bad_zip_and_empty_and_only_secrets(client):
    p = mk_project(client)
    assert up(client, p["id"], "x.zip", b"not a zip").status_code == 400
    assert up(client, p["id"], "e.zip", make_zip({"a/.env": "K=1"})).status_code == 400
    assert client.post(f"/api/projects/{p['id']}/files", files=[]).status_code == 422


def test_plain_file_upload_and_secret_name_blocked(client):
    p = mk_project(client)
    assert up(client, p["id"], "main.gd", b"extends Node").json()["files_saved"] == 1
    assert up(client, p["id"], "server.pem", b"x").status_code == 400
    assert up(client, p["id"], "../../sneaky.gd", b"x").status_code == 200  # tên bị rút gọn thành sneaky.gd
    assert not (Path(p["workspace_path"]).parent.parent / "sneaky.gd").exists()


def test_read_file_traversal_binary_and_redaction(client):
    p = mk_project(client)
    up(client, p["id"], "g.zip", make_zip({"p/a.gd": 'var api_key = "sk-abcdefghijklmnopqrstuvwxyz123"\nextends Node',
                                           "p/img.png": b"\x89PNG"}))
    base = f"/api/projects/{p['id']}/files/content"
    imp = client.get(f"/api/projects/{p['id']}/files").json()["imports"][0]
    ok = client.get(base, params={"path": f"imports/{imp}/p/a.gd"}).json()
    assert "sk-abcdefghijklmnop" not in ok["content"] and "extends Node" in ok["content"]
    assert client.get(base, params={"path": "../../../etc/passwd"}).status_code == 400
    assert client.get(base, params={"path": f"imports/{imp}/p/img.png"}).status_code == 415
    assert client.get(base, params={"path": "nope.gd"}).status_code == 404


def test_upgrade_task_needs_code_then_runs_with_redacted_context(offline):
    p = mk_project(offline)
    r = offline.post(f"/api/projects/{p['id']}/upgrade-task", json={"goal": "Sửa lỗi nhảy"})
    assert r.status_code == 409
    up(offline, p["id"], "g.zip", make_zip({"p/player.gd": "extends Node\nvar secret_token = 'abc123'\n", "p/README.md": "# Hi"}))
    r = offline.post(f"/api/projects/{p['id']}/upgrade-task", json={"goal": "Sửa lỗi nhảy và thêm double jump"})
    assert r.status_code == 201
    tid = r.json()["task_id"]
    t = offline.get(f"/api/tasks/{tid}").json()
    assert t["department_key"] == "game_dev" and "player.gd" in t["context"] and "abc123" not in t["context"]
    done = offline.post(f"/api/tasks/{tid}/run", params={"wait": True}).json()
    assert done["status"] == "Completed"
    saved = offline.post(f"/api/tasks/{tid}/save-to-workspace").json()
    assert (Path(p["workspace_path"]) / saved["path"]).is_file()


def test_save_requires_completed(offline):
    p = mk_project(offline)
    t = offline.post("/api/tasks", json={"project_id": p["id"], "department_key": "qa", "title": "t", "objective": "o"}).json()
    assert offline.post(f"/api/tasks/{t['id']}/save-to-workspace").status_code == 409


def test_viewer_cannot_upload_but_can_list(client):
    p = mk_project(client)
    client.post("/api/users", json={"username": "viewer3", "password": "viewerpass1", "role": "viewer"})
    v = TestClient(client.app)
    v.headers["Authorization"] = "Bearer " + v.post("/api/auth/login", json={"username": "viewer3", "password": "viewerpass1"}).json()["token"]
    assert up(v, p["id"], "a.gd", b"x").status_code == 403
    assert v.get(f"/api/projects/{p['id']}/files").status_code == 200


def test_project_edit_rename_conflict_and_archived_blocks_upload(client):
    a, b = mk_project(client, "A"), mk_project(client, "B")
    assert client.patch(f"/api/projects/{b['id']}", json={"name": "A"}).status_code == 409
    r = client.patch(f"/api/projects/{b['id']}", json={"name": "B2", "genre": "rpg", "description": "mô tả mới"})
    assert r.json()["name"] == "B2" and r.json()["genre"] == "rpg"
    client.patch(f"/api/projects/{b['id']}", json={"status": "Archived"})
    assert up(client, b["id"], "a.gd", b"x").status_code == 409


def test_vietnamese_names_slugified_in_workspace(client):
    p = client.post("/api/projects", json={"name": "Đảo Kỳ Lạ"}).json()
    assert p["workspace_path"].endswith("dao-ky-la")
