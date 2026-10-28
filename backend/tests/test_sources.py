import os
from pathlib import Path

import pytest

from app.services import sources as src
from .conftest import mk_project


@pytest.fixture()
def tree(tmp_path):
    root = tmp_path / "mygames"
    g = root / "puzzle"
    (g / "scripts").mkdir(parents=True)
    (g / ".git").mkdir()
    (g / ".git" / "config").write_text("x")
    (g / "node_modules").mkdir()
    (g / "node_modules" / "a.js").write_text("x")
    (g / "project.godot").write_text("config_version=5")
    (g / "scripts" / "player.gd").write_text("extends Node")
    (g / ".env").write_text("API_KEY=abc")
    (g / "key.pem").write_text("secret")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "passwords.txt").write_text("hunter2")
    try:
        os.symlink(outside, g / "link_out")
        os.symlink(outside / "passwords.txt", g / "link.txt")
    except (OSError, NotImplementedError):
        pass
    return {"root": root, "game": g, "outside": outside}


def _roots(c, *paths):
    r = c.put("/api/system/import-roots", json={"paths": [str(p) for p in paths]})
    assert r.status_code == 200, r.text
    return r.json()


def test_folder_import_requires_allowed_roots(client, tree):
    p = mk_project(client)
    r = client.post(f"/api/projects/{p['id']}/import/folder", json={"path": str(tree["game"])})
    assert r.status_code == 403 and "thư mục gốc" in r.json()["detail"]


def test_folder_import_copies_safely(client, tree):
    p = mk_project(client)
    _roots(client, tree["root"])
    r = client.post(f"/api/projects/{p['id']}/import/folder", json={"path": str(tree["game"])})
    assert r.status_code == 201, r.text
    files = {f["path"] for f in client.get(f"/api/projects/{p['id']}/files").json()["files"]}
    assert any(f.endswith("project.godot") for f in files) and any(f.endswith("scripts/player.gd") for f in files)
    assert not any(".git/" in f or "node_modules" in f or f.endswith(".env") or f.endswith(".pem") or "passwords" in f
                   or "link" in f for f in files)
    assert any("tệp bí mật" in x for x in r.json()["skipped"])
    got = client.get(f"/api/projects/{p['id']}").json()
    assert got["source_type"] == "folder" and got["source_ref"] == str(tree["game"].resolve()) and got["source_synced_at"]
    assert (tree["game"] / ".env").read_text() == "API_KEY=abc"  # thư mục gốc không bị đụng tới


def test_folder_import_blocks_outside_and_traversal(client, tree, tmp_path):
    p = mk_project(client)
    _roots(client, tree["root"])
    for bad in (tree["outside"], tree["root"] / ".." / "outside", tmp_path, "/"):
        r = client.post(f"/api/projects/{p['id']}/import/folder", json={"path": str(bad)})
        assert r.status_code == 403, (bad, r.text)
    assert client.post(f"/api/projects/{p['id']}/import/folder", json={"path": str(tree["root"] / "none")}).status_code == 404
    if (tree["game"] / "link_out").is_symlink():  # symlink trỏ ra ngoài vùng cho phép
        assert client.post(f"/api/projects/{p['id']}/import/folder", json={"path": str(tree["game"] / "link_out")}).status_code == 403


