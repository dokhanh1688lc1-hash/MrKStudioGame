import os
from pathlib import Path

import pytest

from app.services import changes as ch
from app.services import sources as src
from .conftest import mk_project, mk_task


@pytest.fixture()
def game(tmp_path):
    root = tmp_path / "games"
    g = root / "puzzle"
    (g / "scripts").mkdir(parents=True)
    (g / "scripts" / "player.gd").write_text("extends Node\nvar speed = 100\nfunc run():\n    pass\n", encoding="utf-8")
    (g / "scripts" / "win.gd").write_bytes(b"line1\r\nline2\r\n")
    (g / ".env").write_text("KEY=1")
    (g / "run.bat").write_text("echo hi")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "x.gd").write_text("secret")
    return {"root": root, "g": g, "outside": outside}


@pytest.fixture()
def proj(client, game):
    assert client.put("/api/system/import-roots", json={"paths": [str(game["root"])]}).status_code == 200
    p = mk_project(client)
    r = client.post(f"/api/projects/{p['id']}/import/folder", json={"path": str(game["g"])})
    assert r.status_code == 201, r.text
    return p


def _manual(client, pid, path, content):
    return client.post(f"/api/projects/{pid}/changes", json={"path": path, "content": content})


def test_write_access_off_by_default_and_owner_only(client, proj, game):
    c = _manual(client, proj["id"], "scripts/player.gd", "extends Node\nvar speed = 200\n").json()
    r = client.post(f"/api/changes/{c['id']}/apply")
    assert r.status_code == 403 and "quyền ghi" in r.json()["detail"]
    assert (game["g"] / "scripts" / "player.gd").read_text().count("100") == 1  # chưa đổi gì
    client.post("/api/users", json={"username": "mgr1", "password": "Passw0rd!x", "role": "manager"})
    tok = client.post("/api/auth/login", json={"username": "mgr1", "password": "Passw0rd!x"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert client.put(f"/api/projects/{proj['id']}/write-access", json={"enabled": True}, headers=h).status_code == 403
    assert client.post(f"/api/changes/{c['id']}/apply", headers=h).status_code == 403
    assert client.put(f"/api/projects/{proj['id']}/write-access", json={"enabled": True}).json()["allow_write"] is True


def test_write_access_needs_folder_source(client):
    p = mk_project(client)
    assert client.put(f"/api/projects/{p['id']}/write-access", json={"enabled": True}).status_code == 409


def test_apply_backup_and_revert(client, proj, game):
    client.put(f"/api/projects/{proj['id']}/write-access", json={"enabled": True})
    c = _manual(client, proj["id"], "scripts/player.gd", "extends Node\nvar speed = 200\nfunc run():\n    pass\n").json()
    assert c["status"] == "pending" and "-var speed = 100" in c["diff"] and "+var speed = 200" in c["diff"]
    a = client.post(f"/api/changes/{c['id']}/apply")
    assert a.status_code == 200 and a.json()["status"] == "applied"
    f = game["g"] / "scripts" / "player.gd"
    assert "speed = 200" in f.read_text()
    backups = list((client.app.state.settings.data_dir / "file-backups").rglob("player.gd"))
    assert len(backups) == 1 and "speed = 100" in backups[0].read_text()
    assert client.post(f"/api/changes/{c['id']}/apply").status_code == 409  # không áp dụng hai lần
    r = client.post(f"/api/changes/{c['id']}/revert")
    assert r.status_code == 200 and "speed = 100" in f.read_text()
    assert client.post(f"/api/changes/{c['id']}/revert").status_code == 409


def test_conflict_when_file_changed_after_proposal(client, proj, game):
    client.put(f"/api/projects/{proj['id']}/write-access", json={"enabled": True})
    c = _manual(client, proj["id"], "scripts/player.gd", "extends Node\nvar speed = 5\n").json()
    f = game["g"] / "scripts" / "player.gd"
    f.write_text("tôi vừa sửa tay\n", encoding="utf-8")
    r = client.post(f"/api/changes/{c['id']}/apply")
    assert r.status_code == 409 and "thay đổi" in r.json()["detail"]
    assert f.read_text(encoding="utf-8") == "tôi vừa sửa tay\n"
    listed = client.get(f"/api/projects/{proj['id']}/changes").json()["items"][0]
    assert listed["stale"] is True


def test_revert_refuses_if_edited_afterwards(client, proj, game):
    client.put(f"/api/projects/{proj['id']}/write-access", json={"enabled": True})
    c = _manual(client, proj["id"], "scripts/player.gd", "extends Node\nvar speed = 7\n").json()
    client.post(f"/api/changes/{c['id']}/apply")
    f = game["g"] / "scripts" / "player.gd"
    f.write_text(f.read_text() + "# thêm\n")
    assert client.post(f"/api/changes/{c['id']}/revert").status_code == 409


def test_new_file_create_and_revert_deletes_it(client, proj, game):
    client.put(f"/api/projects/{proj['id']}/write-access", json={"enabled": True})
    c = _manual(client, proj["id"], "scripts/new/enemy.gd", "extends Node\n").json()
    assert c["is_new"] is True
    assert client.post(f"/api/changes/{c['id']}/apply").status_code == 200
    f = game["g"] / "scripts" / "new" / "enemy.gd"
    assert f.read_text() == "extends Node\n"
    assert client.post(f"/api/changes/{c['id']}/revert").status_code == 200 and not f.exists()


def test_crlf_preserved(client, proj, game):
    client.put(f"/api/projects/{proj['id']}/write-access", json={"enabled": True})
    c = _manual(client, proj["id"], "scripts/win.gd", "line1\nline2 changed\n").json()
    client.post(f"/api/changes/{c['id']}/apply")
    assert (game["g"] / "scripts" / "win.gd").read_bytes() == b"line1\r\nline2 changed\r\n"


@pytest.mark.parametrize("path", ["../outside/x.gd", "scripts/../../outside/x.gd", "/etc/passwd", "C:/Windows/x.gd",
                                  ".env", "run.bat", "scripts/evil.ps1", "scripts/evil.exe", ".git/config", "node_modules/a.js",
                                  "keys/server.pem", "", "a//b.gd"])
def test_dangerous_paths_rejected(client, proj, game, path):
    r = _manual(client, proj["id"], path or " ", "x")
    assert r.status_code in (422, 404), (path, r.status_code, r.text)
    assert (game["outside"] / "x.gd").read_text() == "secret"


def test_symlink_escape_blocked(client, proj, game):
    link = game["g"] / "escape"
    try:
        os.symlink(game["outside"], link)
    except (OSError, NotImplementedError):
        pytest.skip("không tạo được symlink")
    r = _manual(client, proj["id"], "escape/x.gd", "pwned")
    assert r.status_code == 422 and (game["outside"] / "x.gd").read_text() == "secret"


def test_apply_blocked_when_root_removed_from_allowlist(client, proj, game, tmp_path):
    client.put(f"/api/projects/{proj['id']}/write-access", json={"enabled": True})
    c = _manual(client, proj["id"], "scripts/player.gd", "extends Node\n").json()
    other = tmp_path / "other"
    other.mkdir()
    client.put("/api/system/import-roots", json={"paths": [str(other)]})
    assert client.post(f"/api/changes/{c['id']}/apply").status_code == 403
    assert (game["g"] / "scripts" / "player.gd").read_text().startswith("extends Node\nvar speed")


def test_emergency_stop_blocks_apply(client, proj):
    client.put(f"/api/projects/{proj['id']}/write-access", json={"enabled": True})
    c = _manual(client, proj["id"], "scripts/player.gd", "extends Node\n").json()
    client.post("/api/system/emergency-stop", json={"active": True})
    assert client.post(f"/api/changes/{c['id']}/apply").status_code == 423


def test_reject_and_unchanged_manual(client, proj):
    c = _manual(client, proj["id"], "scripts/player.gd", "extends Node\nvar speed = 1\n").json()
    assert client.post(f"/api/changes/{c['id']}/reject").json()["status"] == "rejected"
    assert client.post(f"/api/changes/{c['id']}/apply").status_code in (403, 409)
    same = (Path(proj["workspace_path"]).parent / "x")  # chỉ để dùng biến, bỏ qua
    cur = client.get(f"/api/projects/{proj['id']}/source-file", params={"path": "scripts/player.gd"}).json()["content"]
    assert _manual(client, proj["id"], "scripts/player.gd", cur).status_code == 422


# ---------- trích đề xuất từ kết quả AI ----------
AI_TEXT = """Giải thích...
<<<FILE imports/1-20260101-000000/scripts/player.gd>>>
<<<SEARCH>>>
var speed = 100
<<<REPLACE>>>
var speed = 250
<<<END>>>
<<<SEARCH>>>
func run():
    pass
<<<REPLACE>>>
func run():
    print("go")
<<<END>>>
<<<END FILE>>>
<<<NEW FILE scripts/health.gd>>>
extends Node
var hp = 3
<<<END FILE>>>
<<<FILE scripts/missing.gd>>>
<<<SEARCH>>>
a
<<<REPLACE>>>
b
<<<END>>>
<<<END FILE>>>
<<<FILE scripts/win.gd>>>
<<<SEARCH>>>
KHÔNG-CÓ-TRONG-TỆP
<<<REPLACE>>>
x
<<<END>>>
<<<END FILE>>>
<<<FILE .env>>>
<<<SEARCH>>>
KEY=1
<<<REPLACE>>>
KEY=2
<<<END>>>
<<<END FILE>>>
"""


def _done_task(client, proj, text, source="claude_cli"):
    t = mk_task(client, proj["id"], "game_dev")
    from app.models import Task
    with client.app.state.sf() as s:
        x = s.get(Task, t["id"])
        x.status, x.result, x.result_source = "Completed", text, source
        s.commit()
    return t["id"]


def test_parse_ai_output(game):
    root = game["g"]
    props, errs = ch.parse_ai_output(AI_TEXT, root)
    byp = {p.rel: p for p in props}
    assert set(byp) == {"scripts/player.gd", "scripts/health.gd"}
    assert "speed = 250" in byp["scripts/player.gd"].new_content and 'print("go")' in byp["scripts/player.gd"].new_content
    assert byp["scripts/health.gd"].base_sha == "" and byp["scripts/player.gd"].base_sha
    assert len(errs) == 3 and any("không tìm thấy" in e for e in errs) and any("không khớp" in e for e in errs) \
        and any("bí mật" in e for e in errs)


def test_search_must_be_unique(game):
    (game["g"] / "dup.gd").write_text("a\na\n")
    props, errs = ch.parse_ai_output("<<<FILE dup.gd>>>\n<<<SEARCH>>>\na\n<<<REPLACE>>>\nb\n<<<END>>>\n<<<END FILE>>>", game["g"])
    assert not props and "không duy nhất" in errs[0]


def test_extract_from_task_then_apply(client, proj, game):
    tid = _done_task(client, proj, AI_TEXT)
    r = client.post(f"/api/tasks/{tid}/extract-changes")
    assert r.status_code == 201 and len(r.json()["created"]) == 2 and len(r.json()["errors"]) == 3
    client.put(f"/api/projects/{proj['id']}/write-access", json={"enabled": True})
    items = client.get(f"/api/projects/{proj['id']}/changes", params={"status": "pending"}).json()["items"]
    assert {i["path"] for i in items} == {"scripts/player.gd", "scripts/health.gd"} and all(not i["stale"] for i in items)
    for i in items:
        assert client.post(f"/api/changes/{i['id']}/apply").status_code == 200
    assert "speed = 250" in (game["g"] / "scripts" / "player.gd").read_text()
    assert (game["g"] / "scripts" / "health.gd").exists()
    assert (game["g"] / ".env").read_text() == "KEY=1"


def test_extract_rejects_internal_incomplete_or_no_blocks(client, proj):
    assert client.post(f"/api/tasks/{_done_task(client, proj, AI_TEXT, 'internal')}/extract-changes").status_code == 409
    assert client.post(f"/api/tasks/{_done_task(client, proj, 'Không có khối nào')}/extract-changes").status_code == 422
    t = mk_task(client, proj["id"], "game_dev")
    assert client.post(f"/api/tasks/{t['id']}/extract-changes").status_code == 409


def test_upgrade_task_includes_format_only_for_folder_projects(client, proj):
    r = client.post(f"/api/projects/{proj['id']}/upgrade-task", json={"goal": "Sửa lỗi tốc độ"})
    assert r.status_code == 201
    t = client.get(f"/api/tasks/{r.json()['task_id']}").json()
    assert "<<<SEARCH>>>" in t["expected_output"]
    p2 = mk_project(client, "Other")
    client.post(f"/api/projects/{p2['id']}/files", files=[("files", ("a.gd", b"x", "text/plain"))])
    t2 = client.get(f"/api/tasks/{client.post(f'/api/projects/{p2['id']}/upgrade-task', json={'goal': 'abc'}).json()['task_id']}").json()
    assert "<<<SEARCH>>>" not in t2["expected_output"]
