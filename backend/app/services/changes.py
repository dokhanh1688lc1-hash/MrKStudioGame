"""Đề xuất sửa file → duyệt → ghi vào thư mục dự án trên máy (có sao lưu và hoàn tác).

Nguyên tắc an toàn:
- AI không bao giờ ghi trực tiếp. AI chỉ đề xuất; chủ studio xem diff rồi bấm Áp dụng.
- Chỉ ghi trong thư mục dự án đã liên kết (nằm trong "thư mục gốc được phép"), và chỉ khi chủ studio bật quyền ghi cho dự án.
- Chỉ tệp văn bản/mã nguồn có đuôi trong danh sách cho phép (không .bat/.exe/.ps1/.sh…); không tệp bí mật; không symlink; không xóa tệp.
- Trước khi ghi: kiểm tra tệp chưa bị đổi kể từ lúc đề xuất (sha256); sao lưu bản gốc; ghi nguyên tử; có Hoàn tác.
"""
from __future__ import annotations

import difflib
import hashlib
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .common import EngineError
from . import workspace as wsvc

MAX_FILE_BYTES = 1024 * 1024
MAX_FILES_PER_PROPOSAL = 50
WRITABLE_SUFFIXES = wsvc.TEXT_SUFFIXES  # văn bản/mã nguồn thuần; không có tệp thực thi/script hệ điều hành

_IMPORT_PREFIX = re.compile(r"^imports/\d+-\d{8}-\d{6}/")
_FILE_BLOCK = re.compile(r"<<<(NEW FILE|FILE)[ \t]+(.+?)[ \t]*>>>[ \t]*\r?\n(.*?)\r?\n?<<<END FILE>>>", re.S)
_EDIT = re.compile(r"<<<SEARCH>>>[ \t]*\r?\n(.*?)\r?\n<<<REPLACE>>>[ \t]*\r?\n(.*?)\r?\n?<<<END>>>", re.S)

FORMAT_HELP = """\
ĐỊNH DẠNG ĐỀ XUẤT SỬA TỆP (chỉ dùng khi bạn đề xuất thay đổi mã; viết đúng nguyên văn các thẻ sau):

Sửa tệp có sẵn — mỗi thay đổi là một cặp SEARCH/REPLACE. Đoạn SEARCH phải là văn bản NGUYÊN VĂN có trong tệp
(đủ dài để duy nhất, giữ nguyên thụt dòng) và chỉ xuất hiện đúng 1 lần:
<<<FILE đường/dẫn/tương_đối.gd>>>
<<<SEARCH>>>
dòng cũ cần thay
<<<REPLACE>>>
dòng mới
<<<END>>>
<<<END FILE>>>

Tạo tệp mới:
<<<NEW FILE đường/dẫn/mới.gd>>>
toàn bộ nội dung tệp
<<<END FILE>>>

Đường dẫn tương đối so với thư mục gốc của dự án (không có tiền tố imports/…). Không xóa tệp. Không đề xuất sửa tệp .env, khóa, hoặc tệp thực thi/script hệ điều hành.
Phần giải thích viết ngoài các khối trên."""


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def normalize_rel(raw: str) -> str:
    rel = (raw or "").strip().strip("`'\"").replace("\\", "/")
    rel = _IMPORT_PREFIX.sub("", rel)
    if not rel or rel.startswith("/") or re.match(r"^[A-Za-z]:", rel) or any(p in ("..", "") for p in rel.split("/")):
        raise EngineError(422, f"Đường dẫn không hợp lệ: {raw!r}")
    if any(p in wsvc.SKIP_DIRS for p in rel.split("/")):
        raise EngineError(422, f"Không được sửa trong thư mục hệ thống: {rel}")
    name = rel.rsplit("/", 1)[-1]
    if wsvc.is_secret_file(name):
        raise EngineError(422, f"Không được sửa tệp bí mật: {rel}")
    if Path(name).suffix.lower() not in WRITABLE_SUFFIXES:
        raise EngineError(422, f"Loại tệp không được phép sửa: {rel} (chỉ văn bản/mã nguồn thông thường).")
    return rel


def target_path(root: Path, rel: str) -> Path:
    """Đường dẫn thật trong thư mục dự án; chặn thoát ra ngoài và symlink."""
    root = root.resolve()
    t = root.joinpath(*rel.split("/"))
    cur = root
    for part in rel.split("/"):  # không đi qua symlink ở bất kỳ cấp nào
        cur = cur / part
        if cur.is_symlink():
            raise EngineError(422, f"Không cho phép symlink: {rel}")
    rt = t.resolve()
    if root not in rt.parents:
        raise EngineError(422, f"Đường dẫn nằm ngoài thư mục dự án: {rel}")
    return t


def read_current(root: Path, rel: str) -> bytes | None:
    t = target_path(root, rel)
    if not t.exists():
        return None
    if not t.is_file():
        raise EngineError(422, f"Không phải tệp: {rel}")
    if t.stat().st_size > MAX_FILE_BYTES:
        raise EngineError(413, f"Tệp quá lớn để sửa qua hệ thống (> {MAX_FILE_BYTES // 1024} KB): {rel}")
    return t.read_bytes()


def _decode(b: bytes, rel: str) -> str:
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        raise EngineError(415, f"Tệp không phải UTF-8: {rel}")


def _match_crlf(original: str | None, new: str) -> str:
    """Giữ kiểu xuống dòng của tệp gốc (Windows thường dùng CRLF)."""
    if original is not None and "\r\n" in original and "\r\n" not in new:
        return new.replace("\n", "\r\n")
    return new


