from app.models import Task
from app.services.guidance import explain_error
from .conftest import mk_project, mk_task


def _set(client, tid, **kw):
    with client.app.state.sf() as s:
        t = s.get(Task, tid)
        for k, v in kw.items():
            setattr(t, k, v)
        s.commit()


def keys(client):
    r = client.get("/api/ceo/attention").json()
    return {i["key"]: i for i in r["items"]}, r


def test_guidance_maps_common_errors_to_steps():
    cases = {"claude: chưa đăng nhập. Mở cửa sổ lệnh": "login", "codex: chưa đăng nhập": "login",
             "Hết thời gian chờ (timeout).": "timeout", "claude thoát với mã 1: usage limit reached": "quota",
             "Không tìm thấy chương trình 'claude'.": "missing_cli", "Emergency Stop đang bật.": "emergency",
             "Đã chạm giới hạn lượt chạy": "budget", "lỗi lạ": "generic"}
    for text, code in cases.items():
        g = explain_error(text)
        assert g["code"] == code and g["steps"] and g["title"], text
    assert "codex" in " ".join(explain_error("codex: chưa đăng nhập")["steps"]).lower()
    assert explain_error("") is None and explain_error(None) is None


def test_failed_task_detail_has_help(client):
    p = mk_project(client)
    t = mk_task(client, p["id"])
    _set(client, t["id"], status="Failed", error="claude: chưa đăng nhập. Mở cửa sổ lệnh")
    d = client.get(f"/api/tasks/{t['id']}").json()
    assert d["help"]["code"] == "login" and d["help"]["page"] == "providers"
    ok = mk_task(client, p["id"])
    assert client.get(f"/api/tasks/{ok['id']}").json()["help"] is None


def test_attention_quiet_when_nothing_to_do(offline):
    k, r = keys(offline)
    assert r["counts"]["urgent"] == 0
    assert "failed" not in k and "ceo_inbox" not in k and "approvals" not in k
    assert "no_ai" in k and k["no_ai"]["severity"] == "warn"      # chưa bật AI thật nào


def test_attention_collects_and_orders_by_severity(client):
    p = mk_project(client)
    a, b = mk_task(client, p["id"])["id"], mk_task(client, p["id"], "qa")["id"]
    _set(client, a, status="Failed", error="Hết thời gian chờ (timeout).")
    _set(client, b, status="Completed", result="xong")
    client.post("/api/lessons", json={"department_key": "qa", "text": "bài học thường"})
    k, r = keys(client)
    assert k["failed"]["severity"] == "urgent" and k["failed"]["count"] == 1
    assert k["failed"]["samples"][0]["id"] == a and "quá lâu" in k["failed"]["samples"][0]["detail"]
    assert k["failed"]["steps"] and k["failed"]["page"] == "ceo"
    assert k["ceo_inbox"]["severity"] == "warn" and k["ceo_inbox"]["samples"][0]["id"] == b
    sev = [i["severity"] for i in r["items"]]
    assert sev == sorted(sev, key=["urgent", "warn", "info"].index)
    assert client.post("/api/system/emergency-stop", json={"active": True}).status_code == 200
    assert keys(client)[0]["emergency"]["severity"] == "urgent"
    client.post("/api/system/emergency-stop", json={"active": False})
    assert "emergency" not in keys(client)[0]
    # CEO quyết định → hết nhắc
    client.post(f"/api/ceo/tasks/{b}/decide", json={"decision": "dismissed"})
    client.post(f"/api/ceo/tasks/{a}/decide", json={"decision": "dismissed"})
    k, _ = keys(client)
    assert "failed" not in k and "ceo_inbox" not in k


def test_attention_budget_provider_and_stale(client):
    from datetime import timedelta
    from app.db import utcnow
    p = mk_project(client)
    t = mk_task(client, p["id"])
    assert client.post("/api/budgets", json={"scope": "studio", "period": "daily", "limit_runs": 1}).status_code in (200, 201)
    client.post(f"/api/tasks/{t['id']}/run", params={"wait": True})
    k, _ = keys(client)
    bud = [v for key, v in k.items() if key.startswith("budget_")]
    assert bud and bud[0]["severity"] == "urgent" and "ĐÃ ĐẦY" in bud[0]["title"]
    r = mk_task(client, p["id"])["id"]
    _set(client, r, status="Running", started_at=utcnow() - timedelta(minutes=45))
    assert keys(client)[0]["stale"]["count"] == 1
    # provider kiểm tra thất bại → urgent kèm bước đăng nhập
    from app.models import ProviderConfig
    with client.app.state.sf() as s:
        c = s.query(ProviderConfig).filter_by(name="claude_cli").one()
        c.last_check_status, c.last_check_message = "failed", "claude: chưa đăng nhập"
        s.commit()
    pk = keys(client)[0]["prov_claude_cli"]
    assert pk["severity"] == "urgent" and any("claude" in x for x in pk["steps"])


def test_attention_assets_lessons_and_viewer_access(client):
    from fastapi.testclient import TestClient
    p = mk_project(client)
    client.post(f"/api/projects/{p['id']}/assets", data={"name": "Không rõ nguồn", "source": "unknown"})
    from app.models import Lesson
    with client.app.state.sf() as s:
        s.add(Lesson(department_key="qa", text="đề xuất mới", status="suggested", source="ceo")); s.commit()
    k, _ = keys(client)
    assert k["assets_problem"]["count"] == 1 and "nguồn" in k["assets_problem"]["samples"][0]["detail"].lower()
    assert k["lessons"]["severity"] == "info"
    client.post("/api/users", json={"username": "viewer7", "password": "viewerpass1", "role": "viewer"})
    v = TestClient(client.app)
    v.headers["Authorization"] = "Bearer " + v.post("/api/auth/login", json={"username": "viewer7", "password": "viewerpass1"}).json()["token"]
    assert v.get("/api/ceo/attention").status_code == 200


def test_patch_task_provider_timeout_and_null_guard(client):
    p = mk_project(client)
    t = mk_task(client, p["id"])
    r = client.patch(f"/api/tasks/{t['id']}", json={"timeout_s": 300, "provider": "codex_cli", "title": None})
    assert r.status_code == 200 and r.json()["timeout_s"] == 300 and r.json()["provider"] == "codex_cli" and r.json()["title"] == t["title"]
    assert client.patch(f"/api/tasks/{t['id']}", json={"timeout_s": 9999}).status_code == 422
    assert client.patch(f"/api/tasks/{t['id']}", json={"provider": None}).json()["provider"] is None
