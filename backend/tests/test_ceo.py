from app.models import Task
from .conftest import mk_project, mk_task


def _done(client, project_id, dept="game_dev", status="Completed", text="KẾT QUẢ ABC", title="T"):
    t = mk_task(client, project_id, dept, title=title)
    with client.app.state.sf() as s:
        x = s.get(Task, t["id"])
        x.status, x.result, x.result_source = status, text if status == "Completed" else None, "claude_cli"
        if status == "Failed":
            x.error = "lỗi mẫu"
        s.commit()
    return t["id"]


def test_inbox_lists_finished_not_ceo_or_pending(client):
    p = mk_project(client)
    a = _done(client, p["id"])
    f = _done(client, p["id"], "qa", "Failed")
    _done(client, p["id"], "ceo")                     # nhiệm vụ của chính CEO không vào hộp thư
    mk_task(client, p["id"], "art")                    # chưa chạy
    r = client.get("/api/ceo/inbox").json()
    assert r["pending"] == 2 and {i["task_id"] for i in r["items"]} == {a, f}
    assert client.get("/api/dashboard").json()["ceo_pending"] == 2
    it = next(i for i in r["items"] if i["task_id"] == a)
    assert it["excerpt"] == "KẾT QUẢ ABC" and it["department_key"] == "game_dev"


def test_accept_and_dismiss_move_to_decided(client):
    p = mk_project(client)
    a, b = _done(client, p["id"]), _done(client, p["id"])
    assert client.post(f"/api/ceo/tasks/{a}/decide", json={"decision": "accepted", "note": "tốt"}).status_code == 201
    assert client.post(f"/api/ceo/tasks/{b}/decide", json={"decision": "dismissed"}).status_code == 201
    assert client.get("/api/ceo/inbox").json()["pending"] == 0
    dec = client.get("/api/ceo/inbox", params={"view": "decided"}).json()["items"]
    assert {(i["task_id"], i["decision"]) for i in dec} == {(a, "accepted"), (b, "dismissed")}
    assert client.post(f"/api/ceo/tasks/{a}/decide", json={"decision": "accepted"}).status_code == 409


def test_rework_creates_followup_with_feedback_and_upstream_result(client, fake):
    p = mk_project(client)
    a = _done(client, p["id"], text="PHIÊN BẢN 1")
    assert client.post(f"/api/ceo/tasks/{a}/decide", json={"decision": "rework"}).status_code == 422  # phải nêu cần sửa gì
    r = client.post(f"/api/ceo/tasks/{a}/decide", json={"decision": "rework", "note": "Thiếu phần xử lý lỗi mạng"}).json()
    f = client.get(f"/api/tasks/{r['followup_task_id']}").json()
    assert f["department_key"] == "game_dev" and f["status"] == "Assigned" and f["title"].startswith("Sửa lại")
    assert "Thiếu phần xử lý lỗi mạng" in f["objective"] and f["depends_on"] == [a]
    done = client.post(f"/api/tasks/{f['id']}/run", params={"wait": True}).json()
    assert done["status"] == "Completed"


def test_forward_to_other_department(client):
    p = mk_project(client)
    a = _done(client, p["id"], "game_dev")
    assert client.post(f"/api/ceo/tasks/{a}/decide", json={"decision": "forward"}).status_code == 422
    assert client.post(f"/api/ceo/tasks/{a}/decide", json={"decision": "forward", "target_department": "nope"}).status_code == 422
    r = client.post(f"/api/ceo/tasks/{a}/decide", json={"decision": "forward", "target_department": "qa", "note": "Kiểm thử bản này"}).json()
    f = client.get(f"/api/tasks/{r['followup_task_id']}").json()
    assert f["department_key"] == "qa" and f["objective"] == "Kiểm thử bản này" and f["depends_on"] == [a]
    assert f["title"].startswith("Tiếp nhận từ")


def test_failed_task_can_be_reworked(client):
    p = mk_project(client)
    a = _done(client, p["id"], status="Failed")
    r = client.post(f"/api/ceo/tasks/{a}/decide", json={"decision": "rework", "note": "Thử lại, giảm phạm vi"})
    assert r.status_code == 201


def test_only_owner_decides_manager_can_digest(client):
    p = mk_project(client)
    a = _done(client, p["id"])
    client.post("/api/users", json={"username": "mgr1", "password": "Passw0rd!x", "role": "manager"})
    tok = client.post("/api/auth/login", json={"username": "mgr1", "password": "Passw0rd!x"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert client.post(f"/api/ceo/tasks/{a}/decide", json={"decision": "accepted"}, headers=h).status_code == 403
    assert client.post("/api/ceo/digest", headers=h).status_code == 201
    assert client.get("/api/ceo/inbox", headers=h).status_code == 200


def test_digest_builds_ceo_task_with_all_results(client):
    p = mk_project(client)
    a = _done(client, p["id"], "game_dev", text="CODE-RESULT-1")
    b = _done(client, p["id"], "qa", "Failed")
    r = client.post("/api/ceo/digest").json()
    assert r["items"] == 2
    t = client.get(f"/api/tasks/{r['task_id']}").json()
    assert t["department_key"] == "ceo" and "CODE-RESULT-1" in t["context"] and "THẤT BẠI" in t["context"]
    assert f"#{a}" in t["context"] and f"#{b}" in t["context"] and "qa" in t["expected_output"]
    done = client.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()
    assert done["status"] == "Completed"
    # nhiệm vụ của CEO không tự vào hộp thư
    assert client.get("/api/ceo/inbox").json()["pending"] == 2


def test_digest_requires_items_and_respects_emergency_stop(client):
    assert client.post("/api/ceo/digest").status_code == 409
    p = mk_project(client)
    _done(client, p["id"])
    client.post("/api/system/emergency-stop", json={"active": True})
    assert client.post("/api/ceo/digest").status_code == 423


def test_archived_project_blocks_followups(client):
    p = mk_project(client)
    a = _done(client, p["id"])
    client.patch(f"/api/projects/{p['id']}", json={"status": "Archived"})
    assert client.post(f"/api/ceo/tasks/{a}/decide", json={"decision": "rework", "note": "x"}).status_code == 409
    assert client.post(f"/api/ceo/tasks/{a}/decide", json={"decision": "accepted"}).status_code == 201
