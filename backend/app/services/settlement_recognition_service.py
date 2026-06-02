"""结算单识别与入库。"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.repair_record import RepairRecord, RepairSettlement, RepairSettlementLine
from app.services.glm_vision_service import recognize_settlement_image
from app.services.term_match_service import _load_term_index, match_line_to_term


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    s = str(raw).strip()[:10]
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _dec(v) -> Decimal:
    try:
        return Decimal(str(v or 0))
    except Exception:
        return Decimal("0")


def recognize_and_save(db: Session, repair: RepairRecord) -> RepairSettlement:
    if not repair.photo_settlement_path:
        raise ValueError("未上传结算单照片")
    path = Path(repair.photo_settlement_path)
    if not path.is_file():
        raise ValueError("结算单照片文件不存在")

    settlement = repair.settlement
    if not settlement:
        settlement = RepairSettlement(repair_record_id=repair.id, recognition_status="processing")
        db.add(settlement)
        db.flush()
    else:
        settlement.recognition_status = "processing"
        settlement.recognition_error = None
        for line in list(settlement.lines):
            db.delete(line)
        db.flush()

    repair.status = "recognizing"
    db.flush()

    try:
        parsed = recognize_settlement_image(path)
        settlement.raw_json = json.dumps(parsed, ensure_ascii=False)
        settlement.order_no = str(parsed.get("order_no") or repair.repair_order_no or "")
        settlement.plate_number = str(parsed.get("plate_number") or "")
        settlement.vehicle_model = str(parsed.get("vehicle_model") or "")
        settlement.owner = str(parsed.get("owner") or "")
        settlement.shop_name = str(parsed.get("shop_name") or "")
        settlement.mileage_in = int(parsed.get("mileage_in") or 0)
        settlement.service_date = _parse_date(parsed.get("service_date"))
        settlement.total_amount = _dec(parsed.get("total_amount"))

        term_index = _load_term_index(db)
        items = parsed.get("items") or []
        if not isinstance(items, list):
            items = []
        for idx, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("item_name") or "").strip()
            part = str(item.get("part_name") or "").strip()
            raw = name if not part else f"{name} {part}"
            match = match_line_to_term(db, raw or name, index=term_index)
            db.add(
                RepairSettlementLine(
                    settlement_id=settlement.id,
                    line_no=idx,
                    item_name=name or raw,
                    part_name=part,
                    quantity=_dec(item.get("quantity") or 1),
                    unit=str(item.get("unit") or ""),
                    labor_fee=_dec(item.get("labor_fee")),
                    part_fee=_dec(item.get("part_fee")),
                    amount=_dec(item.get("amount")),
                    raw_text=raw,
                    term_id=match.term_id,
                    term_name=match.term_name,
                    category_l1=match.category_l1,
                    category_l2=match.category_l2,
                    match_score=match.score,
                    match_method=match.method,
                )
            )

        settlement.recognition_status = "done"
        repair.status = "recognized"
    except Exception as exc:
        settlement.recognition_status = "failed"
        settlement.recognition_error = str(exc)
        repair.status = "recognize_failed"
        raise

    db.flush()
    return settlement