def test_roots_validation_and_permissions(client, tree, tmp_path):
    assert client.put("/api/system/import-roots", json={"paths": ["relative/path"]}).status_code == 422
    assert client.put("/api/system/import-roots", json={"paths": [str(tmp_path / "nope")]}).status_code == 422
    assert client.put("/api/system/import-roots", json={"paths": ["/"]}).status_code == 422
    assert _roots(client, tree["root"], tree["root"])["paths"] == [str(tree["root"].resolve())]
    # manager không được đổi thư mục gốc
    client.post("/api/users", json={"username": "mgr1", "password": "Passw0rd!x", "role": "manager"})
    tok = client.post("/api/auth/login", json={"username": "mgr1", "password": "Passw0rd!x"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert client.put("/api/system/import-roots", json={"paths": []}, headers=h).status_code == 403
    assert client.get("/api/system/import-roots", headers=h).status_code == 200


def test_browse_stays_inside_roots(client, tree):
    _roots(client, tree["root"])
    top = client.get("/api/system/browse").json()
    assert top["dirs"] == [str(tree["root"].resolve())]
    sub = client.get("/api/system/browse", params={"path": str(tree["root"])}).json()
    assert str(tree["game"].resolve()) in sub["dirs"] and sub["parent"] == ""
    assert client.get("/api/system/browse", params={"path": str(tree["outside"])}).status_code == 403


@pytest.mark.parametrize("url", ["http://github.com/a/b", "https://evil.com/a/b", "git@github.com:a/b.git",
                                 "file:///etc/passwd", "https://github.com/a/b/../../c", "--upload-pack=x",
                                 "https://github.com/a", "https://github.com/a/b?x=1", "https://github.com.evil.com/a/b",
                                 "https://user:pw@github.com/a/b"])
def test_github_url_rejected(client, url):
    p = mk_project(client)
    r = client.post(f"/api/projects/{p['id']}/import/github", json={"url": url})
    assert r.status_code in (422,), (url, r.text)


def test_github_branch_validation(client):
    p = mk_project(client)
    for br in ("--evil", "a b", "x;rm", "a..b"):
        r = client.post(f"/api/projects/{p['id']}/import/github", json={"url": "https://github.com/a/b", "branch": br})
        assert r.status_code == 422, br


def _fake_clone(tree):
    def clone(url, branch, dest):
        import shutil
        shutil.copytree(tree["game"], dest, symlinks=True)
        clone.calls.append((url, branch))
        return "abcdef1234567890"
    clone.calls = []
    return clone


def test_github_import_and_sync(client, tree, monkeypatch):
    fake = _fake_clone(tree)
    monkeypatch.setattr(src, "_clone", fake)
    p = mk_project(client)
    r = client.post(f"/api/projects/{p['id']}/import/github", json={"url": "https://github.com/me/my-game/", "branch": "dev"})
    assert r.status_code == 201, r.text
    assert fake.calls == [("https://github.com/me/my-game.git", "dev")]
    assert r.json()["commit"].startswith("abcdef12")
    got = client.get(f"/api/projects/{p['id']}").json()
    assert got["source_type"] == "github" and got["source_ref"] == "https://github.com/me/my-game" and got["source_branch"] == "dev"
    files = {f["path"] for f in client.get(f"/api/projects/{p['id']}/files").json()["files"]}
    assert not any(f.endswith(".env") or ".git/" in f for f in files)
    # đồng bộ lại → thư mục imports mới, giữ bản cũ
    r2 = client.post(f"/api/projects/{p['id']}/sync")
    assert r2.status_code == 201 and len(fake.calls) == 2
    assert len(client.get(f"/api/projects/{p['id']}/files").json()["imports"]) == 2


def test_sync_requires_linked_source_and_archived_blocked(client, tree, monkeypatch):
    p = mk_project(client)
    assert client.post(f"/api/projects/{p['id']}/sync").status_code == 409
    monkeypatch.setattr(src, "_clone", _fake_clone(tree))
    client.patch(f"/api/projects/{p['id']}", json={"status": "Archived"})
    r = client.post(f"/api/projects/{p['id']}/import/github", json={"url": "https://github.com/me/x"})
    assert r.status_code == 409


def test_real_git_clone_of_local_repo(tmp_path):
    """Kiểm tra lệnh git thật (không qua mạng) bằng repo cục bộ."""
    import shutil, subprocess
    if not shutil.which("git"):
        pytest.skip("không có git")
    repo = tmp_path / "r"
    repo.mkdir()
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    for cmd in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-qm", "i"]):
        if cmd[0] == "add":
            (repo / "a.gd").write_text("x")
        subprocess.run(["git", "-C", str(repo), *cmd], check=True, env=env)
    dest = tmp_path / "clone"
    commit = src._clone(str(repo), "", dest)
    assert len(commit) == 40 and (dest / "a.gd").exists()
    with pytest.raises(Exception):
        src._clone(str(tmp_path / "missing"), "", tmp_path / "c2")


def test_owner_can_grant_and_import_in_one_step(client, tree):
    p = mk_project(client)
    r = client.post(f"/api/projects/{p['id']}/import/folder", json={"path": str(tree["game"]), "grant": True})
    assert r.status_code == 201, r.text
    assert str(tree["game"].resolve()) in client.get("/api/system/import-roots").json()["paths"]
    # thư mục khác ngoài vùng vẫn bị chặn nếu không cấp quyền
    p2 = mk_project(client, "P2")
    assert client.post(f"/api/projects/{p2['id']}/import/folder", json={"path": str(tree["outside"])}).status_code == 403


def test_grant_refuses_drive_root(client, tree):
    p = mk_project(client)
    r = client.post(f"/api/projects/{p['id']}/import/folder", json={"path": "/", "grant": True})
    assert r.status_code == 422
