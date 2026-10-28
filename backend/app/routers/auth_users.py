from __future__ import annotations

import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import Principal, current_user, get_db, require
from ..models import User
from ..schemas import LoginIn, UserIn, UserOut
from ..security import hash_password, make_token, verify_password
from ..services.common import audit

router = APIRouter(prefix="/api", tags=["auth"])
_fails: dict[str, list[float]] = defaultdict(list)
MAX_FAILS, WINDOW = 5, 300


@router.post("/auth/login")
def login(body: LoginIn, request: Request, s: Session = Depends(get_db)):
    now = time.time()
    _fails[body.username] = [t for t in _fails[body.username] if now - t < WINDOW]
    if len(_fails[body.username]) >= MAX_FAILS:
        raise HTTPException(429, "Sai quá nhiều lần. Thử lại sau vài phút.")
    u = s.scalar(select(User).where(User.username == body.username))
    if not u or not u.active or not verify_password(body.password, u.password_hash):
        _fails[body.username].append(now)
        audit(s, body.username[:64], "login_failed", "user")
        s.commit()
        raise HTTPException(401, "Sai tên đăng nhập hoặc mật khẩu.")
    _fails.pop(body.username, None)
    st = request.app.state
    audit(s, u.username, "login", "user", u.id)
    s.commit()
    return {"token": make_token(st.secret, u.username, u.role, st.settings.token_ttl_hours),
            "username": u.username, "role": u.role}


@router.get("/auth/me")
def me(user: Principal = Depends(current_user)):
    return {"username": user.username, "role": user.role}


@router.get("/users", response_model=list[UserOut])
def list_users(_: Principal = Depends(require("owner")), s: Session = Depends(get_db)):
    return s.scalars(select(User).order_by(User.id)).all()


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserIn, user: Principal = Depends(require("owner")), s: Session = Depends(get_db)):
    if s.scalar(select(User).where(User.username == body.username)):
        raise HTTPException(409, "Tên đăng nhập đã tồn tại.")
    u = User(username=body.username, password_hash=hash_password(body.password), role=body.role)
    s.add(u)
    s.flush()
    audit(s, user.username, "user_created", "user", u.id, f"role={u.role}")
    s.commit()
    return u
