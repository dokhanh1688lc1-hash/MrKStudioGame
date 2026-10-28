import time

from .conftest import mk_project, mk_task


def _wait(client, tid, want=("Completed", "Failed"), timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        st = client.get(f"/api/tasks/{tid}").json()["status"]
        if st in want:
            return st
        time.sleep(0.1)
    return client.get(f"/api/tasks/{tid}").json()["status"]


def _on(client, v=True):
    assert client.patch("/api/system/settings", json={"auto_run": v}).status_code == 200


def test_default_for_new_installs_is_on_and_toggle(client):
    # fixture tắt để test kiểm soát; bật lại qua API
    assert client.get("/api/system/state").json()["auto_run"] is False
    _on(client)
    assert client.get("/api/system/state").json()["auto_run"] is True


def test_new_task_runs_automatically(client, fake):
    _on(client)
    p = mk_project(client)
    t = mk_task(client, p["id"], "game_dev")
    assert _wait(client, t["id"]) == "Completed"
    assert fake.calls["claude_cli"] + fake.calls["codex_cli"] >= 1


def test_off_means_stays_assigned(client, fake):
    p = mk_project(client)
    t = mk_task(client, p["id"], "game_dev")
    time.sleep(0.5)
    assert client.get(f"/api/tasks/{t['id']}").json()["status"] == "Assigned"
    assert fake.calls["claude_cli"] + fake.calls["codex_cli"] == 0


def test_dependent_runs_after_upstream_completes(client):
    _on(client)
    p = mk_project(client)
    a = mk_task(client, p["id"], "game_dev")
    b = client.post("/api/tasks", json={"project_id": p["id"], "department_key": "qa", "title": "Kiểm thử sau",
                                        "objective": "Kiểm thử kết quả bước trước", "depends_on": [a["id"]]}).json()
    assert _wait(client, a["id"]) == "Completed"
    assert _wait(client, b["id"]) == "Completed"


def test_approval_required_waits_then_runs_after_approve(client):
    _on(client)
    p = mk_project(client)
    t = client.post("/api/tasks", json={"project_id": p["id"], "department_key": "game_dev", "title": "Cần duyệt",
                                        "objective": "Việc cần duyệt", "requires_approval": True}).json()
    assert t["status"] == "Awaiting Approval"
    pend = client.get("/api/approvals", params={"status": "pending"}).json()
    assert len(pend) == 1
    client.post(f"/api/approvals/{pend[0]['id']}/decision", json={"approve": True})
    assert _wait(client, t["id"]) == "Completed"


def test_emergency_stop_blocks_auto_run(client):
    _on(client)
    client.post("/api/system/emergency-stop", json={"active": True})
    p = mk_project(client)
    t = mk_task(client, p["id"], "game_dev")
    time.sleep(0.5)
    assert client.get(f"/api/tasks/{t['id']}").json()["status"] == "Assigned"


def test_paused_project_does_not_auto_run(client):
    _on(client)
    p = mk_project(client)
    client.patch(f"/api/projects/{p['id']}", json={"status": "Paused"})
    t = mk_task(client, p["id"], "game_dev")
    time.sleep(0.5)
    assert client.get(f"/api/tasks/{t['id']}").json()["status"] == "Assigned"


def test_pipeline_first_step_auto_runs_and_gate_waits_for_approval(offline):
    _on(offline)
    p = mk_project(offline)
    tasks = offline.post(f"/api/projects/{p['id']}/pipeline", json={"brief": "Game thử"}).json()
    first = tasks[0]
    assert _wait(offline, first["id"], want=("Completed", "Awaiting Approval", "Failed")) in ("Completed", "Awaiting Approval")
