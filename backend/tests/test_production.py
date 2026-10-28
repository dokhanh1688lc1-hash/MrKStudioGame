from pathlib import Path

from fastapi.testclient import TestClient

from app.models import Task
from .conftest import mk_project, mk_task


def viewer(client, name="viewer8"):
    client.post("/api/users", json={"username": name, "password": "viewerpass1", "role": "viewer"})
    v = TestClient(client.app)
    v.headers["Authorization"] = "Bearer " + v.post("/api/auth/login", json={"username": name, "password": "viewerpass1"}).json()["token"]
    return v


def manager(client, name="mgr1"):
    client.post("/api/users", json={"username": name, "password": "managerpass1", "role": "manager"})
    m = TestClient(client.app)
    m.headers["Authorization"] = "Bearer " + m.post("/api/auth/login", json={"username": name, "password": "managerpass1"}).json()["token"]
    return m


# ---------- tài liệu ----------
def test_documents_are_versioned_and_approval_is_owner_only(client):
    p = mk_project(client)
    a = client.post(f"/api/projects/{p['id']}/documents", json={"kind": "gdd", "title": "GDD", "content": "v1 nội dung"}).json()
    b = client.post(f"/api/projects/{p['id']}/documents", json={"kind": "gdd", "title": "GDD", "content": "v2 nội dung"}).json()
    assert (a["version"], b["version"]) == (1, 2)
    lst = client.get(f"/api/projects/{p['id']}/documents").json()["items"]
    assert len(lst) == 1 and lst[0]["id"] == b["id"] and lst[0]["versions"] == 2
    full = client.get(f"/api/documents/{b['id']}").json()
    assert full["content"] == "v2 nội dung" and [h["version"] for h in full["history"]] == [2, 1]
    m = manager(client)
    assert m.post(f"/api/documents/{b['id']}/status", json={"status": "approved"}).status_code == 403
    assert client.post(f"/api/documents/{b['id']}/status", json={"status": "approved"}).json()["status"] == "approved"
    assert client.post(f"/api/documents/{b['id']}/status", json={"status": "x"}).status_code == 422
    assert m.delete(f"/api/documents/{a['id']}").status_code == 403
    assert client.delete(f"/api/documents/{a['id']}").status_code == 204


def test_document_from_task_needs_completed_result_and_masks_secrets(client):
    p, q = mk_project(client, "A"), mk_project(client, "B")
    t = mk_task(client, p["id"])
    assert client.post(f"/api/projects/{p['id']}/documents/from-task/{t['id']}", json={"kind": "design"}).status_code == 409
    with client.app.state.sf() as s:
        x = s.get(Task, t["id"]); x.status, x.result = "Completed", "Kết quả sk-ant-api03-ABCDEFGHIJKLMNOPQRSTUVWXYZ012345 hết"; s.commit()
    assert client.post(f"/api/projects/{q['id']}/documents/from-task/{t['id']}", json={}).status_code == 404   # sai dự án
    r = client.post(f"/api/projects/{p['id']}/documents/from-task/{t['id']}", json={"kind": "design"})
    assert r.status_code == 201 and r.json()["task_id"] == t["id"]
    assert "ABCDEFGH" not in client.get(f"/api/documents/{r.json()['id']}").json()["content"]
    assert client.post(f"/api/projects/{p['id']}/documents", json={"kind": "nope", "title": "x"}).status_code == 422


