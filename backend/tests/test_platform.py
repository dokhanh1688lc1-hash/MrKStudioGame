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
def test_only_local_providers_exist_and_no_api_key_leak(client):
    ps = {p["name"]: p for p in client.get("/api/providers").json()}
    assert set(ps) == {"claude_cli", "codex_cli", "internal"}
    assert "price_in_per_mtok" not in str(ps) and "api_key" not in str(ps).lower()
    assert ps["claude_cli"]["configured"] and ps["claude_cli"]["enabled"]


def test_check_ok_and_failures(client, fake):
    r = client.post("/api/providers/claude_cli/check").json()
    assert r["last_check_status"] == "ok"
    fake.mode["codex_cli"] = "notlogged"
    r = client.post("/api/providers/codex_cli/check").json()
    assert r["last_check_status"] == "failed" and "chưa đăng nhập" in r["last_check_message"]


def test_missing_programs_reported(offline):
    r = offline.post("/api/providers/claude_cli/check").json()
    assert r["last_check_status"] == "failed" and "Chưa tìm thấy" in r["last_check_message"]
    assert not {p["name"]: p for p in offline.get("/api/providers").json()}["claude_cli"]["configured"]


def test_routing_follows_department_and_falls_back_to_internal(client, offline):
    pv = lambda c, d, **k: c.get("/api/routing/preview", params={"department": d, **k}).json()["chain"]
    assert pv(client, "game_dev")[0] == {"provider": "claude_cli", "model": ""}
    assert pv(client, "market_research")[0]["provider"] == "codex_cli"
    assert pv(offline, "game_dev") == [{"provider": "internal", "model": "internal"}]
    client.patch("/api/providers/claude_cli", json={"enabled": False})
    assert pv(client, "game_dev")[0]["provider"] == "codex_cli"  # claude tắt → họ còn lại


def test_change_department_family(client):
    client.patch("/api/departments/game_dev", json={"preferred_provider": "openai"})
    r = client.get("/api/routing/preview", params={"department": "game_dev"}).json()
    assert r["chain"][0]["provider"] == "codex_cli"


def test_sensitive_data_blocked_for_external(client):
    r = client.get("/api/routing/preview", params={"department": "game_dev", "sensitive": True}).json()
    assert r["chain"][0]["provider"] == "internal"
    client.patch("/api/providers/claude_cli", json={"allow_sensitive": True})
    r = client.get("/api/routing/preview", params={"department": "game_dev", "sensitive": True}).json()
    assert r["chain"][0]["provider"] == "claude_cli"


def test_legacy_api_provider_names_are_mapped(client):
    """Nhiệm vụ cũ lưu provider 'anthropic'/'openai' vẫn chạy được, qua chương trình trên máy."""
    from app.models import Task
    p = mk_project(client)
    t = mk_task(client, p["id"], "game_dev")
    with client.app.state.sf() as s:
        s.get(Task, t["id"]).provider = "anthropic"
        s.commit()
    r = client.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()
    assert r["status"] == "Completed" and r["result_source"] == "claude_cli"
    assert client.post("/api/tasks", json={"project_id": p["id"], "department_key": "qa", "title": "t", "objective": "o",
                                           "provider": "openai"}).status_code == 422  # tạo mới không còn nhận 'openai'


# ---------- chạy nhiệm vụ ----------
def test_internal_mode_task_runs_without_programs_and_is_labeled(offline):
    p = mk_project(offline)
    t = mk_task(offline, p["id"], "market_research")
    r = offline.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()
    assert r["status"] == "Completed" and r["result_source"] == "internal"
    assert "KHÔNG phải kết quả do AI" in r["result"] and r["actual_cost"] == 0.0


def test_real_provider_call_usage_and_zero_cost(client, fake):
    p = mk_project(client)
    t = mk_task(client, p["id"], "game_dev")
    r = client.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()
    assert r["status"] == "Completed" and r["result"] == "CLAUDE-OUT" and r["result_source"] == "claude_cli"
    assert r["actual_cost"] == 0.0  # gói thuê bao: không tính USD theo token
    assert fake.calls["claude_cli"] == 1 and fake.calls["codex_cli"] == 0
    u = client.get("/api/usage").json()[0]
    assert u["provider"] == "claude_cli" and u["input_tokens"] == 1000 and u["cost_usd"] == 0.0


