from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Request

from .security import read_token

RANK = {"viewer": 0, "manager": 1, "owner": 2}


@dataclass
class Principal:
    username: str
    role: str


def get_db(request: Request):
    with request.app.state.sf() as s:
        yield s


def current_user(request: Request, authorization: str = Header(default="")) -> Principal:
    token = authorization[7:] if authorization.lower().startswith("bearer ") else ""
    data = read_token(request.app.state.secret, token) if token else None
    if not data:
        raise HTTPException(401, "Chưa đăng nhập hoặc phiên đã hết hạn.")
    return Principal(data["u"], data["r"])


def require(role: str):
    """Phân quyền ở backend: viewer < manager < owner."""
    def dep(user: Principal = Depends(current_user)) -> Principal:
        if RANK[user.role] < RANK[role]:
            raise HTTPException(403, f"Cần quyền '{role}' trở lên.")
        return user
    return dep
