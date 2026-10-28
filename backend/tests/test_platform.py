from pathlib import Path

from fastapi.testclient import TestClient

from .conftest import make_client, mk_project, mk_task


# ---------- auth & quyền ----------
def test_requires_login(client):
    r = TestClient(client.app).get("/api/projects")
    assert r.status_code == 401


def test_bad_login_and_rate_limit(client):
    c = TestClient(client.app)
    for _ in range(5):
        assert c.post("/api/auth/login", json={"username": "ratelim", "password": "x"}).status_code == 401
    assert c.post("/api/auth/login", json={"username": "ratelim", "password": "x"}).status_code == 429


def test_roles_enforced_in_backend(client):
    client.post("/api/users", json={"username": "viewer1", "password": "viewerpass1", "role": "viewer"})
    v = TestClient(client.app)
    tok = v.post("/api/auth/login", json={"username": "viewer1", "password": "viewerpass1"}).json()["token"]
    v.headers["Authorization"] = f"Bearer {tok}"
    assert v.get("/api/projects").status_code == 200
    assert v.post("/api/projects", json={"name": "x"}).status_code == 403
    assert v.post("/api/system/emergency-stop", json={"active": True}).status_code == 403
    assert v.get("/api/users").status_code == 403


def test_tampered_token_rejected(client):
    c = TestClient(client.app)
    c.headers["Authorization"] = client.headers["Authorization"][:-3] + "abc"
    assert c.get("/api/projects").status_code == 401


# ---------- dự án ----------
def test_project_crud_workspace_search(client, tmp_path):
    p = mk_project(client, "Alpha Quest")
    assert Path(p["workspace_path"]).is_dir()  # workspace riêng
    assert client.post("/api/projects", json={"name": "Alpha Quest"}).status_code == 409
    mk_project(client, "Beta")
    r = client.get("/api/projects", params={"q": "alpha"}).json()
    assert r["total"] == 1 and r["items"][0]["name"] == "Alpha Quest"
    r = client.patch(f"/api/projects/{p['id']}", json={"status": "Concept"})
    assert r.json()["status"] == "Concept"
    assert client.patch(f"/api/projects/{p['id']}", json={"status": "Bogus"}).status_code == 422
    assert client.get("/api/projects/999").status_code == 404


def test_seed_departments_and_agents(client):
    deps = client.get("/api/departments").json()
    assert len(deps) == 14
    assert {d["key"]: d["preferred_provider"] for d in deps}["game_dev"] == "anthropic"
    assert {d["key"]: d["preferred_provider"] for d in deps}["market_research"] == "openai"
    assert len(client.get("/api/agents").json()) == 14


# ---------- provider & routing ----------
def test_providers_masked_and_check(client, fake):
    ps = {p["name"]: p for p in client.get("/api/providers").json()}
    assert ps["openai"]["configured"] and "sk-test-openai" not in str(ps)
    r = client.post("/api/providers/openai/check").json()
    assert r["last_check_status"] == "ok"
    fake.mode["anthropic"] = "unauth"
    assert client.post("/api/providers/anthropic/check").json()["last_check_status"] == "failed"


def test_unconfigured_provider_reported(offline):
    r = offline.post("/api/providers/openai/check").json()
    assert r["last_check_status"] == "failed" and "chưa cấu hình" in r["last_check_message"].lower()


def test_routing_follows_department_and_fallback_to_internal(client, offline):
    r = client.get("/api/routing/preview", params={"department": "game_dev"}).json()
    assert r["chain"][0] == {"provider": "anthropic", "model": "an-model"}
    r = client.get("/api/routing/preview", params={"department": "market_research"}).json()
    assert r["chain"][0]["provider"] == "openai"
    r = offline.get("/api/routing/preview", params={"department": "game_dev"}).json()
    assert r["chain"] == [{"provider": "internal", "model": "internal"}]