# ---------- kiểm thử ----------
def test_test_status_only_changes_through_real_runs(client):
    p = mk_project(client)
    c = client.post(f"/api/projects/{p['id']}/test-cases", json={"title": "Nhảy được", "steps": "bấm Space", "expected": "nhân vật nhảy"}).json()
    assert c["status"] == "not_run"
    sm = client.get(f"/api/projects/{p['id']}/test-cases").json()["summary"]
    assert sm["not_run"] == 1 and sm["passed"] == 0
    assert client.post(f"/api/test-cases/{c['id']}/runs", json={"status": "failed", "notes": "không nhảy"}).status_code == 422   # thiếu mức độ
    assert client.post(f"/api/test-cases/{c['id']}/runs", json={"status": "failed", "severity": "high"}).status_code == 422       # thiếu mô tả
    assert client.post(f"/api/test-cases/{c['id']}/runs", json={"status": "passed", "severity": "low"}).status_code == 422
    assert client.post(f"/api/test-cases/{c['id']}/runs", json={"status": "failed", "severity": "high", "notes": "không nhảy"}).status_code == 201
    it = client.get(f"/api/projects/{p['id']}/test-cases").json()
    assert it["items"][0]["status"] == "failed" and it["items"][0]["severity"] == "high"
    assert it["summary"]["bugs_by_severity"]["high"] == 1
    assert client.post(f"/api/test-cases/{c['id']}/runs", json={"status": "passed"}).status_code == 201     # xác nhận đã sửa
    assert client.get(f"/api/projects/{p['id']}/test-cases").json()["summary"]["passed"] == 1
    assert [r["status"] for r in client.get(f"/api/test-cases/{c['id']}/runs").json()["items"]] == ["passed", "failed"]


def test_import_cases_and_permissions(client):
    p = mk_project(client)
    r = client.post(f"/api/projects/{p['id']}/test-cases/import", json={"lines": "Lưu điểm | thoát game | điểm còn | save\n\nChơi lại | bấm R | reset"})
    assert r.json()["created"] == 2
    assert client.post(f"/api/projects/{p['id']}/test-cases/import", json={"lines": " | \n"}).status_code == 422
    v = viewer(client)
    cid = client.get(f"/api/projects/{p['id']}/test-cases").json()["items"][0]["id"]
    assert v.post(f"/api/test-cases/{cid}/runs", json={"status": "passed"}).status_code == 403
    assert v.get(f"/api/projects/{p['id']}/test-cases").status_code == 200
    assert manager(client).delete(f"/api/test-cases/{cid}").status_code == 403
    assert client.delete(f"/api/test-cases/{cid}").status_code == 204


# ---------- build + checklist ----------
def _ws(client, pid):
    return Path(client.get(f"/api/projects/{pid}").json()["workspace_path"])


def test_builds_need_real_file_and_release_requires_full_checklist(client):
    p = mk_project(client)
    pid = p["id"]
    assert client.post(f"/api/projects/{pid}/builds", json={"version": "1.0.0", "status": "ready"}).status_code == 422
    assert client.post(f"/api/projects/{pid}/builds", json={"version": "1.0.0", "file_path": "../x.exe"}).status_code == 422
    assert client.post(f"/api/projects/{pid}/builds", json={"version": "1.0.0", "file_path": "build/none.zip"}).status_code == 422
    (_ws(client, pid) / "build").mkdir()
    (_ws(client, pid) / "build" / "game.zip").write_bytes(b"PK\x03\x04")
    b = client.post(f"/api/projects/{pid}/builds", json={"version": "1.0.0", "platform": "windows", "status": "ready", "file_path": "build/game.zip", "changelog": "đầu tiên"})
    assert b.status_code == 201
    assert client.post(f"/api/projects/{pid}/builds", json={"version": "1.0.0", "platform": "windows"}).status_code == 409
    bid = b.json()["id"]
    r = client.post(f"/api/builds/{bid}/status", json={"status": "released"})
    assert r.status_code == 409 and "Checklist" in r.json()["detail"]
    assert manager(client).post(f"/api/builds/{bid}/status", json={"status": "released"}).status_code == 403


