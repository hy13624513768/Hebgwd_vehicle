from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.datetime_utils import as_utc
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import LoginResponse, UserInfo

PWD_REGEX = re.compile(r"(?=.*[0-9])(?=.*[A-Z])(?=.*[a-z])(?=.*[^a-zA-Z0-9]).{8,16}")
MAX_FAILED = 3
LOCK_MINUTES = 10


def authenticate(db: Session, username: str, password: str) -> LoginResponse:
    user = db.scalar(select(User).where(User.username == username))
    now = datetime.now(timezone.utc)

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名密码错误")

    if user.lock_until and as_utc(user.lock_until) > now:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="您连续输入错误次数过多，您的用户已被锁定十分钟",
        )

    if user.lock_until and as_utc(user.lock_until) <= now:
        user.failed_attempts = 0
        user.lock_until = None

    if not verify_password(password, user.password_hash):
        user.failed_attempts += 1
        if user.failed_attempts >= MAX_FAILED:
            user.lock_until = now + timedelta(minutes=LOCK_MINUTES)
        db.commit()
        locked = user.lock_until and as_utc(user.lock_until) > now
        if locked:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="您连续输入错误次数过多，您的用户已被锁定十分钟",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名密码错误,如果连续错误超过3次，用户将被锁定",
        )

    user.failed_attempts = 0
    user.lock_until = None
    user.last_login_at = now
    db.commit()

    token = create_access_token(str(user.id))
    return LoginResponse(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
        user=UserInfo(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            role=getattr(user, "role", "staff"),
            workshop_id=getattr(user, "workshop_id", None),
        ),
    )


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)