def test_sensitive_data_blocked_for_external(client):
    r = client.get("/api/routing/preview", params={"department": "game_dev", "sensitive": True}).json()
    assert r["chain"][0]["provider"] == "internal"
    client.patch("/api/providers/anthropic", json={"allow_sensitive": True})
    r = client.get("/api/routing/preview", params={"department": "game_dev", "sensitive": True}).json()
    assert r["chain"][0]["provider"] == "anthropic"


# ---------- chạy nhiệm vụ ----------
def test_internal_mode_task_runs_without_keys_and_is_labeled(offline):
    p = mk_project(offline)
    t = mk_task(offline, p["id"], "market_research")
    r = offline.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()
    assert r["status"] == "Completed" and r["result_source"] == "internal"
    assert "KHÔNG phải kết quả do AI" in r["result"]
    assert r["actual_cost"] == 0.0


def test_real_provider_call_cost_and_usage(client, fake):
    client.patch("/api/providers/anthropic", json={"price_in_per_mtok": 3.0, "price_out_per_mtok": 15.0})
    p = mk_project(client)
    t = mk_task(client, p["id"], "game_dev")
    r = client.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()
    assert r["status"] == "Completed" and r["result"] == "ANTHROPIC-OUT" and r["result_source"] == "anthropic"
    assert abs(r["actual_cost"] - (1000 * 3 + 500 * 15) / 1e6) < 1e-9
    assert fake.calls["anthropic"] == 1 and fake.calls["openai"] == 0
    u = client.get("/api/usage").json()[0]
    assert u["provider"] == "anthropic" and u["input_tokens"] == 1000
    assert client.get("/api/dashboard").json()["spend_today_usd"] > 0


def test_cost_unknown_when_price_not_configured(client):
    p = mk_project(client)
    t = mk_task(client, p["id"], "game_dev")
    r = client.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()
    assert r["status"] == "Completed" and r["actual_cost"] is None and r["estimated_cost"] is None
    assert client.get("/api/usage").json()[0]["cost_usd"] is None  # không bịa giá


def test_retry_then_fail_is_bounded(client, fake):
    fake.mode["anthropic"] = "500"
    p = mk_project(client)
    t = mk_task(client, p["id"], "game_dev", max_retries=2)
    r = client.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()
    assert r["status"] == "Failed" and "500" in r["error"]
    assert fake.calls["anthropic"] == 3 and len(r["attempts"]) == 3  # 1 + 2 retry, không vô hạn


def test_non_retryable_error_does_not_retry(client, fake):
    fake.mode["anthropic"] = "401"
    p = mk_project(client)
    t = mk_task(client, p["id"], "game_dev", max_retries=3)
    r = client.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()
    assert r["status"] == "Failed" and fake.calls["anthropic"] == 1


def test_timeout_is_retryable_and_reported(client, fake):
    fake.mode["openai"] = "timeout"
    p = mk_project(client)
    t = mk_task(client, p["id"], "market_research", max_retries=1)
    r = client.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()
    assert r["status"] == "Failed" and "timeout" in r["error"].lower() and fake.calls["openai"] == 2


def test_fallback_only_when_enabled(client, fake):
    fake.mode["anthropic"] = "401"
    p = mk_project(client)
    t = mk_task(client, p["id"], "game_dev", max_retries=0)
    assert client.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()["status"] == "Failed"
    client.patch("/api/system/settings", json={"fallback_enabled": True})
    r = client.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()
    assert r["status"] == "Completed" and r["result_source"] == "openai"


def test_explicit_unusable_provider_is_422(offline):
    p = mk_project(offline)
    t = mk_task(offline, p["id"], "game_dev", provider="anthropic")
    r = offline.post(f"/api/tasks/{t['id']}/run")
    assert r.status_code == 422


