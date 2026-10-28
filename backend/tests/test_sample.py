import wave
from pathlib import Path

from app.routers.samples import SAMPLE
from fastapi.testclient import TestClient


def test_sample_project_is_created_with_files_and_clean_assets(client):
    r = client.post("/api/samples/godot-coin-dash")
    assert r.status_code == 201 and r.json()["assets"] == 6
    pid = r.json()["project_id"]
    ws = Path(client.get(f"/api/projects/{pid}").json()["workspace_path"])
    for f in ("project.godot", "main.tscn", "scripts/main.gd", "scripts/player.gd", "scripts/coin.gd", "docs/GDD.md", "docs/COPYRIGHT.md", "assets/coin.png"):
        assert (ws / f).is_file(), f
    assert not (ws / ".godot").exists()
    a = client.get(f"/api/projects/{pid}/assets").json()
    assert a["summary"]["total"] == 6 and a["summary"]["with_problems"] == 0 and a["summary"]["ai_generated"] == 0
    assert all(i["source"] == "own" and i["has_file"] and i["status"] == "draft" for i in a["items"])
    aid = a["items"][0]["id"]
    assert client.post(f"/api/assets/{aid}/decision", json={"status": "approved"}).status_code == 200  # không có vấn đề → duyệt được
    assert client.get(f"/api/assets/{aid}/file").status_code == 200


def test_second_call_gets_unique_name_and_listing(client):
    n1 = client.post("/api/samples/godot-coin-dash").json()["name"]
    n2 = client.post("/api/samples/godot-coin-dash").json()["name"]
    assert n1 != n2 and n2.endswith("2")
    assert client.get("/api/samples").json()[0]["available"] is True


def test_manager_only(client):
    client.post("/api/users", json={"username": "viewer5", "password": "viewerpass1", "role": "viewer"})
    v = TestClient(client.app)
    v.headers["Authorization"] = "Bearer " + v.post("/api/auth/login", json={"username": "viewer5", "password": "viewerpass1"}).json()["token"]
    assert v.post("/api/samples/godot-coin-dash").status_code == 403
    assert v.get("/api/samples").status_code == 200


def test_sample_sources_are_consistent():
    """Kiểm tra tĩnh: mọi res:// được tham chiếu đều tồn tại, tài sản hợp lệ, GDScript cân bằng ngoặc."""
    import json, re
    refs = set()
    for f in list(SAMPLE.glob("scripts/*.gd")) + [SAMPLE / "main.tscn", SAMPLE / "project.godot"]:
        txt = f.read_text(encoding="utf-8")
        refs |= set(re.findall(r'res://([\w/.\-]+)', txt))
        assert txt.count("(") == txt.count(")") and txt.count("[") == txt.count("]") and txt.count("{") == txt.count("}"), f
        assert "\t" in txt or f.suffix != ".gd"  # GDScript dùng tab
        assert not re.search(r"^ +\S", txt, re.M) or f.suffix != ".gd", f"{f} thụt lề bằng dấu cách"
    for r in refs:
        assert (SAMPLE / r).is_file(), r
    man = json.loads((SAMPLE / "asset-manifest.json").read_text(encoding="utf-8"))
    on_disk = {p.name for p in (SAMPLE / "assets").iterdir()}
    assert {Path(a["file"]).name for a in man["assets"]} == on_disk
    for a in man["assets"]:
        data = (SAMPLE / a["file"]).read_bytes()
        if a["file"].endswith(".png"):
            assert data[:8] == b"\x89PNG\r\n\x1a\n"
        else:
            with wave.open(str(SAMPLE / a["file"])) as w:
                assert w.getnframes() > 1000 and w.getframerate() == 22050
    for c in ("COPYRIGHT.md", "GDD.md"):
        assert (SAMPLE / "docs" / c).read_text(encoding="utf-8").strip()