@dataclass
class Proposed:
    rel: str
    new_content: str
    base_sha: str      # "" = tệp mới
    note: str = ""


def parse_ai_output(text: str, root: Path) -> tuple[list[Proposed], list[str]]:
    """Trích các khối sửa tệp trong kết quả của AI. Trả về (đề xuất hợp lệ, danh sách lỗi theo tệp)."""
    out: list[Proposed] = []
    errors: list[str] = []
    seen: set[str] = set()
    for m in _FILE_BLOCK.finditer(text or ""):
        kind, raw_path, body = m.group(1), m.group(2), m.group(3)
        try:
            rel = normalize_rel(raw_path)
            if rel in seen:
                raise EngineError(422, f"{rel}: xuất hiện nhiều khối cho cùng một tệp (gộp lại thành một).")
            cur = read_current(root, rel)
            if kind == "NEW FILE":
                if cur is not None:
                    raise EngineError(409, f"{rel}: tệp đã tồn tại (dùng khối FILE với SEARCH/REPLACE).")
                new, base = body, ""
            else:
                if cur is None:
                    raise EngineError(404, f"{rel}: không tìm thấy tệp trong thư mục dự án.")
                orig = _decode(cur, rel)
                norm = orig.replace("\r\n", "\n")
                edits = _EDIT.findall(body)
                if not edits:
                    raise EngineError(422, f"{rel}: khối FILE không có cặp SEARCH/REPLACE hợp lệ.")
                for i, (old, rep) in enumerate(edits, 1):
                    n = norm.count(old)
                    if n == 0:
                        raise EngineError(422, f"{rel}: đoạn SEARCH #{i} không khớp nguyên văn với tệp hiện tại.")
                    if n > 1:
                        raise EngineError(422, f"{rel}: đoạn SEARCH #{i} xuất hiện {n} lần (không duy nhất).")
                    norm = norm.replace(old, rep, 1)
                new, base = _match_crlf(orig, norm), sha(cur)
            if len(new.encode("utf-8")) > MAX_FILE_BYTES:
                raise EngineError(413, f"{rel}: nội dung mới quá lớn.")
            seen.add(rel)
            out.append(Proposed(rel, new, base))
        except EngineError as e:
            errors.append(e.message)
        if len(out) + len(errors) >= MAX_FILES_PER_PROPOSAL:
            errors.append(f"Chỉ xử lý tối đa {MAX_FILES_PER_PROPOSAL} tệp mỗi lần.")
            break
    return out, errors


def propose_manual(root: Path, rel: str, content: str) -> Proposed:
    rel = normalize_rel(rel)
    cur = read_current(root, rel)
    if len(content.encode("utf-8")) > MAX_FILE_BYTES:
        raise EngineError(413, "Nội dung quá lớn.")
    orig = _decode(cur, rel) if cur is not None else None
    new = _match_crlf(orig, content.replace("\r\n", "\n"))
    if cur is not None and new == orig:
        raise EngineError(422, "Nội dung không thay đổi so với tệp hiện tại.")
    return Proposed(rel, new, sha(cur) if cur is not None else "")


def make_diff(rel: str, old: str | None, new: str, max_lines: int = 400) -> str:
    a = (old or "").replace("\r\n", "\n").splitlines(keepends=True)
    b = new.replace("\r\n", "\n").splitlines(keepends=True)
    d = list(difflib.unified_diff(a, b, fromfile=f"a/{rel}" if old is not None else "/dev/null", tofile=f"b/{rel}", n=3))
    if len(d) > max_lines:
        d = d[:max_lines] + [f"… (đã cắt, còn {len(d) - max_lines} dòng diff)\n"]
    return "".join(d)


def current_text(root: Path, rel: str) -> str | None:
    cur = read_current(root, rel)
    return None if cur is None else cur.decode("utf-8", errors="replace")


def _atomic_write(t: Path, data: bytes) -> None:
    t.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=t.parent, prefix=".mrk-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        if t.exists():
            shutil.copymode(t, tmp)
        os.replace(tmp, t)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def apply_change(root: Path, rel: str, new_content: str, base_sha: str, backup_dir: Path) -> dict:
    """Ghi tệp. Trả về {'backup': đường dẫn bản sao lưu hoặc '', 'applied_sha': ...}."""
    rel = normalize_rel(rel)
    t = target_path(root, rel)
    cur = read_current(root, rel)
    if (sha(cur) if cur is not None else "") != base_sha:
        raise EngineError(409, f"Tệp đã thay đổi trên máy kể từ lúc đề xuất ({rel}). Hãy tạo đề xuất mới từ bản hiện tại.")
    backup = ""
    if cur is not None:
        bp = backup_dir / rel
        bp.parent.mkdir(parents=True, exist_ok=True)
        bp.write_bytes(cur)
        backup = str(bp)
    data = new_content.encode("utf-8")
    _atomic_write(t, data)
    return {"backup": backup, "applied_sha": sha(data)}


def revert_change(root: Path, rel: str, applied_sha: str, backup: str) -> None:
    rel = normalize_rel(rel)
    t = target_path(root, rel)
    cur = t.read_bytes() if t.is_file() else None
    if cur is None or sha(cur) != applied_sha:
        raise EngineError(409, f"Tệp đã bị sửa tiếp sau khi áp dụng ({rel}); không thể hoàn tác an toàn.")
    if backup:
        bp = Path(backup)
        if not bp.is_file():
            raise EngineError(410, "Bản sao lưu không còn tồn tại.")
        _atomic_write(t, bp.read_bytes())
    else:
        t.unlink()  # tệp do hệ thống tạo mới
