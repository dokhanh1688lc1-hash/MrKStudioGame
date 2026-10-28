from app.models import CeoReview, Task, TaskDependency, UsageRecord
from .conftest import mk_project, mk_task


def _set(client, tid, status, result=None):
    with client.app.state.sf() as s:
        t = s.get(Task, tid)
        t.status, t.result = status, result
        s.commit()


def test_progress_counts_and_percent(client):
    p = mk_project(client)
    a, b, c, d = (mk_task(client, p["id"], dept)["id"] for dept in ("game_dev", "game_dev", "qa", "qa"))
    _set(client, a, "Completed", "x")
    _set(client, b, "Running")
    _set(client, d, "Cancelled")
    r = client.get("/api/tasks/progress", params={"project_id": p["id"]}).json()
    assert r["total"] == 4 and r["done"] == 1 and r["pct"] == 33          # 1 / (4-1 cancelled)
    gd = next(x for x in r["departments"] if x["key"] == "game_dev")
    assert gd["total"] == 2 and gd["pct"] == 50 and gd["running"] == 1
    allp = client.get("/api/tasks/progress").json()
    assert allp["projects"][0]["id"] == p["id"] and allp["projects"][0]["total"] == 4


def test_progress_empty(client):
    r = client.get("/api/tasks/progress").json()
    assert r["total"] == 0 and r["pct"] == 0 and r["departments"] == []


def test_edit_task(client):
    p = mk_project(client)
    t = mk_task(client, p["id"])
    r = client.patch(f"/api/tasks/{t['id']}", json={"title": "Mới", "acceptance_criteria": "OK"})
    assert r.status_code == 200 and r.json()["title"] == "Mới" and r.json()["acceptance_criteria"] == "OK"
    assert client.patch(f"/api/tasks/{t['id']}", json={"title": ""}).status_code == 422
    _set(client, t["id"], "Running")
    assert client.patch(f"/api/tasks/{t['id']}", json={"title": "Y"}).status_code == 409
    assert client.patch("/api/tasks/9999", json={"title": "Y"}).status_code == 404


def test_delete_cleans_links_but_keeps_usage(client, fake):
    p = mk_project(client)
    up = mk_task(client, p["id"])
    down = mk_task(client, p["id"], depends_on=[up["id"]])
    done = client.post(f"/api/tasks/{up['id']}/run", params={"wait": True}).json()
    assert done["status"] == "Completed"
    with client.app.state.sf() as s:
        before = s.query(UsageRecord).count()
    assert before >= 1
    r = client.delete(f"/api/tasks/{up['id']}")
    assert r.status_code == 200
    assert client.get(f"/api/tasks/{up['id']}").status_code == 404
    assert client.get(f"/api/tasks/{down['id']}").json()["depends_on"] == []
    with client.app.state.sf() as s:
        assert s.query(UsageRecord).count() == before            # hạn mức lượt chạy không bị "reset" bằng cách xóa
        assert s.query(TaskDependency).count() == 0
    assert client.delete(f"/api/tasks/{up['id']}").status_code == 404


def test_delete_refuses_running_and_bulk_is_atomic(client):
    p = mk_project(client)
    a, b = mk_task(client, p["id"])["id"], mk_task(client, p["id"])["id"]
    _set(client, b, "Running")
    assert client.delete(f"/api/tasks/{b}").status_code == 409
    assert client.post("/api/tasks/bulk-delete", json={"ids": [a, b]}).status_code == 409
    assert client.get(f"/api/tasks/{a}").status_code == 200       # không xóa gì khi có việc đang chạy
    _set(client, b, "Failed")
    r = client.post("/api/tasks/bulk-delete", json={"ids": [a, b, a]})
    assert r.status_code == 200 and sorted(r.json()["deleted"]) == sorted([a, b])
    assert client.post("/api/tasks/bulk-delete", json={"ids": []}).status_code == 422


def test_delete_task_with_ceo_review(client):
    p = mk_project(client)
    t = mk_task(client, p["id"])
    _set(client, t["id"], "Completed", "kq")
    assert client.post(f"/api/ceo/tasks/{t['id']}/decide", json={"decision": "dismissed"}).status_code == 201
    with client.app.state.sf() as s:
        assert s.query(CeoReview).count() == 1
    assert client.delete(f"/api/tasks/{t['id']}").status_code == 200
    with client.app.state.sf() as s:
        assert s.query(CeoReview).count() == 0


def test_viewer_cannot_manage(client):
    from fastapi.testclient import TestClient
    p = mk_project(client)
    t = mk_task(client, p["id"])
    client.post("/api/users", json={"username": "viewer4", "password": "viewerpass1", "role": "viewer"})
    v = TestClient(client.app)
    v.headers["Authorization"] = "Bearer " + v.post("/api/auth/login", json={"username": "viewer4", "password": "viewerpass1"}).json()["token"]
    assert v.delete(f"/api/tasks/{t['id']}").status_code == 403
    assert v.patch(f"/api/tasks/{t['id']}", json={"title": "x"}).status_code == 403
    assert v.post("/api/tasks/bulk-delete", json={"ids": [t["id"]]}).status_code == 403
    assert v.get("/api/tasks/progress").status_code == 200
