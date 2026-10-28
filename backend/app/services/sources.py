"""Nhập dự án có sẵn vào workspace từ GitHub hoặc thư mục trên máy tính.

An toàn:
- GitHub: chỉ nhận https://github.com/<chủ>/<repo>; git chạy bằng danh sách tham số (không qua shell), có `--` trước URL,
  không tự hỏi mật khẩu (GIT_TERMINAL_PROMPT=0), timeout cứng, shallow clone, KHÔNG tải submodule. Repo riêng tư dùng
  thông tin đăng nhập git đã có sẵn trên máy bạn (Git Credential Manager) — hệ thống không lưu token.
- Thư mục máy tính: chỉ trong các "thư mục gốc được phép" do chủ studio khai báo; giải đường dẫn thật (chặn ../ và symlink
  thoát ra ngoài); không bao giờ ghi vào thư mục gốc của bạn — luôn SAO CHÉP vào workspace.
- Cả hai: bỏ .git/node_modules…, symlink, tệp bí mật; giới hạn số tệp/dung lượng.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from sqlalchemy.orm import Session

from . import workspace as wsvc
from .common import EngineError, get_setting, set_setting

GITHUB_RE = re.compile(r"^https://github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/([A-Za-z0-9._-]{1,100}?)(?:\.git)?/?$")
BRANCH_RE = re.compile(r"^(?!-)[A-Za-z0-9._/\-]{1,100}$")
CLONE_TIMEOUT_S = 240
ROOTS_KEY = "import_roots"


# ---------- thư mục gốc được phép ----------
def get_roots(s: Session) -> list[str]:
    try:
        v = json.loads(get_setting(s, ROOTS_KEY) or "[]")
        return [x for x in v if isinstance(x, str)]
    except ValueError:
        return []


def set_roots(s: Session, paths: list[str]) -> list[str]:
    clean: list[str] = []
    for raw in paths:
        raw = raw.strip()
        if not raw:
            continue
        p = Path(raw)
        if not p.is_absolute():
            raise EngineError(422, f"Phải là đường dẫn tuyệt đối: {raw}")
        try:
            rp = p.resolve(strict=True)
        except OSError:
            raise EngineError(422, f"Thư mục không tồn tại: {raw}")
        if not rp.is_dir():
            raise EngineError(422, f"Không phải thư mục: {raw}")
        if rp.parent == rp:
            raise EngineError(422, f"Không cho phép cả ổ đĩa / thư mục gốc hệ thống: {raw}. Hãy chọn thư mục chứa các game của bạn.")
        if str(rp) not in clean:
            clean.append(str(rp))
    if len(clean) > 20:
        raise EngineError(422, "Tối đa 20 thư mục gốc.")
    set_setting(s, ROOTS_KEY, json.dumps(clean))
    return clean


def _within(path: Path, roots: list[str]) -> bool:
    for r in roots:
        rr = Path(r)
        if path == rr or rr in path.parents:
            return True
    return False


def resolve_allowed(s: Session, raw: str) -> Path:
    roots = get_roots(s)
    if not roots:
        raise EngineError(403, "Chưa có thư mục gốc nào được phép. Chủ studio hãy thêm trong Cài đặt → Thư mục dự án trên máy.")
    raw = (raw or "").strip()
    if not raw or "\x00" in raw:
        raise EngineError(422, "Chưa nhập đường dẫn thư mục.")
    try:
        p = Path(raw).resolve(strict=True)
    except OSError:
        raise EngineError(404, "Không tìm thấy thư mục này trên máy.")
    if not _within(p, roots):
        raise EngineError(403, "Thư mục nằm ngoài các thư mục gốc được phép.")
    if not p.is_dir():
        raise EngineError(422, "Đường dẫn không phải thư mục.")
    return p


def browse(s: Session, raw: str) -> dict:
    """Liệt kê thư mục con (chỉ trong vùng được phép) để chọn nhanh trên giao diện."""
    roots = get_roots(s)
    if not raw:
        return {"path": "", "parent": "", "dirs": roots, "roots": roots}
    p = resolve_allowed(s, raw)
    dirs = []
    try:
        for c in sorted(p.iterdir(), key=lambda x: x.name.lower()):
            if c.is_dir() and not c.is_symlink() and c.name not in wsvc.SKIP_DIRS and not c.name.startswith("."):
                dirs.append(str(c))
            if len(dirs) >= 300:
                break
    except OSError as e:
        raise EngineError(403, f"Không đọc được thư mục: {e.strerror or e}")
    parent = str(p.parent) if p not in [Path(r) for r in roots] and _within(p.parent, roots) else ""
    return {"path": str(p), "parent": parent, "dirs": dirs, "roots": roots}


# ---------- sao chép an toàn ----------
def copy_tree(src: Path, ws: Path) -> dict:
    """Sao chép src → ws/imports/<n>-<thời gian>, áp dụng bộ lọc và giới hạn của workspace."""
    src = src.resolve()
    dest = wsvc._next_import_dir(ws)
    saved, total, skipped = 0, 0, []
    try:
        for dirpath, dirnames, filenames in os.walk(src, followlinks=False):
            dp = Path(dirpath)
            keep = []
            for d in dirnames:
                if d in wsvc.SKIP_DIRS:
                    continue
                if (dp / d).is_symlink():
                    skipped.append(f"{(dp / d).relative_to(src).as_posix()} (symlink)")
                    continue
                keep.append(d)
            dirnames[:] = keep
            for fn in filenames:
                f = dp / fn
                rel = f.relative_to(src)
                if f.is_symlink() or not f.is_file():
                    skipped.append(f"{rel.as_posix()} (symlink/đặc biệt)")
                    continue
                if wsvc.is_secret_file(fn):
                    skipped.append(f"{rel.as_posix()} (tệp bí mật)")
                    continue
                size = f.stat().st_size
                saved += 1
                total += size
                if saved > wsvc.MAX_FILES or total > wsvc.MAX_UNZIPPED_BYTES:
                    raise EngineError(413, f"Dự án quá lớn (tối đa {wsvc.MAX_FILES} tệp / {wsvc.MAX_UNZIPPED_BYTES // 1024 // 1024} MB). "
                                           "Hãy chọn thư mục nhỏ hơn hoặc loại bớt tài sản nặng.")
                out = wsvc.safe_resolve(dest, rel.as_posix())
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(f, out)
    except Exception:
        shutil.rmtree(dest, ignore_errors=True)
        raise
    if saved == 0:
        shutil.rmtree(dest, ignore_errors=True)
        raise EngineError(400, "Không có tệp hợp lệ nào để nhập." + (f" Bỏ qua: {', '.join(skipped[:5])}" if skipped else ""))
    return {"import": dest.name, "files_saved": saved, "skipped": skipped[:50]}


def import_folder(s: Session, ws: Path, raw: str) -> dict:
    src = resolve_allowed(s, raw)
    if ws.resolve() == src or ws.resolve() in src.parents or src in ws.resolve().parents:
        raise EngineError(422, "Không thể nhập từ chính workspace của studio.")
    res = copy_tree(src, ws)
    res["source"] = str(src)
    return res


# ---------- GitHub ----------
def parse_github(url: str) -> tuple[str, str]:
    m = GITHUB_RE.match((url or "").strip())
    if not m:
        raise EngineError(422, "Chỉ nhận địa chỉ dạng https://github.com/<chủ>/<tên-repo>.")
    return m.group(1), m.group(2)


def _clone(url: str, branch: str, dest: Path) -> str:
    """Chạy git clone nông vào dest; trả về commit hash. Tách riêng để kiểm thử."""
    git = shutil.which("git")
    if not git:
        raise EngineError(503, "Chưa cài Git trên máy. Cài từ https://git-scm.com rồi thử lại.")
    args = [git, "clone", "--depth", "1", "--no-tags", "--single-branch"]
    if branch:
        args += ["--branch", branch]
    args += ["--", url, str(dest)]
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}
    kw = {"creationflags": 0x08000000} if os.name == "nt" else {}
    try:
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=CLONE_TIMEOUT_S,
                           env=env, stdin=subprocess.DEVNULL, **kw)
    except subprocess.TimeoutExpired:
        raise EngineError(504, "Tải từ GitHub quá lâu (timeout). Thử lại hoặc dùng tệp .zip.")
    if r.returncode != 0:
        msg = (r.stderr or r.stdout).strip().splitlines()[-1:] or ["lỗi không rõ"]
        low = (r.stderr or "").lower()
        if "not found" in low or "authentication" in low or "could not read username" in low or "403" in low:
            raise EngineError(404, "Không tải được repo: sai địa chỉ, hoặc repo riêng tư mà máy này chưa đăng nhập GitHub "
                                   "(đăng nhập git trên máy, hoặc tải .zip rồi upload).")
        raise EngineError(502, f"git clone lỗi: {msg[0][:200]}")
    h = subprocess.run([git, "-C", str(dest), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30)
    return h.stdout.strip()[:40]


def import_github(ws: Path, url: str, branch: str = "") -> dict:
    owner, repo = parse_github(url)
    branch = (branch or "").strip()
    if branch and (not BRANCH_RE.match(branch) or ".." in branch):
        raise EngineError(422, "Tên nhánh không hợp lệ.")
    clean_url = f"https://github.com/{owner}/{repo}.git"
    with tempfile.TemporaryDirectory(prefix="mrk-clone-") as td:
        dest = Path(td) / "repo"
        commit = _clone(clean_url, branch, dest)
        res = copy_tree(dest, ws)
    res.update({"source": f"https://github.com/{owner}/{repo}", "commit": commit})
    return res
