from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.roles import LEGACY_DRIVER, VEHICLE_DRIVER, is_account_admin, is_fleet_management
from app.core.data_scope import require_workshop_access
from app.models.driver import Driver
from app.models.user import User
from app.models.workshop import Workshop
from app.schemas.driver import DriverOut


def _is_media_reference(value: str | None) -> bool:
    return bool(value and value.startswith("media://"))


def _with_document_state(data: dict) -> dict:
    health_media = _is_media_reference(data.get("health_check_report"))
    onboarding_media = _is_media_reference(data.get("outsourcing_onboarding"))
    data["has_health_check_report"] = health_media
    data["has_outsourcing_onboarding"] = onboarding_media
    # 媒体对象键属于后端存储细节；前端只通过鉴权下载接口访问。
    if health_media:
        data["health_check_report"] = None
    if onboarding_media:
        data["outsourcing_onboarding"] = None
    return data


def validate_driver_account(db: Session, actor: User, user_id: int | None, workshop_id: int | None) -> None:
    if user_id is None:
        return
    account = db.get(User, user_id)
    if not account:
        raise HTTPException(400, "绑定账号不存在")
    require_workshop_access(actor, account.workshop_id)
    if account.role not in {VEHICLE_DRIVER, LEGACY_DRIVER}:
        raise HTTPException(400, "只能绑定驾驶员角色账号")
    if account.workshop_id != workshop_id:
        raise HTTPException(400, "驾驶员与绑定账号的车间必须一致，请先调整账号归属")


def driver_to_out(db: Session, row: Driver, user=None) -> DriverOut:
    workshop_name: str | None = None
    if row.workshop_id:
        ws = db.get(Workshop, row.workshop_id)
        workshop_name = ws.name if ws else None
    data = _with_document_state(DriverOut.model_validate(row).model_dump())
    data["workshop_name"] = workshop_name
    return _visible_fields(DriverOut(**data), user)


def drivers_to_out_list(db: Session, rows: list[Driver], user=None) -> list[DriverOut]:
    if not rows:
        return []
    ws_ids = {r.workshop_id for r in rows if r.workshop_id}
    name_by_id: dict[int, str] = {}
    if ws_ids:
        for ws in db.scalars(select(Workshop).where(Workshop.id.in_(ws_ids))).all():
            name_by_id[ws.id] = ws.name
    out: list[DriverOut] = []
    for row in rows:
        data = _with_document_state(DriverOut.model_validate(row).model_dump())
        data["workshop_name"] = name_by_id.get(row.workshop_id) if row.workshop_id else None
        out.append(_visible_fields(DriverOut(**data), user))
    return out


def _visible_fields(out: DriverOut, user) -> DriverOut:
    if user is None:
        return out
    can_view_full = is_account_admin(user.role) or (
        is_fleet_management(user.role)
        and user.workshop_id is not None
        and user.workshop_id == out.workshop_id
    )
    if not can_view_full:
        out.is_restricted = True
        out.license_type = ""
        out.vehicle_type_label = ""
        out.status = ""
        out.id_card = None
        out.health_check_report = None
        out.outsourcing_onboarding = None
        out.first_hire_date = None
        out.user_id = None
        out.has_health_check_report = False
        out.has_outsourcing_onboarding = False
    return out
