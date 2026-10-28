import json
import os
import stat
import time

import pytest

from .conftest import make_client, mk_project, mk_task

FAKE_CLAUDE = r'''#!/usr/bin/env bash
LOG="$FAKE_LOG"
case "$1" in
  --version) echo "9.9.9 (Fake Claude)"; exit 0;;
  auth) if [ "$FAKE_MODE" = "notlogged" ]; then echo '{"loggedIn": false}'; else echo '{"loggedIn": true}'; fi; exit 0;;
esac
INPUT="$(cat)"
{ echo "ARGS: $*"; echo "CWD: $PWD"; echo "ANTH_KEY: ${ANTHROPIC_API_KEY:-<unset>}"; echo "OPENAI_KEY: ${OPENAI_API_KEY:-<unset>}"; echo "STDIN: $INPUT"; } >> "$LOG"
case "$FAKE_MODE" in
  sleep) sleep 30;;
  notlogged) echo "Not logged in · Please run /login" >&2; exit 1;;
  fail) echo "boom" >&2; exit 2;;
esac
printf '{"type":"result","is_error":false,"result":"CLAUDE-FAKE-OUT","usage":{"input_tokens":11,"output_tokens":22}}'
'''
FAKE_CODEX = r'''#!/usr/bin/env bash
LOG="$FAKE_LOG"
case "$1" in
  --version) echo "codex-cli 9.9.9"; exit 0;;
  login) if [ "$FAKE_MODE" = "notlogged" ]; then echo "Not logged in"; else echo "Logged in using ChatGPT"; fi; exit 0;;
esac
OUT=""; PREV=""
for a in "$@"; do [ "$PREV" = "-o" ] && OUT="$a"; PREV="$a"; done
INPUT="$(cat)"
{ echo "ARGS: $*"; echo "OPENAI_KEY: ${OPENAI_API_KEY:-<unset>}"; echo "STDIN: $INPUT"; } >> "$LOG"
[ "$FAKE_MODE" = "fail" ] && { echo "codex broke" >&2; exit 3; }
echo "CODEX-FAKE-OUT" > "$OUT"
'''


@pytest.fixture()
def clis(tmp_path, monkeypatch):
    for name, body in (("claude", FAKE_CLAUDE), ("codex", FAKE_CODEX)):
        f = tmp_path / name
        f.write_text(body)
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "cli.log"
    monkeypatch.setenv("CLAUDE_CLI_PATH", str(tmp_path / "claude"))
    monkeypatch.setenv("CODEX_CLI_PATH", str(tmp_path / "codex"))
    monkeypatch.setenv("FAKE_LOG", str(log))
    monkeypatch.setenv("FAKE_MODE", "ok")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-SHOULD-NOT-LEAK")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-SHOULD-NOT-LEAK")
    return log


def enable(c, *names):
    for n in names:
        assert c.patch(f"/api/providers/{n}", json={"enabled": True}).status_code == 200


def test_cli_providers_disabled_by_default_and_listed(tmp_path, clis):
    c = make_client(tmp_path, enable=False)
    ps = {p["name"]: p for p in c.get("/api/providers").json()}
    assert ps["claude_cli"]["kind"] == "cli" and ps["claude_cli"]["configured"] and not ps["claude_cli"]["enabled"]
    r = c.get("/api/routing/preview", params={"department": "game_dev"}).json()
    assert r["chain"][0]["provider"] == "internal"  # chưa bật → không dùng


def test_check_reports_login_state(tmp_path, clis, monkeypatch):
    c = make_client(tmp_path, enable=False)
    r = c.post("/api/providers/claude_cli/check").json()
    assert r["last_check_status"] == "ok" and "đã đăng nhập" in r["last_check_message"]
    assert c.post("/api/providers/codex_cli/check").json()["last_check_status"] == "ok"
    monkeypatch.setenv("FAKE_MODE", "notlogged")
    for n in ("claude_cli", "codex_cli"):
        r = c.post(f"/api/providers/{n}/check").json()
        assert r["last_check_status"] == "failed" and "chưa đăng nhập" in r["last_check_message"]


def test_check_when_program_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CLI_PATH", str(tmp_path / "nope"))
    monkeypatch.setenv("PATH", str(tmp_path))
    c = make_client(tmp_path, enable=False)
    r = c.post("/api/providers/claude_cli/check").json()
    assert r["last_check_status"] == "failed" and "Chưa tìm thấy" in r["last_check_message"]
    assert not {x["name"]: x for x in c.get("/api/providers").json()}["claude_cli"]["configured"]


