from .conftest import mk_project


def _by_title(tasks):
    return {t["title"].split(". ", 1)[1]: t for t in tasks}


def test_template_has_gates_and_valid_dependencies(client):
    tpl = client.get("/api/pipeline/template").json()
    keys = {s["key"] for s in tpl}
    assert len(tpl) == 12
    for s in tpl:
        assert set(s["depends_on"]) <= keys
    assert {s["key"] for s in tpl if s["needs_owner_approval"]} == {"gdd", "prototype", "release_prep"}


def test_create_pipeline_once_and_isolated_per_project(offline):
    p1, p2 = mk_project(offline, "P1"), mk_project(offline, "P2")
    r = offline.post(f"/api/projects/{p1['id']}/pipeline", json={"brief": "Game puzzle cho trẻ em"})
    assert r.status_code == 201 and len(r.json()) == 12
    assert offline.post(f"/api/projects/{p1['id']}/pipeline", json={}).status_code == 409
    assert offline.post(f"/api/projects/{p2['id']}/pipeline", json={}).status_code == 201
    assert len(offline.get(f"/api/projects/{p1['id']}/pipeline").json()) == 12
    t = r.json()[0]
    assert "Game puzzle cho trẻ em" in t["context"] and "Game: P1" in t["context"]
    assert offline.post("/api/projects/999/pipeline", json={}).status_code == 404


def test_pipeline_runs_in_order_with_approval_gates_and_passes_results(offline):
    p = mk_project(offline)
    offline.post(f"/api/projects/{p['id']}/pipeline", json={"brief": "BRIEF-XYZ"})
    pid = p["id"]

    rep = offline.post(f"/api/projects/{pid}/pipeline/run-ready", params={"wait": True}).json()
    done = [r["title"] for r in rep if r["outcome"] == "finished"]
    assert [d.split(". ")[1] for d in done] == ["Nghiên cứu thị trường", "Ý tưởng game (Concept)"]
    gdd = next(r for r in rep if "GDD" in r["title"])
    assert gdd["outcome"] == "not_started" and "phê duyệt" in gdd["reason"]

    tasks = _by_title(offline.get(f"/api/projects/{pid}/pipeline").json())
    assert tasks["Tài liệu thiết kế (GDD)"]["status"] == "Awaiting Approval"
    assert tasks["Đánh giá khả thi kỹ thuật"]["status"] == "Assigned"  # chưa chạy khi GDD chưa xong

    pend = offline.get("/api/approvals", params={"status": "pending"}).json()
    assert len(pend) == 1
    offline.post(f"/api/approvals/{pend[0]['id']}/decision", json={"approve": True})

    offline.post(f"/api/projects/{pid}/pipeline/run-ready", params={"wait": True})
    tasks = _by_title(offline.get(f"/api/projects/{pid}/pipeline").json())
    assert tasks["Tài liệu thiết kế (GDD)"]["status"] == "Completed"
    for name in ("Đánh giá khả thi kỹ thuật", "Art Bible", "Audio Bible", "Mô hình kiếm tiền", "Marketing & ASO"):
        assert tasks[name]["status"] == "Completed", name
    assert tasks["Kế hoạch prototype"]["status"] == "Awaiting Approval"  # cổng thứ hai
    assert tasks["Kế hoạch kiểm thử"]["status"] == "Assigned"

    # Kết quả bước trước được đưa vào prompt của bước sau (chế độ nội bộ in lại prompt).
    detail = offline.get(f"/api/tasks/{tasks['Tài liệu thiết kế (GDD)']['id']}").json()
    assert "Kết quả từ bước trước: [Pipeline] 2. Ý tưởng game (Concept)" in detail["result"]
    assert "BRIEF-XYZ" in detail["result"]


def test_pipeline_stops_on_emergency_stop(offline):
    p = mk_project(offline)
    offline.post(f"/api/projects/{p['id']}/pipeline", json={})
    offline.post("/api/system/emergency-stop", json={"active": True})
    rep = offline.post(f"/api/projects/{p['id']}/pipeline/run-ready", params={"wait": True}).json()
    assert rep and all(r["outcome"] == "not_started" for r in rep)
    tasks = offline.get(f"/api/projects/{p['id']}/pipeline").json()
    assert all(t["status"] == "Assigned" for t in tasks)


def test_pipeline_requires_manager(client):
    p = mk_project(client)
    client.post("/api/users", json={"username": "viewer2", "password": "viewerpass1", "role": "viewer"})
    from fastapi.testclient import TestClient
    v = TestClient(client.app)
    v.headers["Authorization"] = "Bearer " + v.post("/api/auth/login", json={"username": "viewer2", "password": "viewerpass1"}).json()["token"]
    assert v.post(f"/api/projects/{p['id']}/pipeline", json={}).status_code == 403
    assert v.get("/api/pipeline/template").status_code == 200
