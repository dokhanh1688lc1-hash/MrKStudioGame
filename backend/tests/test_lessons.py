from fastapi.testclient import TestClient

from app.models import Lesson
from app.services.orchestrator import build_prompt
from .conftest import mk_project, mk_task


def _prompt_of(client, tid):
    from app.models import Task
    from app.services import lessons as svc
    with client.app.state.sf() as s:
        t = s.get(Task, tid)
        return build_prompt(t, None, svc.texts_and_mark_used(s, t.department_key, t.project_id))


def test_manual_lesson_is_injected_for_that_department_only(client):
    p = mk_project(client)
    r = client.post("/api/lessons", json={"department_key": "qa", "text": "Luôn nêu bước tái hiện lỗi."})
    assert r.status_code == 201 and r.json()["status"] == "active"
    qa, dev = mk_task(client, p["id"], "qa"), mk_task(client, p["id"], "game_dev")
    assert "Luôn nêu bước tái hiện lỗi." in _prompt_of(client, qa["id"])
    assert "Bài học của phòng ban" not in _prompt_of(client, dev["id"])
    assert client.get("/api/lessons", params={"department": "qa"}).json()["items"][0]["uses"] == 1


def test_project_scope_and_status_rules(client):
    a, b = mk_project(client, "A"), mk_project(client, "B")
    client.post("/api/lessons", json={"department_key": "qa", "text": "Chỉ cho dự án A thôi.", "project_id": a["id"]})
    client.post("/api/lessons", json={"department_key": "qa", "text": "Bài học đã lưu trữ ở đây."})
    arch = client.get("/api/lessons").json()["items"][0]
    client.patch(f"/api/lessons/{arch['id']}", json={"status": "archived"})
    ta, tb = mk_task(client, a["id"], "qa"), mk_task(client, b["id"], "qa")
    assert "Chỉ cho dự án A thôi." in _prompt_of(client, ta["id"])
    pb = _prompt_of(client, tb["id"])
    assert "Chỉ cho dự án A" not in pb and "đã lưu trữ" not in pb


def test_ceo_note_creates_suggestion_not_injected_until_approved(client):
    p = mk_project(client)
    t = mk_task(client, p["id"], "qa")
    from app.models import Task
    with client.app.state.sf() as s:
        x = s.get(Task, t["id"]); x.status, x.result = "Completed", "kq"; s.commit()
    r = client.post(f"/api/ceo/tasks/{t['id']}/decide", json={"decision": "rework", "note": "Thiếu kịch bản kiểm thử âm."})
    assert r.status_code == 201 and r.json()["lesson_suggested"] is True
    l = client.get("/api/lessons", params={"status": "suggested"}).json()["items"][0]
    assert l["source"] == "ceo" and l["project_id"] == p["id"] and l["department_key"] == "qa"
    nxt = mk_task(client, p["id"], "qa")
    assert "kịch bản kiểm thử âm" not in _prompt_of(client, nxt["id"])
    assert client.patch(f"/api/lessons/{l['id']}", json={"status": "active", "project_id": None}).json()["project_id"] is None
    assert "Thiếu kịch bản kiểm thử âm." in _prompt_of(client, nxt["id"])


def test_no_suggestion_without_note_or_duplicate(client):
    p = mk_project(client)
    ids = []
    for _ in range(2):
        t = mk_task(client, p["id"], "qa")
        from app.models import Task
        with client.app.state.sf() as s:
            x = s.get(Task, t["id"]); x.status, x.result = "Completed", "kq"; s.commit()
        ids.append(t["id"])
    assert client.post(f"/api/ceo/tasks/{ids[0]}/decide", json={"decision": "accepted"}).json()["lesson_suggested"] is False
    assert client.post(f"/api/ceo/tasks/{ids[1]}/decide", json={"decision": "accepted", "note": "Báo cáo rõ ràng, giữ."}).json()["lesson_suggested"] is True
    t3 = mk_task(client, p["id"], "qa")
    from app.models import Task
    with client.app.state.sf() as s:
        x = s.get(Task, t3["id"]); x.status, x.result = "Completed", "kq"; s.commit()
    assert client.post(f"/api/ceo/tasks/{t3['id']}/decide", json={"decision": "accepted", "note": "Báo cáo rõ ràng, giữ."}).json()["lesson_suggested"] is False


def test_limits_secrets_and_caps(client):
    p = mk_project(client)
    client.post("/api/lessons", json={"department_key": "qa", "text": "Khóa sk-ant-api03-ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 đừng lộ."})
    assert "ABCDEFGH" not in client.get("/api/lessons").json()["items"][0]["text"]
    for i in range(12):
        client.post("/api/lessons", json={"department_key": "art", "text": f"Quy tắc số {i} " + "x" * 300})
    t = mk_task(client, p["id"], "art")
    pr = _prompt_of(client, t["id"])
    assert pr.count("\n- ") <= 8 and len(pr.split("## Bài học")[1].split("##")[0]) < 1700
    assert client.post("/api/lessons", json={"department_key": "nope", "text": "xxxxxxxx"}).status_code == 422
    assert client.post("/api/lessons", json={"department_key": "qa", "text": "ab"}).status_code == 422
    for i in range(29):
        assert client.post("/api/lessons", json={"department_key": "audio", "text": f"Bài {i:02d} dài đủ"}).status_code == 201
    assert client.post("/api/lessons", json={"department_key": "audio", "text": "Bài thừa ra ngoài"}).status_code == 201
    assert client.post("/api/lessons", json={"department_key": "audio", "text": "Bài vượt giới hạn 31"}).status_code == 409


def test_delete_task_keeps_lesson_and_permissions(client):
    p = mk_project(client)
    t = mk_task(client, p["id"], "qa")
    with client.app.state.sf() as s:
        s.add(Lesson(department_key="qa", text="Bài từ một task", status="active", source="ceo", task_id=t["id"])); s.commit()
    assert client.delete(f"/api/tasks/{t['id']}").status_code == 200
    items = client.get("/api/lessons").json()["items"]
    assert len(items) == 1 and items[0]["task_id"] is None
    client.post("/api/users", json={"username": "viewer6", "password": "viewerpass1", "role": "viewer"})
    v = TestClient(client.app)
    v.headers["Authorization"] = "Bearer " + v.post("/api/auth/login", json={"username": "viewer6", "password": "viewerpass1"}).json()["token"]
    assert v.get("/api/lessons").status_code == 200
    assert v.post("/api/lessons", json={"department_key": "qa", "text": "viewer không được"}).status_code == 403
    assert v.delete(f"/api/lessons/{items[0]['id']}").status_code == 403
    assert client.delete(f"/api/lessons/{items[0]['id']}").status_code == 204
    assert client.delete(f"/api/lessons/{items[0]['id']}").status_code == 404
