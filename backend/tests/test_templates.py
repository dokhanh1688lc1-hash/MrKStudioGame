from app.schemas import TaskIn
from .conftest import mk_project


def test_templates_cover_all_departments_and_are_valid(client):
    tpl = client.get("/api/tasks/templates/all").json()
    depts = {d["key"] for d in client.get("/api/departments").json()}
    assert set(tpl) == depts
    for key, items in tpl.items():
        assert items, key
        for t in items:
            assert all(t[f].strip() for f in ("title", "objective", "expected_output", "acceptance_criteria")), (key, t["title"])
            TaskIn(project_id=1, department_key=key, **t)  # hợp lệ với schema tạo nhiệm vụ


def test_template_creates_task(client):
    p = mk_project(client)
    t = client.get("/api/tasks/templates/all").json()["game_design"][0]
    r = client.post("/api/tasks", json={"project_id": p["id"], "department_key": "game_design", **t})
    assert r.status_code == 201 and r.json()["title"] == t["title"]
