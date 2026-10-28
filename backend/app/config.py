"""Cấu hình ứng dụng. Khóa API chỉ đọc từ biến môi trường, không bao giờ lưu vào DB."""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_dotenv(path: Path) -> None:
    """Trình đọc .env tối giản (không ghi đè biến môi trường đã có)."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


@dataclass
class Settings:
    database_url: str = "sqlite:///./data/mrk_studio.db"
    secret_key: str = ""
    admin_username: str = "owner"
    admin_password: str = ""
    token_ttl_hours: int = 12
    data_dir: Path = field(default_factory=lambda: ROOT / "data")
    frontend_dist: Path = field(default_factory=lambda: ROOT / "frontend" / "dist")
    games_dir: Path = field(default_factory=lambda: ROOT / "games")

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(ROOT / ".env")
        e = os.environ
        return cls(
            database_url=_abs_sqlite(e.get("DATABASE_URL", cls.database_url)),
            secret_key=e.get("SECRET_KEY", ""),
            admin_username=e.get("ADMIN_USERNAME", "owner"),
            admin_password=e.get("ADMIN_PASSWORD", ""),
            token_ttl_hours=int(e.get("TOKEN_TTL_HOURS", "12")),
        )

    def ensure_secret(self) -> str:
        """Trả về secret ký token; nếu chưa cấu hình thì sinh và lưu vào data/secret.key."""
        if self.secret_key and not self.secret_key.startswith("doi-thanh"):
            return self.secret_key
        self.data_dir.mkdir(parents=True, exist_ok=True)
        f = self.data_dir / "secret.key"
        if f.is_file():
            self.secret_key = f.read_text().strip()
        else:
            self.secret_key = secrets.token_urlsafe(48)
            f.write_text(self.secret_key)
        return self.secret_key


def _abs_sqlite(url: str) -> str:
    """Đường dẫn SQLite tương đối được tính từ thư mục gốc dự án, không phụ thuộc nơi chạy."""
    pre = "sqlite:///"
    if url.startswith(pre) and not url.startswith("sqlite:////") and ":memory:" not in url:
        rel = url[len(pre):]
        if not (len(rel) > 1 and rel[1] == ":"):  # ổ đĩa Windows, vd C:\...
            path = (ROOT / rel).resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            return pre + path.as_posix()
    return url