def test_checklist_auto_items_follow_real_data_and_full_flow(client):
    p = mk_project(client)
    pid = p["id"]
    ck = client.get(f"/api/projects/{pid}/release-checklist").json()
    assert ck["ready"] is False   # (dự án chưa có tài sản nên mục tài sản tạm đạt)
    byk = {i["key"]: i for i in ck["items"]}
    assert byk["docs_approved"]["done"] is False and byk["tests_pass"]["done"] is False and byk["build_ready"]["done"] is False
    assert client.put(f"/api/projects/{pid}/release-checklist/tests_pass", json={"done": True}).status_code == 422    # tự động, không tick tay
    assert manager(client).put(f"/api/projects/{pid}/release-checklist/owner_approval", json={"done": True}).status_code == 403
    assert client.put(f"/api/projects/{pid}/release-checklist/nope", json={"done": True}).status_code == 404
    # GDD được duyệt
    d = client.post(f"/api/projects/{pid}/documents", json={"kind": "gdd", "title": "GDD", "content": "x"}).json()
    client.post(f"/api/documents/{d['id']}/status", json={"status": "approved"})
    # test passed
    c = client.post(f"/api/projects/{pid}/test-cases", json={"title": "T"}).json()
    client.post(f"/api/test-cases/{c['id']}/runs", json={"status": "passed"})
    # build ready
    (_ws(client, pid) / "g.zip").write_bytes(b"PK")
    b = client.post(f"/api/projects/{pid}/builds", json={"version": "1.0", "status": "ready", "file_path": "g.zip"}).json()
    # tài sản chưa rõ nguồn gốc → chặn
    client.post(f"/api/projects/{pid}/assets", data={"name": "mơ hồ", "source": "unknown"})
    assert {i["key"]: i["done"] for i in client.get(f"/api/projects/{pid}/release-checklist").json()["items"]}["assets_approved"] is False
    aid = client.get(f"/api/projects/{pid}/assets").json()["items"][0]["id"]
    client.patch(f"/api/assets/{aid}", json={"source": "own"})
    client.post(f"/api/assets/{aid}/decision", json={"status": "approved"})
    for k in ("licenses_reviewed", "store_metadata", "privacy_policy", "monetization_tested"):
        assert client.put(f"/api/projects/{pid}/release-checklist/{k}", json={"done": True, "note": "ok"}).status_code == 200
    ck = client.get(f"/api/projects/{pid}/release-checklist").json()
    assert ck["ready"] is False and [i["key"] for i in ck["items"] if not i["done"]] == ["owner_approval"]
    assert client.post(f"/api/builds/{b['id']}/status", json={"status": "released"}).status_code == 409
    assert client.put(f"/api/projects/{pid}/release-checklist/owner_approval", json={"done": True}).json()["ready"] is True
    assert client.post(f"/api/builds/{b['id']}/status", json={"status": "released"}).json()["status"] == "released"
    # lỗi nghiêm trọng mới → checklist lùi lại
    c2 = client.post(f"/api/projects/{pid}/test-cases", json={"title": "T2"}).json()
    client.post(f"/api/test-cases/{c2['id']}/runs", json={"status": "failed", "severity": "critical", "notes": "crash"})
    assert client.get(f"/api/projects/{pid}/release-checklist").json()["ready"] is False


# ---------- tài chính ----------
def test_finance_revenue_counts_only_after_owner_confirms(client):
    p = mk_project(client)
    base = {"occurred_on": "2026-10-01", "project_id": p["id"]}
    client.post("/api/finance/records", json={**base, "kind": "cost", "category": "ai_subscription", "amount": "20.00"})
    client.post("/api/finance/records", json={**base, "kind": "cost", "category": "tool", "amount": "5.50", "estimated": True})
    rv = client.post("/api/finance/records", json={**base, "kind": "revenue", "category": "ads", "amount": "12.34"}).json()
    client.post("/api/finance/records", json={**base, "kind": "cost", "amount": "100000", "currency": "VND"})
    s = client.get("/api/finance/summary", params={"project_id": p["id"]}).json()
    usd = next(c for c in s["currencies"] if c["currency"] == "USD")
    assert usd["cost_actual"] == 20.0 and usd["cost_estimated"] == 5.5 and usd["revenue_confirmed"] == 0 and usd["revenue_pending"] == 12.34
    assert usd["profit"] == -20.0 and any(c["currency"] == "VND" for c in s["currencies"])     # không trộn tiền tệ
    assert manager(client).post(f"/api/finance/records/{rv['id']}/confirm").status_code == 403
    client.post(f"/api/finance/records/{rv['id']}/confirm")
    usd = next(c for c in client.get("/api/finance/summary").json()["currencies"] if c["currency"] == "USD")
    assert usd["revenue_confirmed"] == 12.34 and usd["profit"] == 12.34 - 20.0
    assert "gói thuê bao" in s["note"]


