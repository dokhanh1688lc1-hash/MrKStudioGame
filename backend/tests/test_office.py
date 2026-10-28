from .conftest import mk_project, mk_task


def test_office_counts_per_department(client):
    p = mk_project(client)
    t = mk_task(client, p["id"], "game_dev")
    mk_task(client, p["id"], "game_dev")
    mk_task(client, p["id"], "qa")
    client.post(f"/api/tasks/{t['id']}/run", params={"wait": True})
    rows = {r["key"]: r for r in client.get("/api/office").json()}
    assert len(rows) == 14
    assert rows["game_dev"]["done"] == 1 and rows["game_dev"]["queued"] == 1 and rows["game_dev"]["agents"] >= 1
    assert rows["qa"]["queued"] == 1 and rows["market_research"]["done"] == 0