def test_run_via_claude_cli_safely(tmp_path, clis):
    c = make_client(tmp_path, enable=False)
    enable(c, "claude_cli")
    p = mk_project(c)
    t = mk_task(c, p["id"], "game_dev", objective="NỘI-DUNG-BÍ-MẬT-123; rm -rf /")
    r = c.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()
    assert r["status"] == "Completed" and r["result"] == "CLAUDE-FAKE-OUT" and r["result_source"] == "claude_cli"
    assert r["actual_cost"] == 0.0
    a = r["attempts"][0]
    assert a["input_tokens"] == 11 and a["output_tokens"] == 22
    log = clis.read_text()
    args = next(l for l in log.splitlines() if l.startswith("ARGS:"))
    assert "-p" in args and "--tools=" in args and "dontAsk" in args
    assert "NỘI-DUNG-BÍ-MẬT" not in args  # prompt không nằm trong tham số dòng lệnh
    assert "NỘI-DUNG-BÍ-MẬT-123; rm -rf /" in log  # mà đi qua stdin
    assert "ANTH_KEY: <unset>" in log and "OPENAI_KEY: <unset>" in log  # khóa API không rò sang CLI
    assert "cli-scratch" in log  # chạy trong thư mục rỗng
    assert "Hướng dẫn" in log.upper().replace("Ư", "ƯƯ") or "HƯỚNG DẪN HỆ THỐNG" in log


def test_run_via_codex_cli(tmp_path, clis):
    c = make_client(tmp_path, enable=False)
    enable(c, "codex_cli")
    p = mk_project(c)
    t = mk_task(c, p["id"], "market_research")
    r = c.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()
    assert r["status"] == "Completed" and r["result"] == "CODEX-FAKE-OUT" and r["result_source"] == "codex_cli"
    log = clis.read_text()
    assert "--sandbox read-only" in log and "OPENAI_KEY: <unset>" in log


def test_cli_not_logged_in_fails_clearly_without_retry(tmp_path, clis, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "notlogged")
    c = make_client(tmp_path, enable=False)
    enable(c, "claude_cli")
    p = mk_project(c)
    t = mk_task(c, p["id"], "game_dev", max_retries=3)
    r = c.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()
    assert r["status"] == "Failed" and "chưa đăng nhập" in r["error"] and len(r["attempts"]) == 1


def test_sensitive_requires_permission_for_cli(tmp_path, clis):
    c = make_client(tmp_path, enable=False)
    enable(c, "claude_cli")
    r = c.get("/api/routing/preview", params={"department": "game_dev", "sensitive": True}).json()
    assert r["chain"][0]["provider"] == "internal"
    c.patch("/api/providers/claude_cli", json={"allow_sensitive": True})
    r = c.get("/api/routing/preview", params={"department": "game_dev", "sensitive": True}).json()
    assert r["chain"][0]["provider"] == "claude_cli"


def test_model_name_is_validated_not_passed_to_shell(tmp_path, clis):
    c = make_client(tmp_path, enable=False)
    enable(c, "claude_cli")
    p = mk_project(c)
    t = mk_task(c, p["id"], "game_dev", provider="claude_cli", model="x; touch /tmp/pwned")
    r = c.post(f"/api/tasks/{t['id']}/run", params={"wait": True}).json()
    assert r["status"] == "Failed" and "không hợp lệ" in r["error"]
    assert not os.path.exists("/tmp/pwned")


def test_timeout_kills_the_process_tree(tmp_path, clis, monkeypatch):
    from app.providers.base import ProviderError
    from app.providers.cli_providers import ClaudeCli
    monkeypatch.setenv("FAKE_MODE", "sleep")
    prov = ClaudeCli(tmp_path / "scratch")
    t0 = time.time()
    with pytest.raises(ProviderError) as e:
        prov.complete(system="", prompt="hi", model="", max_tokens=10, timeout=1)
    assert e.value.retryable and time.time() - t0 < 10
    time.sleep(0.5)
    assert os.system("pgrep -f '[s]leep 30' > /dev/null") != 0  # không còn tiến trình sleep mồ côi
