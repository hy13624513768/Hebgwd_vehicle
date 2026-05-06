"""一次性检查：库内 registered_at 数量 + VehicleOut 序列化字段。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.vehicle import Vehicle  # noqa: E402
from app.schemas.vehicle import VehicleOut  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        total = db.scalar(select(func.count()).select_from(Vehicle)) or 0
        with_reg = db.scalar(select(func.count()).select_from(Vehicle).where(Vehicle.registered_at.isnot(None))) or 0
        print(f"bus_vehicle rows: {total}, registered_at NOT NULL: {with_reg}")
        rows = db.scalars(select(Vehicle).order_by(Vehicle.id).limit(3)).all()
        for r in rows:
            vo = VehicleOut.model_validate(r)
            d = vo.model_dump(mode="json")
            print(r.plate_number, "orm=", r.registered_at, "out=", d.get("registered_at"))
        # 与 FastAPI 响应类似的 JSON
        sample = VehicleOut.model_validate(rows[0]).model_dump(mode="json") if rows else {}
        print("sample_json_keys:", sorted(sample.keys()))
        print("sample_json_snippet:", json.dumps({k: sample[k] for k in ("plate_number", "registered_at") if sample}, ensure_ascii=False))
    finally:
        db.close()


if __name__ == "__main__":
    main()
