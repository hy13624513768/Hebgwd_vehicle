"""调用本地昆仑油卡脚本并原子更新当前余额。"""

from __future__ import annotations

import importlib.util
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from threading import Lock
from types import ModuleType
from typing import Callable
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.fuel import FuelBalance, FuelCardLookup
from app.models.workshop import Workshop

ProgressCallback = Callable[[str], None]
_import_lock = Lock()


def _script_path() -> Path:
    configured = settings.kunlun_balance_script.strip()
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
    else:
        # 本地默认布局：Hebgwd_vehicle 与“中国石油”同在 project 目录。
        path = Path(__file__).resolve().parents[4] / "中国石油" / "获取油卡余额.py"
    path = path.resolve()
    if not path.is_file():
        raise RuntimeError(f"找不到昆仑油卡接口脚本：{path}")
    return path


def _load_script(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("hebgwd_local_kunlun_balance", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载昆仑油卡接口脚本")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("load_login_module", "fetch_all_staff_balances", "normalize_card_no"):
        if not callable(getattr(module, name, None)):
            raise RuntimeError(f"昆仑油卡接口脚本缺少函数：{name}")
    return module


def _money(value: object) -> Decimal:
    try:
        amount = Decimal(str(value).replace(",", "").strip())
        if not amount.is_finite():
            raise ValueError("non-finite")
        return amount.quantize(Decimal("0.01"))
    except (InvalidOperation, AttributeError, TypeError, ValueError) as exc:
        raise RuntimeError("昆仑平台返回了无效的当前余额，本次同步未写入") from exc


def import_balance_rows(rows: list[dict], *, session_factory=None) -> dict:
    """将昆仑 getStaffList 返回值更新到现有余额表；不清空历史数据。"""
    normalized: dict[str, Decimal] = {}
    for item in rows:
        card_no = str(item.get("卡号") or "").strip()
        if not card_no:
            continue
        if card_no in normalized:
            raise RuntimeError(f"昆仑平台返回重复卡号：{card_no}，本次同步未写入")
        normalized[card_no] = _money(item.get("当前余额"))
    if not normalized:
        raise RuntimeError("昆仑平台未返回有效油卡余额，原有数据已保留")

    factory = session_factory or SessionLocal
    with _import_lock, factory() as db, db.begin():
        lookups = {
            row.card_no.strip(): row
            for row in db.scalars(select(FuelCardLookup)).all()
        }
        workshop_ids = {
            row.name: row.id for row in db.scalars(select(Workshop)).all()
        }
        snapshots = {
            row.card_no: row for row in db.scalars(select(FuelBalance)).all()
        }
        matched = 0
        for card_no, amount in normalized.items():
            row = snapshots.get(card_no)
            if row is None:
                row = FuelBalance(card_no=card_no)
                db.add(row)
                snapshots[card_no] = row
            link = lookups.get(card_no)
            if link is not None:
                row.workshop = link.workshop
                row.workshop_id = workshop_ids.get(link.workshop)
                row.vehicle_no = link.vehicle_no
                matched += 1
            # 新接口只有 availableAmount；映射到现有 amount/total，备用金固定为 0。
            row.amount = amount
            row.reserve_fund = Decimal("0.00")
            row.total = amount
            row.updated_at = datetime.now(ZoneInfo("UTC"))

    return {
        "ok": True,
        "platform": "kunlun",
        "balance_written": len(normalized),
        "balance_matched": matched,
        "balance_unmatched": len(normalized) - matched,
        "record_written": 0,
        "record_matched": 0,
    }


def sync_kunlun_balances(on_progress: ProgressCallback | None = None, *, session_factory=None) -> dict:
    emit = on_progress or (lambda _message: None)
    path = _script_path()
    emit("正在加载本地昆仑油卡接口…")
    module = _load_script(path)
    emit("正在登录昆仑油卡平台并查询司机卡余额…")
    login_module = module.load_login_module()
    rows = module.fetch_all_staff_balances(login_module)
    excluded = {
        str(card).strip() for card in getattr(module, "EXCLUDED_CARD_NOS", set())
    }
    filtered = [
        row for row in rows
        if module.normalize_card_no(row.get("卡号")) not in excluded
    ]
    emit(f"平台返回 {len(rows)} 张油卡，正在写入本地数据库…")
    result = import_balance_rows(filtered, session_factory=session_factory)
    result["balance_excluded"] = len(rows) - len(filtered)
    return result
