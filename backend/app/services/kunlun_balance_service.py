"""调用本地昆仑油卡脚本并原子更新当前余额。"""

from __future__ import annotations

import importlib.util
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import requests
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
from app.services.kunlun_login_progress import ensure_login_with_progress

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


def _balance_post(client, base, headers, path, body):
    for attempt in range(3):
        try:
            response = client.session.post(base + '/portal/zyzx/' + path, json=body, headers=headers, timeout=60)
            if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                time.sleep(.5 * (attempt + 1))
                continue
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or payload.get('success') is not True:
                raise RuntimeError('昆仑余额接口返回失败，本次同步未写入')
            return payload.get('data')
        except (requests.Timeout, requests.ConnectionError):
            if attempt == 2:
                raise
            time.sleep(.5 * (attempt + 1))


def fetch_staff_balances(login_module, normalize_card_no, on_progress=None, *, max_workers=4):
    """首两页并行，按实际总数补页；每页独立连接，完整校验后返回。"""
    if not 1 <= max_workers <= 4:
        raise ValueError('余额查询并发数必须在 1 至 4 之间')
    emit = on_progress or (lambda _: None)
    token = ensure_login_with_progress(login_module, emit)
    client = login_module.KunlunLogin('', '')
    headers = client._headers()
    headers['Authorization'] = 'Bearer ' + token['access_token']
    try:
        accounts = _balance_post(client, login_module.BASE, headers, 'unitAcctOuter/listMainAccount', {
            'relationType': '1', 'userId': (token.get('raw') or {}).get('user_id') or '', 'accountType': '1',
        })
    finally:
        client.session.close()
    if not isinstance(accounts, list) or not accounts or not accounts[0].get('enterpriseAccountNo'):
        raise RuntimeError('昆仑平台未返回有效主账户，本次同步未写入')
    account_no = accounts[0]['enterpriseAccountNo']
    emit('账户信息已获取，正在读取油卡余额，请稍候…')
    def fetch_page(number):
        page_client = login_module.KunlunLogin('', '')
        page_headers = page_client._headers()
        page_headers['Authorization'] = 'Bearer ' + token['access_token']
        try:
            return _balance_post(page_client, login_module.BASE, page_headers, 'unitAcctOuter/getStaffList', {
                'data': {'unitMainAccountNo': account_no}, 'pageNum': number, 'pageSize': 100,
            })
        finally:
            page_client.session.close()
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='kunlun-balance') as executor:
        pending = {1: executor.submit(fetch_page, 1)}
        # 第二页仅作预取；实际总页数为 1 时，不使用也不校验其返回值。
        if max_workers > 1:
            pending[2] = executor.submit(fetch_page, 2)
        first = pending[1].result()
        if not isinstance(first, dict) or not isinstance(first.get('rows'), list):
            raise RuntimeError('昆仑余额分页格式异常，本次同步未写入')
        total = int(first['totalRows'])
        page_count = max(1, (total + 99) // 100)
        if total < 0 or page_count > 10000:
            raise RuntimeError('昆仑余额分页数量异常，本次同步未写入')
        pages = {1: first}
        emit(f'已读取第 1/{page_count} 页余额，正在并发查询其余分页…')
        for number in range(2, page_count + 1):
            if number not in pending:
                pending[number] = executor.submit(fetch_page, number)
        required = {future: number for number, future in pending.items() if 1 < number <= page_count}
        for future in as_completed(required):
            number = required[future]
            pages[number] = future.result()
            emit(f'已读取 {len(pages)}/{page_count} 页余额…')
    result = []
    seen = set()
    for number in range(1, page_count + 1):
        page = pages[number]
        expected = min(100, total - (number - 1) * 100)
        if (not isinstance(page, dict) or not isinstance(page.get('rows'), list)
                or int(page['totalRows']) != total or len(page['rows']) != expected):
            raise RuntimeError('昆仑余额分页不完整或查询期间数量变化，本次同步未写入')
        for item in page['rows']:
            card_no = normalize_card_no(item.get('cardNo'))
            if not card_no:
                continue
            if card_no in seen:
                raise RuntimeError('昆仑余额分页出现重复卡号，本次同步未写入')
            seen.add(card_no)
            result.append({'卡号': card_no, '当前余额': item.get('availableAmount'),
                           '车牌': (item.get('carLicense') or '').strip(), '账户编号': item.get('mainAccountNo')})
    return result


def sync_kunlun_balances(on_progress: ProgressCallback | None = None, *, session_factory=None) -> dict:
    emit = on_progress or (lambda _message: None)
    path = _script_path()
    emit("正在连接昆仑油卡平台，准备查询余额…")
    module = _load_script(path)
    login_module = module.load_login_module()
    rows = fetch_staff_balances(login_module, module.normalize_card_no, emit)
    excluded = {
        str(card).strip() for card in getattr(module, "EXCLUDED_CARD_NOS", set())
    }
    filtered = [
        row for row in rows
        if module.normalize_card_no(row.get("卡号")) not in excluded
    ]
    emit(f"已获取 {len(rows)} 条余额数据，正在保存并刷新列表…")
    result = import_balance_rows(filtered, session_factory=session_factory)
    result["balance_excluded"] = len(rows) - len(filtered)
    return result
