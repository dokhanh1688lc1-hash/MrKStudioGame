import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


class FakeAI:
    """Giả lập máy chủ OpenAI/Anthropic để test mà không gọi mạng thật."""

    def __init__(self):
        self.calls = {"openai": 0, "anthropic": 0}
        self.mode = {"openai": "ok", "anthropic": "ok"}

    def transport(self, name):
        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/v1/models":
                return httpx.Response(200 if self.mode[name] != "unauth" else 401, json={"data": []})
            self.calls[name] += 1
            m = self.mode[name]
            if m == "500":
                return httpx.Response(500, json={"error": {"message": "boom"}})
            if m == "401":
                return httpx.Response(401, json={"error": {"message": "bad key"}})
            if m == "timeout":
                raise httpx.ReadTimeout("t")
            if name == "openai":
                return httpx.Response(200, json={"choices": [{"message": {"content": "OPENAI-OUT"}}],
                                                 "usage": {"prompt_tokens": 1000, "completion_tokens": 500}})
            return httpx.Response(200, json={"content": [{"type": "text", "text": "ANTHROPIC-OUT"}],
                                             "usage": {"input_tokens": 1000, "output_tokens": 500}})
        return httpx.MockTransport(handler)


@pytest.fixture()
def fake():
    return FakeAI()


def make_client(tmp_path, fake, *, keys=True):
    s = Settings(database_url=f"sqlite:///{tmp_path/'t.db'}", secret_key="test-secret", admin_password="Passw0rd!x",
                 openai_api_key="sk-test-openai" if keys else "", anthropic_api_key="sk-ant-test" if keys else "",
                 openai_default_model="oa-model", anthropic_default_model="an-model",
                 data_dir=tmp_path / "data", games_dir=tmp_path / "games", frontend_dist=tmp_path / "nodist")
    app = create_app(s, transports={"openai": fake.transport("openai"), "anthropic": fake.transport("anthropic")},
                     retry_delay=0)
    c = TestClient(app)
    tok = c.post("/api/auth/login", json={"username": "owner", "password": "Passw0rd!x"}).json()["token"]
    c.headers["Authorization"] = f"Bearer {tok}"
    return c


@pytest.fixture()
def client(tmp_path, fake):
    return make_client(tmp_path, fake)


@pytest.fixture()
def offline(tmp_path, fake):
    """Không có API key nào → chế độ nội bộ."""
    return make_client(tmp_path, fake, keys=False)


def mk_project(c, name="Game A"):
    r = c.post("/api/projects", json={"name": name, "genre": "puzzle", "platform": "mobile"})
    assert r.status_code == 201, r.text
    return r.json()


def mk_task(c, pid, dept="game_dev", **kw):
    body = {"project_id": pid, "department_key": dept, "title": "T", "objective": "Làm X", **kw}
    r = c.post("/api/tasks", json=body)
    assert r.status_code == 201, r.text
    return r.json()
