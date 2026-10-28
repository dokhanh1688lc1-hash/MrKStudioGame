import wave
from pathlib import Path

from app.routers.samples import SAMPLE
from fastapi.testclient import TestClient


def test_sample_project_is_created_with_files_and_clean_assets(client):
    r = client.post("/api/samples/godot-coin-dash")
    assert r.status_code == 201 and r.json()["assets"] == 6 and r.json()["documents"] == 5 and r.json()["test_cases"] == 12
    pid = r.json()["project_id"]
    ws = Path(client.get(f"/api/projects/{pid}").json()["workspace_path"])
    for f in ("project.godot", "main.tscn", "scripts/main.gd", "scripts/player.gd", "scripts/coin.gd", "docs/GDD.md", "docs/COPYRIGHT.md", "assets/coin.png"):
        assert (ws / f).is_file(), f
    assert not (ws / ".godot").exists()
    a = client.get(f"/api/projects/{pid}/assets").json()
    assert a["summary"]["total"] == 6 and a["summary"]["with_problems"] == 0 and a["summary"]["ai_generated"] == 0
    assert all(i["source"] == "own" and i["has_file"] and i["status"] == "draft" for i in a["items"])
    assert len(client.get(f"/api/projects/{pid}/documents").json()["items"]) == 5
    tc = client.get(f"/api/projects/{pid}/test-cases").json()
    assert tc["summary"]["total"] == 12 and tc["summary"]["not_run"] == 12 and tc["summary"]["passed"] == 0   # chưa ai chạy → không Passed
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


def test_sample_level_is_playable_by_static_geometry():
    """Kiểm tra tĩnh dữ liệu màn chơi trong main.gd: xu nằm trong thế giới, không nằm trong bậc, và nhảy tới được."""
    import re
    src = (SAMPLE / "scripts" / "main.gd").read_text(encoding="utf-8")
    plats = [tuple(map(float, m)) for m in re.findall(r"\[(\d+), (\d+), (\d+), (\d+)\]", src.split("const PLATFORMS")[1].split("const COINS")[0])]
    coins = [tuple(map(float, m)) for m in re.findall(r"Vector2\((\d+), (\d+)\)", src.split("const COINS")[1].split("var player")[0])]
    assert len(plats) == 7 and len(coins) == 12
    jump = float(re.search(r"JUMP_VELOCITY := -(\d+)", (SAMPLE / "scripts" / "player.gd").read_text()).group(1))
    grav = float(re.search(r"GRAVITY := (\d+)", (SAMPLE / "scripts" / "player.gd").read_text()).group(1))
    reach = jump * jump / (2 * grav)                      # độ cao nhảy tối đa
    tops = sorted(cy - h / 2 for cx, cy, w, h in plats)   # đỉnh các bậc (y nhỏ = cao)
    ground = max(tops)
    assert ground - min(t for t in tops if t < ground) > reach            # có bậc cao hơn một cú nhảy từ đất → cần bắc cầu bằng bậc khác
    for cx, cy in coins:
        assert 0 < cx < 1280 and 0 < cy < 360
        assert not any(px - w / 2 <= cx <= px + w / 2 and py - h / 2 <= cy <= py + h / 2 for px, py, w, h in plats), (cx, cy)
    # mỗi bậc phải có một bậc/đất khác thấp hơn không quá `reach` và gần theo chiều ngang (<= 200px)
    for cx, cy, w, h in plats:
        top = cy - h / 2
        if top >= ground:
            continue
        assert any(0 < (ot - top) <= reach and abs(ox - cx) <= 200 + (w + ow) / 2 for ox, oy, ow, oh in plats for ot in [oy - oh / 2] if (ox, oy) != (cx, cy)) or ground - top <= reach, (cx, cy)
    t = (SAMPLE / "tests" / "run_tests.gd").read_text(encoding="utf-8")
    assert "Progress.record" in t and "quit(1 if _failed > 0 else 0)" in t