def test_retry_then_fail_is_bounded(client, fake):
    fake.mode["claude_cli"] = "overloaded"
    p = mk_project(client)
    t = mk_task(client, p["id"], "game_dev", max_retries=2)
    r = client.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()
    assert r["status"] == "Failed" and "503" in r["error"]
    assert fake.calls["claude_cli"] == 3 and len(r["attempts"]) == 3  # 1 + 2 retry, không vô hạn


def test_non_retryable_error_does_not_retry(client, fake):
    fake.mode["claude_cli"] = "notlogged"
    p = mk_project(client)
    t = mk_task(client, p["id"], "game_dev", max_retries=3)
    r = client.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()
    assert r["status"] == "Failed" and fake.calls["claude_cli"] == 1 and "chưa đăng nhập" in r["error"]


def test_fallback_only_when_enabled(client, fake):
    fake.mode["claude_cli"] = "fail"
    p = mk_project(client)
    t = mk_task(client, p["id"], "game_dev", max_retries=0)
    assert client.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()["status"] == "Failed"
    client.patch("/api/system/settings", json={"fallback_enabled": True})
    r = client.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()
    assert r["status"] == "Completed" and r["result_source"] == "codex_cli"


def test_explicit_unusable_provider_is_422(offline):
    p = mk_project(offline)
    t = mk_task(offline, p["id"], "game_dev", provider="claude_cli")
    assert offline.post(f"/api/tasks/{t['id']}/run").status_code == 422


# ---------- ngân sách (logic kiểm tra; CLI/nội bộ luôn 0 USD nên cần dữ liệu chi phí để kích hoạt) ----------
def _seed_spend(c, project_id, cost):
    from app.models import UsageRecord
    with c.app.state.sf() as s:
        s.add(UsageRecord(project_id=project_id, department_key="game_dev", provider="claude_cli", model="", cost_usd=cost))
        s.commit()


def test_budget_blocks_when_already_spent(client, fake):
    p = mk_project(client)
    client.post("/api/budgets", json={"scope": "studio", "period": "daily", "limit_usd": 0.5})
    _seed_spend(client, p["id"], 0.6)  # đã tiêu quá hạn mức (vd. dịch vụ trả phí khác ghi nhận chi phí)
    t = mk_task(client, p["id"], "game_dev")
    r = client.post(f"/api/tasks/{t['id']}/run")
    assert r.status_code == 402 and "ngân sách" in r.json()["detail"].lower()
    assert fake.calls["claude_cli"] == 0  # không gọi khi vượt ngân sách
    assert client.get(f"/api/tasks/{t['id']}").json()["status"] == "Blocked"


def test_budget_does_not_block_when_under_limit(client):
    p = mk_project(client)
    client.post("/api/budgets", json={"scope": "studio", "period": "daily", "limit_usd": 10})
    _seed_spend(client, p["id"], 1.0)
    t = mk_task(client, p["id"], "game_dev")
    assert client.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()["status"] == "Completed"


def test_budget_summary_ratio_and_warning(client):
    p = mk_project(client)
    client.post("/api/budgets", json={"scope": "project", "scope_key": str(p["id"]), "period": "total", "limit_usd": 2})
    _seed_spend(client, p["id"], 1.0)
    b = client.get("/api/budgets").json()[0]
    assert abs(b["spent_usd"] - 1.0) < 1e-9 and abs(b["ratio"] - 0.5) < 1e-9


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
    assert fake.calls["claude_cli"] == 0
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


def test_no_api_key_concept_left(client):
    def keys(x):
        if isinstance(x, dict):
            for k, v in x.items():
                yield k
                yield from keys(v)
        elif isinstance(x, list):
            for v in x:
                yield from keys(v)
    names = set()
    for url in ("/api/providers", "/api/dashboard", "/api/system/state"):
        names |= set(keys(client.get(url).json()))
    assert not {n for n in names if "key" in n.lower() or "price" in n.lower() or n == "prefer_cli"}, names

def test_task_validation(client):
    p = mk_project(client)
    base = {"project_id": p["id"], "title": "t", "objective": "o"}
    assert client.post("/api/tasks", json={**base, "department_key": "nope"}).status_code == 422
    assert client.post("/api/tasks", json={**base, "department_key": "qa", "max_retries": 99}).status_code == 422
    assert client.post("/api/tasks", json={**base, "project_id": 999, "department_key": "qa"}).status_code == 404
