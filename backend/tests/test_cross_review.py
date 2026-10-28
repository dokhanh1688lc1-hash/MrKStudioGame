from app.models import Task
from .conftest import mk_project, mk_task


def _done(client, pid, source, dept="game_dev"):
    t = mk_task(client, pid, dept, title="Viết nhảy", acceptance_criteria="Chạy được")
    with client.app.state.sf() as s:
        x = s.get(Task, t["id"])
        x.status, x.result, x.result_source = "Completed", "KẾT QUẢ GỐC", source
        s.commit()
    return t["id"]


def test_cross_review_uses_the_other_provider_and_gets_result(client, fake):
    p = mk_project(client)
    tid = _done(client, p["id"], "claude_cli")
    r = client.post(f"/api/tasks/{tid}/cross-review")
    assert r.status_code == 201 and r.json()["reviewer"] == "codex_cli"
    rv = client.get(f"/api/tasks/{r.json()['task_id']}").json()
    assert rv["provider"] == "codex_cli" and rv["title"].startswith("Đánh giá chéo") and rv["depends_on"] == [tid]
    assert "Chạy được" in rv["objective"]
    done = client.post(f"/api/tasks/{rv['id']}/run", params={"wait": True}).json()
    assert done["status"] == "Completed" and done["result_source"] == "codex_cli"
    assert fake.calls["codex_cli"] == 1 and fake.calls["claude_cli"] == 0


def test_reverse_direction(client):
    p = mk_project(client)
    tid = _done(client, p["id"], "codex_cli")
    assert client.post(f"/api/tasks/{tid}/cross-review").json()["reviewer"] == "claude_cli"


def test_rejections(client, offline):
    p = mk_project(client)
    pending = mk_task(client, p["id"], "game_dev")
    assert client.post(f"/api/tasks/{pending['id']}/cross-review").status_code == 409
    assert client.post(f"/api/tasks/{_done(client, p['id'], 'internal')}/cross-review").status_code == 409
    assert client.post("/api/tasks/9999/cross-review").status_code == 404
    # provider kia đang tắt
    client.patch("/api/providers/codex_cli", json={"enabled": False})
    r = client.post(f"/api/tasks/{_done(client, p['id'], 'claude_cli')}/cross-review")
    assert r.status_code == 409 and "codex_cli" in r.json()["detail"]
