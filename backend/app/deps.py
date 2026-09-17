import uuid

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.models import User, UserRole, UserStatus
from app.db.session import get_db


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user_id = uuid.UUID(decode_token(token, "access"))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.get(User, user_id)
    if user is None or user.status != UserStatus.active:
        raise HTTPException(status_code=401, detail="User not found or disabled")
    return user


def require_user(user: User = Depends(get_current_user)) -> User:
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin required")
    return user
