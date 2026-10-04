"""车间数据边界。未分配车间的车间管理员不能访问全段数据。"""

from fastapi import HTTPException
from sqlalchemy import false, or_, select

from app.core.roles import WORKSHOP_ADMIN, WORKSHOP_DIRECTOR, is_account_admin
from app.models.vehicle import Vehicle
from app.models.workshop import Workshop


def is_workshop_user(user) -> bool:
    return user.role in {WORKSHOP_ADMIN, WORKSHOP_DIRECTOR}


def scope_condition(model, user):
    if not is_workshop_user(user):
        return None
    if not user.workshop_id:
        return false()
    if hasattr(model, "workshop_id"):
        label = getattr(model, "workshop", None)
        if label is None:
            label = getattr(model, "org_unit", None)
        if label is not None:
            return or_(model.workshop_id == user.workshop_id,
                       (model.workshop_id.is_(None)) & label.in_(select(Workshop.name).where(Workshop.id == user.workshop_id)))
        return model.workshop_id == user.workshop_id
    if hasattr(model, "vehicle_id"):
        return model.vehicle_id.in_(
            select(Vehicle.id).where(Vehicle.workshop_id == user.workshop_id)
        )
    return false()


def scoped(stmt, model, user):
    condition = scope_condition(model, user)
    return stmt.where(condition) if condition is not None else stmt


def require_workshop_access(user, workshop_id):
    if is_workshop_user(user) and (
        user.workshop_id is None or user.workshop_id != workshop_id
    ):
        raise HTTPException(403, "只能操作所属车间的数据；未分配数据请联系段级管理员")


def require_vehicle_access(db, user, vehicle_id):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(404, "车辆不存在")
    require_workshop_access(user, vehicle.workshop_id)
    return vehicle


def require_global_management(user):
    if not is_account_admin(user.role):
        raise HTTPException(403, "共享主数据与全段同步需要段级管理员权限")


def validate_workshop(db, workshop_id):
    if workshop_id is not None and not db.get(Workshop, workshop_id):
        raise HTTPException(400, "车间不存在")
