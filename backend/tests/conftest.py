import stat
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

CLAUDE = r'''#!/usr/bin/env bash
D="$FAKE_DIR"; MODE="$(cat "$D/mode_claude" 2>/dev/null || echo ok)"
case "$1" in
  --version) echo "9.9.9 (Fake Claude)"; exit 0;;
  auth) if [ "$MODE" = "notlogged" ]; then echo '{"loggedIn": false}'; else echo '{"loggedIn": true}'; fi; exit 0;;
esac
cat > /dev/null; echo x >> "$D/calls_claude"
case "$MODE" in
  overloaded) echo "503 overloaded" >&2; exit 1;;
  notlogged) echo "Not logged in · Please run /login" >&2; exit 1;;
  fail) echo "boom" >&2; exit 2;;
  sleep) sleep 30;;
esac
printf '{"type":"result","is_error":false,"result":"CLAUDE-OUT","usage":{"input_tokens":1000,"output_tokens":500}}'
'''
CODEX = r'''#!/usr/bin/env bash
D="$FAKE_DIR"; MODE="$(cat "$D/mode_codex" 2>/dev/null || echo ok)"
case "$1" in
  --version) echo "codex-cli 9.9.9"; exit 0;;
  login) if [ "$MODE" = "notlogged" ]; then echo "Not logged in"; else echo "Logged in using ChatGPT"; fi; exit 0;;
esac
OUT=""; PREV=""; for a in "$@"; do [ "$PREV" = "-o" ] && OUT="$a"; PREV="$a"; done
cat > /dev/null; echo x >> "$D/calls_codex"
case "$MODE" in
  overloaded) echo "503 overloaded" >&2; exit 1;;
  notlogged) echo "Not logged in" >&2; exit 1;;
  fail) echo "boom" >&2; exit 2;;
esac
echo "CODEX-OUT" > "$OUT"
'''
SHORT = {"claude_cli": "claude", "codex_cli": "codex"}


class _Calls:
    def __init__(self, d): self.d = d

    def __getitem__(self, name):
        f = self.d / f"calls_{SHORT[name]}"
        return len(f.read_text().splitlines()) if f.exists() else 0


class _Mode:
    def __init__(self, d): self.d = d

    def __setitem__(self, name, mode): (self.d / f"mode_{SHORT[name]}").write_text(mode)


class FakeCLIs:
    """Claude Code / Codex giả: đếm số lần gọi, đổi chế độ lỗi bằng fake.mode[...]."""

    def __init__(self, tmp_path, monkeypatch):
        self.dir = tmp_path / "fakecli"
        self.dir.mkdir()
        for name, body in (("claude", CLAUDE), ("codex", CODEX)):
            f = self.dir / name
            f.write_text(body)
            f.chmod(f.stat().st_mode | stat.S_IEXEC)
        self.calls, self.mode, self.mp = _Calls(self.dir), _Mode(self.dir), monkeypatch
        monkeypatch.setenv("FAKE_DIR", str(self.dir))

    def present(self, yes: bool):
        for var, name in (("CLAUDE_CLI_PATH", "claude"), ("CODEX_CLI_PATH", "codex")):
            self.mp.setenv(var, str(self.dir / name) if yes else str(self.dir / "missing"))


@pytest.fixture()
def fake(tmp_path, monkeypatch):
    return FakeCLIs(tmp_path, monkeypatch)


def make_client(tmp_path, fake=None, *, cli=True, enable=True):
    """cli=True: có claude/codex giả trên máy; enable=True: bật hai provider CLI (mặc định chúng tắt)."""
    if fake is not None:
        fake.present(cli)
    s = Settings(database_url=f"sqlite:///{tmp_path/'t.db'}", secret_key="test-secret", admin_password="Passw0rd!x",
                 data_dir=tmp_path / "data", games_dir=tmp_path / "games", frontend_dist=tmp_path / "nodist")
    app = create_app(s, retry_delay=0)
    c = TestClient(app)
    tok = c.post("/api/auth/login", json={"username": "owner", "password": "Passw0rd!x"}).json()["token"]
    c.headers["Authorization"] = f"Bearer {tok}"
    if cli and enable:
        for n in ("claude_cli", "codex_cli"):
            assert c.patch(f"/api/providers/{n}", json={"enabled": True}).status_code == 200
    return c


@pytest.fixture()
def client(tmp_path, fake):
    return make_client(tmp_path, fake)


@pytest.fixture()
def offline(tmp_path, fake):
    """Không có chương trình AI nào trên máy → chế độ nội bộ."""
    return make_client(tmp_path, fake, cli=False)


def mk_project(c, name="Game A"):
    r = c.post("/api/projects", json={"name": name, "genre": "puzzle", "platform": "mobile"})
    assert r.status_code == 201, r.text
    return r.json()


def mk_task(c, pid, dept="game_dev", **kw):
    body = {"project_id": pid, "department_key": dept, "title": "T", "objective": "Làm X", **kw}
    r = c.post("/api/tasks", json=body)
    assert r.status_code == 201, r.text
    return r.json()
