from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings
from .db import Base, make_engine, make_session_factory
from .providers.registry import ProviderRegistry
from .routers import auth_users, ops, projects, tasks
from .services.orchestrator import Orchestrator
from .services.seed import recover_interrupted, seed_all

log = logging.getLogger("mrk")


def create_app(settings: Settings | None = None, transports: dict | None = None,
               retry_delay: float = 1.0) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.games_dir.mkdir(parents=True, exist_ok=True)
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)  # Phase 1: tạo bảng trực tiếp; Alembic: xem docs/DEVELOPMENT.md
    sf = make_session_factory(engine)

    app = FastAPI(title="MrK Studio Game", version="0.1.0")
    app.state.settings = settings
    app.state.secret = settings.ensure_secret()
    app.state.sf = sf
    app.state.registry = ProviderRegistry(settings, transports)
    app.state.orch = Orchestrator(sf, app.state.registry, retry_delay=retry_delay)

    with sf() as s:
        pwd = seed_all(s, settings)
        n = recover_interrupted(s)
    if pwd:
        msg = f"Tài khoản chủ studio: '{settings.admin_username}' / mật khẩu (chỉ hiện một lần): {pwd}"
        print("=" * 70 + f"\n{msg}\n" + "=" * 70)
    if n:
        log.warning("Đã đánh dấu %d nhiệm vụ bị gián đoạn là Failed", n)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    for r in (auth_users.router, projects.router, tasks.router, ops.router):
        app.include_router(r)

    dist = settings.frontend_dist
    if (dist / "index.html").is_file():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            f = (dist / path).resolve()
            if path and f.is_file() and dist.resolve() in f.parents:
                return FileResponse(f)
            return FileResponse(dist / "index.html")
    return app


def app_factory() -> FastAPI:  # uvicorn --factory app.main:app_factory
    return create_app()
