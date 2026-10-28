"""Provider dùng công cụ dòng lệnh đã cài và đăng nhập sẵn trên máy (gói thuê bao, không cần API key).

- claude_cli: Claude Code (`claude -p`), đăng nhập bằng tài khoản Claude.
- codex_cli : OpenAI Codex CLI (`codex exec`), đăng nhập bằng tài khoản ChatGPT.

An toàn:
- Chạy bằng danh sách tham số (không qua shell); prompt và system prompt đi qua stdin, KHÔNG nằm trong tham số.
- Thư mục làm việc là thư mục rỗng `data/cli-scratch`; công cụ của CLI bị tắt/giới hạn (Claude: --tools= ;
  Codex: sandbox read-only) nên mô hình chỉ trả văn bản, không sửa tệp.
- Xóa ANTHROPIC_API_KEY / OPENAI_API_KEY / CODEX_API_KEY khỏi môi trường tiến trình con để CLI dùng đăng nhập
  thuê bao thay vì âm thầm tính tiền theo API.
- Timeout cứng, diệt cả cây tiến trình; giới hạn 2 tiến trình chạy đồng thời.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from .base import Provider, ProviderError, ProviderResult

STRIP_ENV = {"ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL",
             "ANTHROPIC_BASE_URL"}
MODEL_RE = re.compile(r"^[A-Za-z0-9_.:\-\[\]]{1,80}$")
_SLOTS = threading.BoundedSemaphore(2)
WIN = sys.platform == "win32"


def _kill_tree(p: subprocess.Popen) -> None:
    try:
        if WIN:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True, timeout=10)
        else:
            import signal
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    except Exception:  # noqa: BLE001
        p.kill()


def run_cli(args: list[str], stdin: str, timeout: float, cwd: Path) -> tuple[int, str, str]:
    env = {k: v for k, v in os.environ.items() if k not in STRIP_ENV}
    kw = {"creationflags": 0x08000000} if WIN else {"start_new_session": True}  # CREATE_NO_WINDOW
    cwd.mkdir(parents=True, exist_ok=True)
    p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(cwd),
                         env=env, text=True, encoding="utf-8", errors="replace", **kw)
    try:
        out, err = p.communicate(stdin, timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(p)
        try:
            p.communicate(timeout=5)
        except Exception:  # noqa: BLE001
            pass
        raise ProviderError("Hết thời gian chờ (timeout).", retryable=True)
    return p.returncode, out or "", err or ""


class _CliProvider(Provider):
    external = True
    subscription = True
    binary = ""
    env_var = ""

    def __init__(self, scratch: Path, path_override: str = ""):
        self.scratch = scratch
        self.exe = path_override or os.environ.get(self.env_var, "") or shutil.which(self.binary) or ""

    def configured(self) -> bool:
        return bool(self.exe) and Path(self.exe).exists()

    def masked_key(self) -> str:  # hiển thị đường dẫn chương trình thay cho khóa
        return self.exe

    def _simple(self, args: list[str], timeout: float) -> tuple[int, str]:
        try:
            rc, out, err = run_cli([self.exe, *args], "", timeout, self.scratch)
        except ProviderError as e:
            return 1, str(e)
        except OSError as e:
            return 1, f"Không chạy được: {e}"
        return rc, (out or err).strip()

    def _model_args(self, model: str) -> list[str]:
        if not model:
            return []
        if not MODEL_RE.match(model):
            raise ProviderError("Tên model không hợp lệ.")
        return ["--model" if self.binary == "claude" else "-m", model]

    @staticmethod
    def _full_prompt(system: str, prompt: str) -> str:
        return f"[HƯỚNG DẪN HỆ THỐNG]\n{system}\n\n[NHIỆM VỤ]\n{prompt}" if system else prompt

    def _fail(self, rc: int, out: str, err: str) -> ProviderError:
        txt = (err or out).strip()[:300]
        low = txt.lower()
        if any(k in low for k in ("not logged in", "login", "unauthorized", "authenticate", "/login")):
            return ProviderError(f"{self.binary}: chưa đăng nhập. Mở cửa sổ lệnh và đăng nhập lại. ({txt})")
        retry = any(k in low for k in ("rate limit", "usage limit", "overloaded", "429", "502", "503", "504"))
        return ProviderError(f"{self.binary} thoát với mã {rc}: {txt}", retryable=retry and "usage limit" not in low)

    def complete(self, *, system, prompt, model, max_tokens, timeout) -> ProviderResult:
        if not self.configured():
            raise ProviderError(f"Không tìm thấy chương trình '{self.binary}'.")
        with _SLOTS:
            return self._complete(system, prompt, model, timeout)

    def _complete(self, system: str, prompt: str, model: str, timeout: float) -> ProviderResult:
        raise NotImplementedError


class ClaudeCli(_CliProvider):
    name = "claude_cli"
    binary = "claude"
    env_var = "CLAUDE_CLI_PATH"

    def check(self, timeout: float = 20.0) -> tuple[bool, str]:
        if not self.configured():
            return False, "Chưa tìm thấy 'claude' trên máy (cài Claude Code, hoặc đặt CLAUDE_CLI_PATH trong .env)."
        rc, ver = self._simple(["--version"], timeout)
        if rc != 0:
            return False, f"Chạy 'claude --version' lỗi: {ver[:200]}"
        rc, st = self._simple(["auth", "status"], timeout)
        try:
            logged = bool(json.loads(st).get("loggedIn"))
        except Exception:  # noqa: BLE001
            logged = rc == 0 and "not logged in" not in st.lower()
        if not logged:
            return False, (f"{ver}: chưa đăng nhập. Chạy 'claude' trong cửa sổ lệnh và đăng nhập. "
                           f"[claude auth status trả về: {' '.join(st.split())[:200] or '(trống)'}]")
        return True, f"{ver}: đã đăng nhập (gói thuê bao)."

    def _complete(self, system, prompt, model, timeout) -> ProviderResult:
        args = [self.exe, "-p", "--output-format", "json", "--tools=", "--no-session-persistence",
                "--permission-mode", "dontAsk", *self._model_args(model)]
        try:
            rc, out, err = run_cli(args, self._full_prompt(system, prompt), timeout, self.scratch)
        except OSError as e:
            raise ProviderError(f"Không chạy được claude: {e}")
        try:
            d = json.loads(out)
        except Exception:  # noqa: BLE001
            d = None
        if isinstance(d, dict):
            if d.get("is_error") or rc != 0:
                raise self._fail(rc, str(d.get("result", "")), err)
            u = d.get("usage") or {}
            return ProviderResult(str(d.get("result", "")), u.get("input_tokens"), u.get("output_tokens"))
        if rc != 0:
            raise self._fail(rc, out, err)
        return ProviderResult(out.strip())


class CodexCli(_CliProvider):
    name = "codex_cli"
    binary = "codex"
    env_var = "CODEX_CLI_PATH"

    def check(self, timeout: float = 20.0) -> tuple[bool, str]:
        if not self.configured():
            return False, "Chưa tìm thấy 'codex' trên máy (cài: npm i -g @openai/codex, hoặc đặt CODEX_CLI_PATH trong .env)."
        rc, ver = self._simple(["--version"], timeout)
        if rc != 0:
            return False, f"Chạy 'codex --version' lỗi: {ver[:200]}"
        rc, st = self._simple(["login", "status"], timeout)
        low = st.lower()
        if rc != 0 or "not logged in" in low or "logged in" not in low:
            return False, f"{ver}: chưa đăng nhập. Chạy 'codex login' (chọn Sign in with ChatGPT). ({st[:120]})"
        return True, f"{ver}: {st.splitlines()[0][:100]}"

    def _complete(self, system, prompt, model, timeout) -> ProviderResult:
        with tempfile.TemporaryDirectory(prefix="mrk-codex-") as td:
            outfile = Path(td) / "last.txt"
            args = [self.exe, "exec", "--sandbox", "read-only", "--skip-git-repo-check", "--ephemeral",
                    "--color", "never", "-o", str(outfile), *self._model_args(model), "-"]
            try:
                rc, out, err = run_cli(args, self._full_prompt(system, prompt), timeout, self.scratch)
            except OSError as e:
                raise ProviderError(f"Không chạy được codex: {e}")
            if rc != 0:
                raise self._fail(rc, out, err)
            text = outfile.read_text(encoding="utf-8").strip() if outfile.exists() else out.strip()
            if not text:
                raise ProviderError("codex không trả về nội dung.")
            return ProviderResult(text)