def test_finance_validation_and_permissions(client):
    ok = {"kind": "cost", "occurred_on": "2026-10-01", "amount": "1.00"}
    for bad in ({"amount": "0"}, {"amount": "-3"}, {"amount": "1.234"}, {"amount": "abc"}, {"occurred_on": "01/10/2026"},
                {"currency": "usd"}, {"kind": "revenue", "estimated": True}, {"project_id": 999}):
        r = client.post("/api/finance/records", json={**ok, **bad})
        assert r.status_code in (404, 422), bad
    v = viewer(client)
    assert v.get("/api/finance/summary").status_code == 403
    assert v.post("/api/finance/records", json=ok).status_code == 403
    rid = client.post("/api/finance/records", json=ok).json()["id"]
    assert manager(client).delete(f"/api/finance/records/{rid}").status_code == 403
    assert client.delete(f"/api/finance/records/{rid}").status_code == 204


# ---------- analytics ----------
def test_analytics_requires_source_period_and_limitations(client):
    p = mk_project(client)
    good = {"title": "Tuần 1", "source": "Google Play Console (xuất tay)", "period_start": "2026-10-01", "period_end": "2026-10-07",
            "metrics": {"D1 retention %": 31.5, "crash rate": 0.4}, "limitations": "Chỉ có 120 người dùng", "summary": "ổn"}
    r = client.post(f"/api/projects/{p['id']}/analytics", json=good)
    assert r.status_code == 201 and r.json()["metrics"]["D1 retention %"] == 31.5
    for bad in ({"source": ""}, {"limitations": ""}, {"period_end": "2026-09-01"}, {"period_start": "xx"}, {"metrics": {"": 1}}, {"metrics": {"a": "text"}}):
        assert client.post(f"/api/projects/{p['id']}/analytics", json={**good, **bad}).status_code == 422, bad
    assert len(client.get(f"/api/projects/{p['id']}/analytics").json()["items"]) == 1
    assert manager(client).delete(f"/api/analytics/{r.json()['id']}").status_code == 403
    assert client.delete(f"/api/analytics/{r.json()['id']}").status_code == 204


def test_studio_overview(client):
    a, b = mk_project(client, "A"), mk_project(client, "B")
    t = mk_task(client, a["id"])
    with client.app.state.sf() as s:
        x = s.get(Task, t["id"]); x.status = "Completed"; s.commit()
    client.post(f"/api/projects/{a['id']}/test-cases", json={"title": "x"})
    items = {i["name"]: i for i in client.get("/api/studio/overview").json()["items"]}
    assert items["A"]["tasks"]["pct"] == 100 and items["A"]["tests"]["total"] == 1 and items["B"]["tasks"]["total"] == 0
    assert items["A"]["release"]["total"] == 10 and viewer(client).get("/api/studio/overview").status_code == 200


def test_archived_project_is_read_only(client):
    p = mk_project(client)
    client.patch(f"/api/projects/{p['id']}", json={"status": "Archived"})
    assert client.post(f"/api/projects/{p['id']}/documents", json={"title": "x"}).status_code == 409
    assert client.post(f"/api/projects/{p['id']}/test-cases", json={"title": "x"}).status_code == 409
    assert client.get(f"/api/projects/{p['id']}/documents").status_code == 200


def test_paused_project_blocks_runs_until_resumed(client, fake):
    p = mk_project(client)
    t = mk_task(client, p["id"])
    client.patch(f"/api/projects/{p['id']}", json={"status": "Paused"})
    r = client.post(f"/api/tasks/{t['id']}/run")
    assert r.status_code == 409 and "tạm dừng" in r.json()["detail"]
    from app.services.guidance import explain_error
    assert explain_error(r.json()["detail"])["code"] == "paused"
    client.patch(f"/api/projects/{p['id']}", json={"status": "Production"})
    assert client.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()["status"] == "Completed"
