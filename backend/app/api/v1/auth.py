from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db, user_to_info
from app.core.security import hash_password
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    SliderCompleteRequest,
    SliderStartResponse,
    UserInfo,
)
from app.services.auth_service import authenticate
from app.services.slider_service import slider_store

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/slider/start", response_model=SliderStartResponse)
def slider_start() -> SliderStartResponse:
    return SliderStartResponse(session_id=slider_store.start())


@router.post("/slider/complete", status_code=status.HTTP_204_NO_CONTENT)
def slider_complete(body: SliderCompleteRequest) -> None:
    if not slider_store.complete(body.session_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="滑块会话无效或已过期")


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> LoginResponse:
    return authenticate(db, body.username.strip(), body.password, body.slider_session_id)


@router.get("/me", response_model=UserInfo)
def me(current: Annotated[User, Depends(get_current_user)]) -> UserInfo:
    return user_to_info(current)


def bootstrap_admin_if_needed(db: Session) -> None:
    username = settings.bootstrap_admin_username.strip()
    if not username:
        return
    exists = db.scalar(select(User).where(User.username == username))
    if exists:
        return
    if not settings.bootstrap_admin_password:
        return
    user = User(
        username=username,
        password_hash=hash_password(settings.bootstrap_admin_password),
        display_name=settings.bootstrap_admin_display_name or username,
        role="super_admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
