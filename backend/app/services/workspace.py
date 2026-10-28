"""Workspace của từng dự án: nhập mã nguồn (zip/tệp) an toàn, liệt kê, đọc, dựng ngữ cảnh cho AI.

Bảo vệ: chống zip-slip, bỏ symlink, giới hạn dung lượng/số tệp, không nhập tệp bí mật (.env, khóa riêng),
che các chuỗi giống khóa API trước khi gửi nội dung cho AI.
"""
from __future__ import annotations

import io
import re
import stat
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

from .common import EngineError

MAX_UPLOAD_BYTES = 100 * 1024 * 1024      # tổng dung lượng tải lên mỗi lần
MAX_FILES = 5000
MAX_UNZIPPED_BYTES = 300 * 1024 * 1024
MAX_READ_BYTES = 200 * 1024
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".godot", ".import", "__MACOSX"}
SECRET_NAMES = {".env", "id_rsa", "id_ed25519", "id_dsa", ".npmrc", ".pypirc", "credentials", "secrets.json"}
SECRET_SUFFIXES = (".pem", ".key", ".pfx", ".p12", ".keystore", ".jks")
TEXT_SUFFIXES = {".gd", ".tscn", ".tres", ".godot", ".cfg", ".md", ".txt", ".json", ".py", ".js", ".ts", ".tsx",
                 ".cs", ".shader", ".gdshader", ".toml", ".yml", ".yaml", ".html", ".css", ".csv", ".ini", ".xml",
                 ".gradle", ".java", ".kt", ".swift", ".c", ".cpp", ".h"}

_REDACTIONS = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "[ĐÃ-CHE-KHÓA-RIÊNG]"),
    (re.compile(r"\b(sk-[A-Za-z0-9_\-]{16,}|ghp_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_\-]{30,}|AKIA[0-9A-Z]{16})"), "[ĐÃ-CHE-KHÓA]"),
    (re.compile(r"(?im)^(\s*(?:[\w\-.]+\s+)*[\"']?[\w\-.]*(?:key|token|secret|password|passwd)[\w\-.]*[\"']?\s*[=:]\s*)(\S.*)$"), r"\1[ĐÃ-CHE]"),
]


def redact(text: str) -> str:
    for rx, rep in _REDACTIONS:
        text = rx.sub(rep, text)
    return text


def is_secret_file(name: str) -> bool:
    n = name.lower()
    return n in SECRET_NAMES or n.startswith(".env") or n.endswith(SECRET_SUFFIXES)


def safe_resolve(ws: Path, rel: str) -> Path:
    """Giải đường dẫn tương đối trong workspace; chặn thoát ra ngoài."""
    root = ws.resolve()
    p = (root / rel).resolve()
    if p != root and root not in p.parents:
        raise EngineError(400, "Đường dẫn không hợp lệ.")
    return p


def _clean_member(name: str) -> PurePosixPath | None:
    name = name.replace("\\", "/")
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts or (p.parts and re.match(r"^[A-Za-z]:$", p.parts[0])):
        raise EngineError(400, f"Tệp zip chứa đường dẫn không an toàn: {name}")
    if any(part in SKIP_DIRS for part in p.parts):
        return None
    return p


def _next_import_dir(ws: Path) -> Path:
    base = ws / "imports"
    base.mkdir(parents=True, exist_ok=True)
    n = 1 + max([int(d.name.split("-")[0]) for d in base.iterdir() if d.is_dir() and d.name.split("-")[0].isdigit()] or [0])
    d = base / f"{n}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    d.mkdir()
    return d


