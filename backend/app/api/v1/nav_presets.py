import hashlib
import json
from threading import Lock
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, select, text

from app.core.deps import CurrentUser, DbSession
from app.core.rbac import FleetUser
from app.core.roles import is_fleet_management, can_delete_nav_preset
from app.models.nav_preset import NavPreset
from app.models.nav_preset_op_log import NavPresetOpLog
from app.schemas.nav_preset import NavPresetListOut, NavPresetMarker, NavPresetReplaceIn
from app.schemas.nav_preset_op_log import NavPresetOpLogCreate, NavPresetOpLogOut


def _assert_unique_marker_names(markers: list[NavPresetMarker]) -> None:
    seen: set[str] = set()
    for m in markers:
        key = m.name.strip()
        if key in seen:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"标记名称「{key}」重复，请修改为不重名的名称后再保存。",
            )
        seen.add(key)

router = APIRouter(prefix="/nav-presets", tags=["nav-presets"])
_write_lock = Lock()


def _list_from_db(db) -> NavPresetListOut:
    rows = db.scalars(select(NavPreset).order_by(NavPreset.sort_order.asc(), NavPreset.id.asc())).all()
    markers = [NavPresetMarker(name=r.name, lng=r.lng, lat=r.lat, locked=bool(r.is_locked)) for r in rows]
    revision = hashlib.sha256(json.dumps([m.model_dump() for m in markers], sort_keys=True).encode()).hexdigest()
    return NavPresetListOut(markers=markers, revision=revision)


@router.get("", response_model=NavPresetListOut)
def list_nav_presets(db: DbSession, _: CurrentUser) -> NavPresetListOut:
    """所有登录用户可读，保证各端预设点一致。"""
    return _list_from_db(db)


@router.put("", response_model=NavPresetListOut)
def replace_nav_presets(db: DbSession, body: NavPresetReplaceIn, current: FleetUser) -> NavPresetListOut:
    with _write_lock:
        if db.bind.dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(82473103)"))
        return _replace_nav_presets(db, body, current)


def _replace_nav_presets(db, body, current):
    """车队管理类角色可整体替换预设点列表（与前端 v-model 同步）。"""
    _assert_unique_marker_names(body.markers)
    existing = set(db.scalars(select(NavPreset.name)).all())
    incoming = {marker.name.strip() for marker in body.markers}
    if existing - incoming and not can_delete_nav_preset(current.role):
        raise HTTPException(403, "当前角色不能删除或重命名已有标记点")
    if body.revision != _list_from_db(db).revision:
        raise HTTPException(409, "导航点已更新，请重新加载后再保存")
    db.execute(delete(NavPreset))
    for i, m in enumerate(body.markers):
        db.add(
            NavPreset(
                sort_order=i,
                name=m.name.strip(),
                lng=m.lng,
                lat=m.lat,
                is_locked=m.locked,
            )
        )
    db.commit()
    return _list_from_db(db)


@router.post("/operation-logs", response_model=NavPresetOpLogOut, status_code=status.HTTP_201_CREATED)
def create_nav_preset_operation_log(
    db: DbSession,
    body: NavPresetOpLogCreate,
    current: CurrentUser,
) -> NavPresetOpLogOut:
    """记录段内导航标记点操作（新增/删除/解锁锁定/保存）；不含地图拖动。"""
    if not is_fleet_management(current.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要车队管理权限")
    row = NavPresetOpLog(
        user_id=current.id,
        username=current.username,
        display_name=current.display_name or current.username,
        role=current.role,
        action=body.action,
        marker_name=body.marker_name.strip(),
        marker_lng=body.marker_lng,
        marker_lat=body.marker_lat,
        detail=(body.detail or "").strip(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return NavPresetOpLogOut.model_validate(row)
