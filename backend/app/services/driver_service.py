from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.driver import Driver
from app.models.workshop import Workshop
from app.schemas.driver import DriverOut


def driver_to_out(db: Session, row: Driver) -> DriverOut:
    workshop_name: str | None = None
    if row.workshop_id:
        ws = db.get(Workshop, row.workshop_id)
        workshop_name = ws.name if ws else None
    data = DriverOut.model_validate(row).model_dump()
    data["workshop_name"] = workshop_name
    return DriverOut(**data)


def drivers_to_out_list(db: Session, rows: list[Driver]) -> list[DriverOut]:
    if not rows:
        return []
    ws_ids = {r.workshop_id for r in rows if r.workshop_id}
    name_by_id: dict[int, str] = {}
    if ws_ids:
        for ws in db.scalars(select(Workshop).where(Workshop.id.in_(ws_ids))).all():
            name_by_id[ws.id] = ws.name
    out: list[DriverOut] = []
    for row in rows:
        data = DriverOut.model_validate(row).model_dump()
        data["workshop_name"] = name_by_id.get(row.workshop_id) if row.workshop_id else None
        out.append(DriverOut(**data))
    return out