# ---------- ngân sách ----------
def test_budget_blocks_when_exceeded(client, fake):
    client.patch("/api/providers/anthropic", json={"price_in_per_mtok": 1000.0, "price_out_per_mtok": 1000.0})
    client.patch("/api/system/settings", json={"approval_cost_threshold_usd": 1000})
    p = mk_project(client)
    client.post("/api/budgets", json={"scope": "studio", "period": "daily", "limit_usd": 0.5})
    t = mk_task(client, p["id"], "game_dev", max_output_tokens=1024)  # ước tính ~1.0+ USD
    r = client.post(f"/api/tasks/{t['id']}/run")
    assert r.status_code == 402 and "ngân sách" in r.json()["detail"].lower()
    assert fake.calls["anthropic"] == 0  # không gọi API khi vượt ngân sách
    assert client.get(f"/api/tasks/{t['id']}").json()["status"] == "Blocked"


def test_budget_requires_price_for_external(client, fake):
    client.post("/api/budgets", json={"scope": "studio", "period": "monthly", "limit_usd": 10})
    p = mk_project(client)
    t = mk_task(client, p["id"], "game_dev")
    r = client.post(f"/api/tasks/{t['id']}/run")
    assert r.status_code == 402 and "giá" in r.json()["detail"] and fake.calls["anthropic"] == 0


def test_budget_does_not_block_internal_mode(offline):
    offline.post("/api/budgets", json={"scope": "studio", "period": "daily", "limit_usd": 0.01})
    p = mk_project(offline)
    t = mk_task(offline, p["id"], "qa")
    assert offline.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()["status"] == "Completed"


def test_task_budget_limit(client):
    client.patch("/api/providers/anthropic", json={"price_in_per_mtok": 1000.0, "price_out_per_mtok": 1000.0})
    client.patch("/api/system/settings", json={"approval_cost_threshold_usd": 1000})
    p = mk_project(client)
    t = mk_task(client, p["id"], "game_dev", budget_limit=0.001)
    assert client.post(f"/api/tasks/{t['id']}/run").status_code == 402


def test_budget_validation(client):
    assert client.post("/api/budgets", json={"scope": "studio", "limit_usd": -1}).status_code == 422
    assert client.post("/api/budgets", json={"scope": "project", "scope_key": "999", "limit_usd": 5}).status_code == 422
    assert client.post("/api/budgets", json={"scope": "studio", "limit_usd": 5}).status_code == 201
    assert client.post("/api/budgets", json={"scope": "studio", "limit_usd": 6}).status_code == 409


# ---------- phê duyệt ----------
def test_approval_flow(offline):
    p = mk_project(offline)
    t = mk_task(offline, p["id"], "qa", requires_approval=True)
    r = offline.post(f"/api/tasks/{t['id']}/run")
    assert r.status_code == 409
    assert offline.get(f"/api/tasks/{t['id']}").json()["status"] == "Awaiting Approval"
    pend = offline.get("/api/approvals", params={"status": "pending"}).json()
    assert len(pend) == 1 and pend[0]["task_id"] == t["id"]
    assert offline.post(f"/api/tasks/{t['id']}/run").status_code == 409
    assert len(offline.get("/api/approvals", params={"status": "pending"}).json()) == 1  # không tạo trùng
    offline.post(f"/api/approvals/{pend[0]['id']}/decision", json={"approve": True})
    r = offline.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()
    assert r["status"] == "Completed"
    assert offline.post(f"/api/approvals/{pend[0]['id']}/decision", json={"approve": False}).status_code == 409


def test_rejected_approval_cancels_task(offline):
    p = mk_project(offline)
    t = mk_task(offline, p["id"], "qa", requires_approval=True)
    offline.post(f"/api/tasks/{t['id']}/run")
    a = offline.get("/api/approvals").json()[0]
    offline.post(f"/api/approvals/{a['id']}/decision", json={"approve": False})
    assert offline.get(f"/api/tasks/{t['id']}").json()["status"] == "Cancelled"


def test_cost_over_threshold_requires_approval(client, fake):
    client.patch("/api/providers/anthropic", json={"price_in_per_mtok": 1000.0, "price_out_per_mtok": 1000.0})
    p = mk_project(client)
    t = mk_task(client, p["id"], "game_dev")
    assert client.post(f"/api/tasks/{t['id']}/run").status_code == 409
    assert fake.calls["anthropic"] == 0


