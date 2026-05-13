from fastapi import APIRouter
from sqlalchemy import delete, select

from app.core.deps import CurrentUser, DbSession
from app.core.rbac import FleetUser
from app.models.nav_preset import NavPreset
from app.schemas.nav_preset import NavPresetListOut, NavPresetMarker, NavPresetReplaceIn

router = APIRouter(prefix="/nav-presets", tags=["nav-presets"])


def _list_from_db(db) -> NavPresetListOut:
    rows = db.scalars(select(NavPreset).order_by(NavPreset.sort_order.asc(), NavPreset.id.asc())).all()
    return NavPresetListOut(
        markers=[
            NavPresetMarker(name=r.name, lng=r.lng, lat=r.lat, locked=bool(r.is_locked)) for r in rows
        ],
    )


@router.get("", response_model=NavPresetListOut)
def list_nav_presets(db: DbSession, _: CurrentUser) -> NavPresetListOut:
    """所有登录用户可读，保证各端预设点一致。"""
    return _list_from_db(db)


@router.put("", response_model=NavPresetListOut)
def replace_nav_presets(db: DbSession, body: NavPresetReplaceIn, _: FleetUser) -> NavPresetListOut:
    """车队管理类角色可整体替换预设点列表（与前端 v-model 同步）。"""
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
