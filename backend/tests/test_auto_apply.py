from .conftest import mk_task
from .test_changes import AI_TEXT, _done_task, game, proj  # noqa: F401  (fixtures dùng lại)


def _enable(client, proj, auto=True):
    assert client.put(f"/api/projects/{proj['id']}/write-access", json={"enabled": True}).status_code == 200
    if auto:
        assert client.put(f"/api/projects/{proj['id']}/auto-apply", json={"enabled": True}).status_code == 200


def test_auto_apply_needs_write_access_and_owner(client, proj):
    assert client.put(f"/api/projects/{proj['id']}/auto-apply", json={"enabled": True}).status_code == 409
    _enable(client, proj)
    assert client.get(f"/api/projects/{proj['id']}/changes").json()["auto_apply"] is True
    # tắt quyền ghi → tự áp dụng tắt theo
    client.put(f"/api/projects/{proj['id']}/write-access", json={"enabled": False})
    assert client.get(f"/api/projects/{proj['id']}/changes").json()["auto_apply"] is False


def test_task_completion_overwrites_files_with_backup_and_revert(client, proj, game):
    _enable(client, proj)
    tid = _done_task(client, proj, AI_TEXT)
    client.app.state.orch.auto_apply_changes(tid)
    assert "speed = 250" in (game["g"] / "scripts" / "player.gd").read_text()
    assert (game["g"] / "scripts" / "health.gd").exists()
    assert (game["g"] / ".env").read_text() == "KEY=1"
    items = client.get(f"/api/projects/{proj['id']}/changes", params={"status": "applied"}).json()["items"]
    assert len(items) == 2 and all(i["decided_by"] == "auto" for i in items)
    one = next(i for i in items if i["path"] == "scripts/player.gd")
    assert client.post(f"/api/changes/{one['id']}/revert").status_code == 200
    assert "speed = 100" in (game["g"] / "scripts" / "player.gd").read_text()


def test_off_by_default_nothing_written(client, proj, game):
    client.put(f"/api/projects/{proj['id']}/write-access", json={"enabled": True})
    tid = _done_task(client, proj, AI_TEXT)
    client.app.state.orch.auto_apply_changes(tid)
    assert "speed = 100" in (game["g"] / "scripts" / "player.gd").read_text()


def test_internal_results_and_emergency_stop_do_not_write(client, proj, game):
    _enable(client, proj)
    client.app.state.orch.auto_apply_changes(_done_task(client, proj, AI_TEXT, "internal"))
    assert "speed = 100" in (game["g"] / "scripts" / "player.gd").read_text()
    client.post("/api/system/emergency-stop", json={"active": True})
    client.app.state.orch.auto_apply_changes(_done_task(client, proj, AI_TEXT))
    assert "speed = 100" in (game["g"] / "scripts" / "player.gd").read_text()
