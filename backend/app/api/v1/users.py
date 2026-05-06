from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.core.deps import DbSession, get_current_user
from app.core.roles import (
    SUPER_ADMIN,
    assignable_roles_for_actor,
    can_actor_manage_user,
    is_account_admin,
    rank,
)
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user_admin import (
    RoleDefinitionOut,
    UserAdminCreate,
    UserAdminListOut,
    UserAdminOut,
    UserAdminUpdate,
)
from app.services.auth_service import PWD_REGEX

router = APIRouter(prefix="/users", tags=["users"])

ROLE_DESCRIPTIONS: dict[str, str] = {
    SUPER_ADMIN: "全系统最高权限，可管理所有账号（含超级管理员分级）。",
    "section_admin": "段内业务与账号管理（不可操作内置超级管理员账号）。",
    "workshop_director": "车间范围管理与审批协调。",
    "workshop_admin": "车间日常事务与数据维护。",
    "vehicle_driver": "车辆驾驶与出车相关操作，默认不可进行车队全量配置。",
}


def _require_account_admin(user: User) -> User:
    if not is_account_admin(user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要段级管理员或超级管理员权限")
    return user


def require_account_admin_user(
    current: Annotated[User, Depends(get_current_user)],
) -> User:
    return _require_account_admin(current)


AccountAdmin = Annotated[User, Depends(require_account_admin_user)]


@router.get("/role-definitions", response_model=list[RoleDefinitionOut])
def list_role_definitions(_: AccountAdmin) -> list[RoleDefinitionOut]:
    """分级说明（预留扩展 description，供前端展示）。"""
    order = [
        ("vehicle_driver", "车辆驾驶员"),
        ("workshop_admin", "车间管理员"),
        ("workshop_director", "车间主任"),
        ("section_admin", "段级管理员"),
        (SUPER_ADMIN, "超级管理员"),
    ]
    out: list[RoleDefinitionOut] = []
    for code, label in order:
        out.append(
            RoleDefinitionOut(
                code=code,
                label=label,
                rank=rank(code),
                description=ROLE_DESCRIPTIONS.get(code, ""),
            )
        )
    return out


@router.get("/assignable-roles", response_model=list[str])
def list_assignable_roles(current: AccountAdmin) -> list[str]:
    return assignable_roles_for_actor(current.role)


@router.get("", response_model=UserAdminListOut)
def list_users(
    db: DbSession,
    current: AccountAdmin,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    q: Annotated[str | None, Query(max_length=64)] = None,
) -> UserAdminListOut:
    stmt = select(User)
    count_stmt = select(func.count()).select_from(User)
    if q and q.strip():
        like = f"%{q.strip()}%"
        cond = or_(User.username.ilike(like), User.display_name.ilike(like))
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    total = int(db.scalar(count_stmt) or 0)
    rows = list(db.scalars(stmt.order_by(User.id.asc()).offset(skip).limit(limit)).all())
    return UserAdminListOut(items=[UserAdminOut.model_validate(r) for r in rows], total=total)


@router.post("", response_model=UserAdminOut, status_code=status.HTTP_201_CREATED)
def create_user(db: DbSession, current: AccountAdmin, body: UserAdminCreate) -> User:
    allowed = set(assignable_roles_for_actor(current.role))
    if body.role not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无权分配该角色")
    if not PWD_REGEX.fullmatch(body.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码需 8-16 位并包含大小写字母、数字与特殊字符",
        )
    username = body.username.strip()
    if not re.match(r"^[A-Za-z0-9_\-.]{1,64}$", username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名仅允许字母数字与 _-. ")
    u = User(
        username=username,
        password_hash=hash_password(body.password),
        display_name=body.display_name.strip(),
        role=body.role,
        is_active=body.is_active,
    )
    db.add(u)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")
    db.refresh(u)
    return UserAdminOut.model_validate(u)


@router.patch("/{user_id}", response_model=UserAdminOut)
def update_user(db: DbSession, current: AccountAdmin, user_id: int, body: UserAdminUpdate) -> User:
    row = db.get(User, user_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if not can_actor_manage_user(current.role, row.username, row.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改该用户")
    if row.username.lower() == "admin":
        if body.role is not None and str(body.role) != SUPER_ADMIN:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="内置超级管理员账号角色必须为超级管理员")
        if body.is_active is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不可禁用内置超级管理员账号")

    data = body.model_dump(exclude_unset=True)
    if "role" in data and data["role"] is not None:
        nr = str(data["role"])
        allowed = set(assignable_roles_for_actor(current.role))
        if nr not in allowed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无权分配该角色")
        if row.username.lower() == "admin" and nr != SUPER_ADMIN:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不可变更内置超级管理员角色")
        row.role = nr
    if "display_name" in data and data["display_name"] is not None:
        row.display_name = data["display_name"].strip()
    if "password" in data and data["password"] is not None:
        pwd = data["password"]
        if not PWD_REGEX.fullmatch(pwd):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="密码需 8-16 位并包含大小写字母、数字与特殊字符",
            )
        row.password_hash = hash_password(pwd)
    if "is_active" in data and data["is_active"] is not None:
        if row.username.lower() == "admin" and data["is_active"] is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不可禁用内置超级管理员账号")
        row.is_active = bool(data["is_active"])

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="更新失败")
    db.refresh(row)
    return UserAdminOut.model_validate(row)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(db: DbSession, current: AccountAdmin, user_id: int) -> None:
    if current.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不可删除当前登录账号")
    row = db.get(User, user_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if row.username.lower() == "admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不可删除内置超级管理员账号")
    if not can_actor_manage_user(current.role, row.username, row.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权删除该用户")
    db.delete(row)
    db.commit()
