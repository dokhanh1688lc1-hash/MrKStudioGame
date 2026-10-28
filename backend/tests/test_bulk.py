import time

from .conftest import mk_project


BODY = {"title": "Phân tích thị trường & ý tưởng", "objective": "Đề xuất hướng phát triển game puzzle"}


def test_bulk_creates_one_task_per_department(client):
    p = mk_project(client)
    r = client.post("/api/tasks/bulk", json={**BODY, "project_id": p["id"],
                    "department_keys": ["market_research", "game_design", "qa", "qa"],
                    "notes": {"qa": "Chỉ kiểm thử luồng tutorial"}})
    assert r.status_code == 201, r.text
    ids = r.json()["task_ids"]
    assert len(ids) == 3  # bỏ trùng "qa"
    tasks = [client.get(f"/api/tasks/{i}").json() for i in ids]
    assert [t["department_key"] for t in tasks] == ["market_research", "game_design", "qa"]
    assert all(t["status"] == "Assigned" and t["title"] == BODY["title"] for t in tasks)
    assert "Chỉ kiểm thử luồng tutorial" in tasks[2]["objective"] and "Ghi chú" not in tasks[0]["objective"]


def test_bulk_is_all_or_nothing(client):
    p = mk_project(client)
    r = client.post("/api/tasks/bulk", json={**BODY, "project_id": p["id"], "department_keys": ["qa", "khong_co"]})
    assert r.status_code == 422
    r = client.post("/api/tasks/bulk", json={**BODY, "project_id": p["id"], "department_keys": ["qa"], "notes": {"art": "x"}})
    assert r.status_code == 422
    assert client.get(f"/api/tasks?project_id={p['id']}").json()["total"] == 0


def test_bulk_validation_and_permissions(client):
    p = mk_project(client)
    assert client.post("/api/tasks/bulk", json={**BODY, "project_id": p["id"], "department_keys": []}).status_code == 422
    assert client.post("/api/tasks/bulk", json={**BODY, "project_id": 9999, "department_keys": ["qa"]}).status_code == 404


def test_bulk_run_now_starts_each_task(client, fake):
    p = mk_project(client)
    r = client.post("/api/tasks/bulk", json={**BODY, "project_id": p["id"], "run_now": True,
                    "department_keys": ["game_dev", "qa"]}).json()
    assert len(r["started"]) == 2 and not r["run_errors"]
    for _ in range(100):
        sts = [client.get(f"/api/tasks/{i}").json()["status"] for i in r["task_ids"]]
        if all(s == "Completed" for s in sts):
            break
        time.sleep(0.1)
    assert sts == ["Completed", "Completed"]
    assert fake.calls["claude_cli"] == 2


def test_bulk_run_now_reports_blocked_tasks(client):
    p = mk_project(client)
    r = client.post("/api/tasks/bulk", json={**BODY, "project_id": p["id"], "run_now": True, "requires_approval": True,
                    "department_keys": ["qa"]}).json()
    assert r["started"] == [] and r["run_errors"]  # cần phê duyệt trước