def import_uploads(ws: Path, uploads: list[tuple[str, bytes]]) -> dict:
    """uploads: [(tên tệp, nội dung)]. Mỗi lần nhập tạo thư mục imports/<n>-<thời gian>, không ghi đè bản cũ."""
    if not uploads:
        raise EngineError(400, "Chưa chọn tệp nào.")
    if sum(len(b) for _, b in uploads) > MAX_UPLOAD_BYTES:
        raise EngineError(413, f"Quá lớn (tối đa {MAX_UPLOAD_BYTES // 1024 // 1024} MB mỗi lần).")
    dest = _next_import_dir(ws)
    saved, skipped, total = 0, [], 0
    try:
        for fname, data in uploads:
            base = Path(fname.replace("\\", "/")).name
            if fname.lower().endswith(".zip"):
                try:
                    zf = zipfile.ZipFile(io.BytesIO(data))
                except zipfile.BadZipFile:
                    raise EngineError(400, f"'{base}' không phải tệp zip hợp lệ.")
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    rel = _clean_member(info.filename)
                    if rel is None:
                        continue
                    if stat.S_ISLNK(info.external_attr >> 16):
                        skipped.append(f"{rel} (symlink)")
                        continue
                    if is_secret_file(rel.name):
                        skipped.append(f"{rel} (tệp bí mật)")
                        continue
                    saved += 1
                    total += info.file_size
                    if saved > MAX_FILES or total > MAX_UNZIPPED_BYTES:
                        raise EngineError(413, "Zip có quá nhiều tệp hoặc quá lớn sau khi giải nén.")
                    out = safe_resolve(dest, str(rel))
                    out.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(info) as src, open(out, "wb") as dst:
                        written = 0
                        while chunk := src.read(65536):
                            written += len(chunk)
                            if written > info.file_size + 1024:  # khai báo kích thước gian dối
                                raise EngineError(400, "Zip không hợp lệ (kích thước sai).")
                            dst.write(chunk)
            else:
                if is_secret_file(base):
                    skipped.append(f"{base} (tệp bí mật)")
                    continue
                if saved + 1 > MAX_FILES:
                    raise EngineError(413, "Quá nhiều tệp.")
                (dest / base).write_bytes(data)
                saved += 1
    except Exception:
        import shutil
        shutil.rmtree(dest, ignore_errors=True)
        raise
    if saved == 0:
        import shutil
        shutil.rmtree(dest, ignore_errors=True)
        raise EngineError(400, "Không có tệp hợp lệ nào để nhập." + (f" Bỏ qua: {', '.join(skipped[:5])}" if skipped else ""))
    return {"import": dest.name, "files_saved": saved, "skipped": skipped[:50]}


def list_tree(ws: Path, limit: int = 1000) -> dict:
    root = ws.resolve()
    items, truncated = [], False
    if root.is_dir():
        for p in sorted(root.rglob("*")):
            if any(part in SKIP_DIRS for part in p.relative_to(root).parts) or p.is_symlink() or not p.is_file():
                continue
            if len(items) >= limit:
                truncated = True
                break
            items.append({"path": p.relative_to(root).as_posix(), "size": p.stat().st_size})
    return {"files": items, "truncated": truncated,
            "imports": sorted([d.name for d in (root / "imports").iterdir() if d.is_dir()]) if (root / "imports").is_dir() else []}


def read_text(ws: Path, rel: str) -> dict:
    p = safe_resolve(ws, rel)
    if not p.is_file():
        raise EngineError(404, "Không tìm thấy tệp.")
    if p.suffix.lower() not in TEXT_SUFFIXES and p.name.lower() not in {"readme", "license", "makefile"}:
        raise EngineError(415, "Chỉ xem được tệp văn bản/mã nguồn.")
    if is_secret_file(p.name):
        raise EngineError(403, "Không hiển thị tệp bí mật.")
    raw = p.read_bytes()[:MAX_READ_BYTES + 1]
    try:
        text = raw[:MAX_READ_BYTES].decode("utf-8")
    except UnicodeDecodeError:
        raise EngineError(415, "Tệp không phải UTF-8.")
    return {"path": rel, "content": redact(text), "truncated": len(raw) > MAX_READ_BYTES}


_PRIORITY = ("readme", "project.godot", "package.json", "requirements.txt", "pyproject.toml", "export_presets.cfg")


def build_context(ws: Path, budget_chars: int = 20000, per_file: int = 3000) -> str:
    """Tóm tắt workspace cho AI: cây tệp + nội dung các tệp chính. Đã che chuỗi giống khóa API."""
    tree = list_tree(ws, 300)
    files = tree["files"]
    if not files:
        return "(Workspace chưa có tệp nào.)"
    out = ["## Cây tệp (tối đa 300)"] + [f"- {f['path']} ({f['size']} B)" for f in files]
    if tree["truncated"]:
        out.append("- … (còn nữa, đã cắt bớt)")

    def rank(f):
        name = f["path"].rsplit("/", 1)[-1].lower()
        pri = 0 if any(name.startswith(k) for k in _PRIORITY) else 1
        return (pri, f["size"])

    used = sum(len(x) for x in out)
    out.append("\n## Nội dung tệp chính")
    for f in sorted(files, key=rank):
        p = Path(f["path"])
        if p.suffix.lower() not in TEXT_SUFFIXES or is_secret_file(p.name) or f["size"] == 0:
            continue
        try:
            body = redact(safe_resolve(ws, f["path"]).read_text(encoding="utf-8")[:per_file])
        except (UnicodeDecodeError, OSError):
            continue
        chunk = f"\n### {f['path']}\n```\n{body}\n```"
        if used + len(chunk) > budget_chars:
            break
        out.append(chunk)
        used += len(chunk)
    return "\n".join(out)
