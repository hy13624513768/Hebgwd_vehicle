from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.core.deps import get_current_user
from app.core.roles import is_fleet_management
from app.models.user import User


def require_fleet_management(user: User = Depends(get_current_user)) -> User:
    """段级/车间/超级管理员等车管类角色：可维护车辆/驾驶员/维保/油卡等。"""
    if not is_fleet_management(user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要车队管理权限")
    return user


def require_report_export(user: User = Depends(get_current_user)) -> User:
    """与车队管理同级：可导出报表。"""
    if not is_fleet_management(user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要车队管理或报表导出权限")
    return user


FleetUser = Annotated[User, Depends(require_fleet_management)]
ExporterUser = Annotated[User, Depends(require_report_export)]
