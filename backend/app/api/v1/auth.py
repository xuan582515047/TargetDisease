import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.db.models import User, UserStatus
from app.db.session import get_db
from app.deps import require_user
from app.schemas import LoginRequest, RegisterRequest, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(response: Response, user_id: uuid.UUID):
    access = security.create_access_token(str(user_id))
    refresh = security.create_refresh_token(str(user_id))
    response.set_cookie(
        "access_token",
        access,
        httponly=True,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    response.set_cookie(
        "refresh_token",
        refresh,
        httponly=True,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 3600,
    )


def _norm_email(email: str) -> str:
    return email.strip().lower()


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    email = _norm_email(body.email)
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="邮箱已存在！！")
    user = User(email=email, password_hash=security.hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=UserOut)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    email = _norm_email(body.email)
    user = db.query(User).filter(User.email == email).first()
    if user is None or not security.verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    _set_auth_cookies(response, user.id)
    return user


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"ok": True}


@router.post("/refresh", response_model=UserOut)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        user_id = uuid.UUID(security.decode_token(refresh_token, "refresh"))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = db.get(User, user_id)
    if user is None or user.status != UserStatus.active:
        raise HTTPException(status_code=401, detail="User not found or disabled")
    access = security.create_access_token(str(user.id))
    response.set_cookie(
        "access_token",
        access,
        httponly=True,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return user


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(require_user)):
    return user