# ---------- dependency, hủy, trùng lặp, dừng khẩn cấp ----------
def test_dependencies_block_until_complete(offline):
    p = mk_project(offline)
    a = mk_task(offline, p["id"], "qa")
    b = mk_task(offline, p["id"], "qa", depends_on=[a["id"]])
    assert offline.post(f"/api/tasks/{b['id']}/run").status_code == 409
    assert offline.get(f"/api/tasks/{b['id']}").json()["status"] == "Blocked"
    offline.post(f"/api/tasks/{a['id']}/run", params={"wait": True})
    assert offline.post(f"/api/tasks/{b['id']}/run", params={"wait": True}).json()["status"] == "Completed"


def test_dependency_must_be_same_project(offline):
    p1, p2 = mk_project(offline, "P1"), mk_project(offline, "P2")
    a = mk_task(offline, p1["id"], "qa")
    r = offline.post("/api/tasks", json={"project_id": p2["id"], "department_key": "qa", "title": "x",
                                         "objective": "y", "depends_on": [a["id"]]})
    assert r.status_code == 422


def test_cancel_and_no_rerun_of_final(offline):
    p = mk_project(offline)
    t = mk_task(offline, p["id"], "qa")
    assert offline.post(f"/api/tasks/{t['id']}/cancel").json()["status"] == "Cancelled"
    assert offline.post(f"/api/tasks/{t['id']}/run").status_code == 409
    assert offline.post(f"/api/tasks/{t['id']}/cancel").status_code == 409


def test_no_duplicate_run(offline):
    from app.models import Task
    p = mk_project(offline)
    t = mk_task(offline, p["id"], "qa")
    with offline.app.state.sf() as s:  # mô phỏng đang chạy
        s.get(Task, t["id"]).status = "Running"
        s.commit()
    assert offline.post(f"/api/tasks/{t['id']}/run").status_code == 409


def test_emergency_stop(client, fake):
    p = mk_project(client)
    t = mk_task(client, p["id"], "game_dev")
    r = client.post("/api/system/emergency-stop", json={"active": True}).json()
    assert r["emergency_stop"] is True
    assert client.post(f"/api/tasks/{t['id']}/run").status_code == 423
    assert fake.calls["anthropic"] == 0
    client.post("/api/system/emergency-stop", json={"active": False})
    assert client.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()["status"] == "Completed"


def test_restart_recovers_running_tasks(tmp_path, fake):
    from app.models import Task
    c = make_client(tmp_path, fake)
    p = mk_project(c)
    t = mk_task(c, p["id"], "qa")
    with c.app.state.sf() as s:
        s.get(Task, t["id"]).status = "Running"
        s.commit()
    c2 = make_client(tmp_path, fake)  # "khởi động lại" trên cùng database
    got = c2.get(f"/api/tasks/{t['id']}").json()
    assert got["status"] == "Failed" and "gián đoạn" in got["error"]


# ---------- audit / bí mật ----------
def test_audit_log_records_actions(client):
    p = mk_project(client)
    mk_task(client, p["id"], "qa")
    actions = {a["action"] for a in client.get("/api/audit").json()["items"]}
    assert {"login", "project_created", "task_created", "bootstrap_owner"} <= actions


def test_no_secret_leak_in_api(client):
    dump = str(client.get("/api/providers").json()) + str(client.get("/api/dashboard").json())
    assert "sk-test-openai" not in dump and "sk-ant-test" not in dump


def test_task_validation(client):
    p = mk_project(client)
    base = {"project_id": p["id"], "title": "t", "objective": "o"}
    assert client.post("/api/tasks", json={**base, "department_key": "nope"}).status_code == 422
    assert client.post("/api/tasks", json={**base, "department_key": "qa", "max_retries": 99}).status_code == 422
    assert client.post("/api/tasks", json={**base, "project_id": 999, "department_key": "qa"}).status_code == 404
