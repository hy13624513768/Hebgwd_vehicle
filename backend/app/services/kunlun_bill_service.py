"""昆仑车队油品订单：复用余额登录，并发抓取、逐区间原子写入。"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import time
import requests
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.fuel import FuelCardLookup, FuelRecord
from app.models.vehicle import Vehicle
from app.models.workshop import Workshop
from app.services.kunlun_balance_service import _load_script, _script_path, _import_lock
from app.services.kunlun_login_progress import ensure_login_with_progress


def _number(value, label):
    try:
        result = Decimal(str(value).replace(',', '').strip())
        if not result.is_finite() or result < 0:
            raise ValueError(label)
        return result.quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise RuntimeError(f'昆仑账单{label}无效，本次同步未写入') from exc


def _present(value):
    return value is not None and str(value).strip() != ''


# 仅保存昆仑账单页展示的业务字段，不保存登录数据或平台内部标识。
BILL_FIELDS = (
    'driverName', 'staffNo', 'licensePlate', 'productTypeName', 'actualPayTotalAmount',
    'stationName', 'orderNo', 'orderTime', 'transRecordNo', 'transactionPlaceName',
    'transactionSubType', 'oilName', 'productQty', 'oilReceivableAmount',
    'oilReceivedAmount', 'oilDiscountAmount', 'nonfuelProductName',
    'nonfuelReceivableAmount', 'nonfuelReceivedAmount', 'nonfuelDiscountAmount',
    'balanceAfTransaction', 'accountNo', 'memberName', 'memberPhone', 'ewalletCardNo',
)
PRODUCT_FIELDS = ('productCode', 'productName', 'productType', 'priceUnit', 'unit', 'productQty')


def _business_data(item, fields):
    return {key: str(item[key]) if isinstance(item[key], Decimal) else item[key]
            for key in fields if key in item}


def fetch_bill_products(order_no):
    """商品明细按需查询，复用余额查询的登录流程。"""
    login_module = _load_script(_script_path()).load_login_module()
    token = login_module.ensure_login()
    client = login_module.KunlunLogin('', '')
    try:
        headers = client._headers()
        headers['Authorization'] = 'Bearer ' + token['access_token']
        rows = _post(client, login_module.BASE, headers, 'consumptionRecord/detail', {'orderNo': order_no})
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise RuntimeError('昆仑商品明细格式异常')
        return [_business_data(row, PRODUCT_FIELDS) for row in rows]
    finally:
        client.session.close()


class BillPlatformError(RuntimeError):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def _post(client, base, headers, path, body):
    dates = body.get('businessDay')
    context = f"（{dates[0]} 至 {dates[1]}，第 {body.get('pageNum', 1)} 页）" if dates else ''
    for attempt in range(3):
        try:
            response = client.session.post(base + '/portal/zyzx/' + path, json=body, headers=headers, timeout=60)
        except (requests.Timeout, requests.ConnectionError) as exc:
            if attempt < 2:
                time.sleep(.5 * (attempt + 1))
                continue
            raise BillPlatformError(f'连接昆仑平台超时或网络异常{context}，请稍后重新查询') from exc
        if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
            time.sleep(.5 * (attempt + 1))
            continue
        if response.status_code >= 400:
            raise BillPlatformError(f'昆仑平台查询失败{context}：HTTP {response.status_code}，请稍后重新查询', response.status_code)
        try:
            payload = response.json()
        except ValueError as exc:
            raise BillPlatformError(f'昆仑平台返回无效数据{context}，请稍后重新查询') from exc
        if not isinstance(payload, dict) or payload.get('success') is not True:
            raise BillPlatformError(f'昆仑平台查询未成功{context}，请稍后重新查询')
        return payload.get('data')


def _fetch_bill_rows_serial(login_module, date_from: date, date_to: date, on_progress=None, *, token_data=None, accounts_data=None):
    emit = on_progress or (lambda _: None)
    token = token_data or ensure_login_with_progress(login_module, emit)
    client = login_module.KunlunLogin('', '')
    headers = client._headers()
    headers['Authorization'] = 'Bearer ' + token['access_token']
    try:
        accounts = accounts_data or _post(client, login_module.BASE, headers, 'unitAcctOuter/listMainAccount', {
            'relationType': '1', 'userId': (token.get('raw') or {}).get('user_id') or '', 'accountType': '1',
        })
        if not isinstance(accounts, list) or not accounts:
            raise RuntimeError('昆仑平台未返回单位账户')
        result = {}
        for account_index, account in enumerate(accounts, 1):
            if not account.get('mainAccountNo') or not account.get('enterpriseNo'):
                raise RuntimeError('昆仑单位账户字段不完整')
            start = date_from
            while start <= date_to:
                # 官方页面限定一个月；28 天窗口兼容所有月份。
                end = min(start + timedelta(days=27), date_to)
                page_num, fetched, expected = 1, 0, None
                window_keys = []
                while True:
                    emit(f'查询账户 {account_index}/{len(accounts)}，{start} 至 {end}，第 {page_num} 页…')
                    try:
                        page = _post(client, login_module.BASE, headers, 'consumptionRecord/page', {
                            'mainAccountNo': account['mainAccountNo'], 'enterpriseNo': account['enterpriseNo'],
                            'driverName': '', 'cardNo': '', 'licensePlate': '', 'productTypeName': '油品',
                            'businessDay': [start.isoformat(), end.isoformat()], 'pageNum': page_num, 'pageSize': 100,
                        })
                    except BillPlatformError as exc:
                        if exc.status_code and exc.status_code >= 500 and start < end:
                            for key in window_keys:
                                result.pop(key, None)
                            end = start + timedelta(days=(end - start).days // 2)
                            page_num, fetched, expected = 1, 0, None
                            window_keys = []
                            emit(f'昆仑大范围查询暂时失败，改为 {start} 至 {end} 的小范围重试…')
                            continue
                        raise
                    if not isinstance(page, dict) or not isinstance(page.get('rows'), list):
                        raise RuntimeError('昆仑账单分页格式异常')
                    total = int(page['totalRows'])
                    if total < 0 or (expected is not None and total != expected):
                        raise RuntimeError('查询期间昆仑账单数量发生变化，请重新同步')
                    expected = total
                    rows = page['rows']
                    for row in rows:
                        order_no = str(row.get('orderNo') or '').strip()
                        if not order_no:
                            raise RuntimeError('昆仑账单缺少订单号')
                        # 订单号稳定；交易流水号可能晚于订单生成，不能用它作为唯一键。
                        key = 'kunlun:' + hashlib.sha256((str(account['mainAccountNo']) + ':' + order_no).encode()).hexdigest()
                        if key in result:
                            raise RuntimeError('昆仑账单分页返回重复订单，请重新同步')
                        item = dict(row, platform_record_id=key)
                        if _present(item.get('ewalletCardNo')) and not _present(item.get('productQty')):
                            try:
                                details = _post(client, login_module.BASE, headers, 'consumptionRecord/detail', {'orderNo': order_no})
                                item['productDetails'] = [_business_data(d, PRODUCT_FIELDS) for d in details]
                                oil = [d for d in details if str(d.get('unit') or '').lower() in {'l', '升'}]
                                if oil:
                                    item['productQty'] = sum((_number(d.get('productQty'), '升数') for d in oil), Decimal('0'))
                            except Exception:
                                # 平台部分订单的明细返回 500：保存账单，明确标记升数缺失。
                                emit('部分订单明细暂不可用，缺失升数将显示为“—”…')
                        result[key] = item
                        window_keys.append(key)
                    fetched += len(rows)
                    if fetched > expected or (fetched < expected and not rows):
                        raise RuntimeError('昆仑账单分页不完整，本次同步未写入')
                    if fetched == expected:
                        break
                    page_num += 1
                    if page_num > 10000:
                        raise RuntimeError('昆仑账单分页超出安全上限')
                start = end + timedelta(days=1)
        return list(result.values())
    finally:
        client.session.close()


def fetch_bill_rows(login_module, date_from: date, date_to: date, on_progress=None, *,
                    max_workers=4, window_days=28, on_batch_ready=None):
    """登录一次；每路独立 Session，完整区间校验通过后才交给入库回调。"""
    emit = on_progress or (lambda _: None)
    emit('正在连接昆仑油卡平台，准备查询账单…')
    token = ensure_login_with_progress(login_module, emit)
    client = login_module.KunlunLogin('', '')
    headers = client._headers()
    headers['Authorization'] = 'Bearer ' + token['access_token']
    try:
        accounts = _post(client, login_module.BASE, headers, 'unitAcctOuter/listMainAccount', {
            'relationType': '1', 'userId': (token.get('raw') or {}).get('user_id') or '', 'accountType': '1',
        })
    finally:
        client.session.close()
    if not isinstance(accounts, list) or not accounts:
        raise RuntimeError('昆仑平台未返回单位账户')
    emit('账户信息已获取，正在按日期区间读取账单，请稍候…')
    if not 1 <= max_workers <= 4 or not 1 <= window_days <= 28:
        raise ValueError('无效的并发数或日期区间大小')
    jobs = []
    for account in accounts:
        if not account.get('mainAccountNo') or not account.get('enterpriseNo'):
            raise RuntimeError('昆仑单位账户字段不完整')
        start = date_from
        while start <= date_to:
            end = min(start + timedelta(days=window_days - 1), date_to)
            jobs.append((account, start, end))
            start = end + timedelta(days=1)
    # 优先查询最近区间，默认日期倒序列表更快显示最新账单。
    jobs.sort(key=lambda job: job[1], reverse=True)
    result = {}
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='kunlun-bill') as executor:
        pending = {executor.submit(_fetch_bill_rows_serial, login_module, start, end, emit,
                                   token_data=token, accounts_data=[account]): (start, end)
                   for account, start, end in jobs}
        try:
            for future in as_completed(pending):
                start, end = pending[future]
                rows = future.result()
                for row in rows:
                    key = row['platform_record_id']
                    if key in result:
                        raise RuntimeError('昆仑账单重复订单，请重新查询')
                    result[key] = row
                if on_batch_ready is not None:
                    on_batch_ready(rows, start, end)
        except Exception:
            for future in pending:
                future.cancel()
            raise
    return list(result.values())


def import_bill_rows(rows, date_from, date_to, *, session_factory=None):
    normalized = {}
    for item in rows:
        key = item['platform_record_id']
        if key in normalized:
            raise RuntimeError('昆仑账单重复订单')
        try:
            occurred = datetime.fromisoformat(str(item.get('orderTime') or ''))
            if occurred.tzinfo is None:
                occurred = occurred.replace(tzinfo=ZoneInfo('Asia/Shanghai'))
            local_day = occurred.astimezone(ZoneInfo('Asia/Shanghai')).date()
            if not date_from <= local_day <= date_to:
                raise ValueError('out of range')
        except ValueError as exc:
            raise RuntimeError('昆仑账单时间无效或超出查询日期') from exc
        volume_available = _present(item.get('productQty'))
        balance_available = _present(item.get('balanceAfTransaction'))
        amount = item.get('oilReceivedAmount')
        if not _present(amount):
            amount = item.get('actualPayTotalAmount')
        normalized[key] = {
            'platform_data': _business_data(item, BILL_FIELDS),
            'card_asn': str(item.get('ewalletCardNo') or '').strip(),
            'car_no': str(item.get('licensePlate') or '').strip(),
            'occur_time': occurred.astimezone(timezone.utc),
            'amount': _number(amount, '实付金额'),
            'volumn': _number(item['productQty'], '升数') if volume_available else Decimal('0'),
            'balance': _number(item['balanceAfTransaction'], '交易后余额') if balance_available else Decimal('0'),
            'org_name': str(item.get('stationName') or '').strip(),
            'gift_name': str(item.get('oilName') or '').strip(),
            'volume_available': volume_available, 'balance_available': balance_available,
        }
        if 'productDetails' in item:
            normalized[key]['platform_data']['productDetails'] = item['productDetails']
    factory = session_factory or SessionLocal
    inserted = updated = matched = 0
    with _import_lock, factory() as db, db.begin():
        links = {r.card_no.strip(): r for r in db.scalars(select(FuelCardLookup)).all()}
        workshops = {r.name: r.id for r in db.scalars(select(Workshop)).all()}
        vehicles = {r.plate_number: r for r in db.scalars(select(Vehicle)).all()}
        existing = {}
        keys = list(normalized)
        for offset in range(0, len(keys), 500):
            existing.update({r.platform_record_id: r for r in db.scalars(select(FuelRecord).where(
                FuelRecord.platform_record_id.in_(keys[offset:offset + 500]))).all()})
        for key, values in normalized.items():
            link = links.get(values['card_asn'])
            vehicle = vehicles.get(values['car_no'])
            values['workshop'], values['workshop_id'] = '', None
            if link:
                values['car_no'] = link.vehicle_no or values['car_no']
                values['workshop'], values['workshop_id'] = link.workshop, workshops.get(link.workshop)
            elif vehicle:
                values['workshop'], values['workshop_id'] = vehicle.org_unit or '', vehicle.workshop_id
            if values['workshop_id'] is not None:
                matched += 1
            record = existing.get(key)
            if record is None:
                record = FuelRecord(platform_record_id=key)
                db.add(record)
                inserted += 1
            else:
                updated += 1
                # 已成功查询的商品明细保留，刷新列表不重复请求。
                if 'productDetails' not in values['platform_data'] and record.platform_data and 'productDetails' in record.platform_data:
                    values['platform_data']['productDetails'] = record.platform_data['productDetails']
            for field, value in values.items():
                setattr(record, field, value)
    return {
        'ok': True, 'platform': 'kunlun', 'record_written': len(normalized),
        'record_inserted': inserted, 'record_updated': updated, 'record_matched': matched,
        'record_missing_volume': sum(not v['volume_available'] for v in normalized.values()),
        'record_missing_card': sum(not v['card_asn'] for v in normalized.values()),
        'date_from': date_from.isoformat(), 'date_to': date_to.isoformat(),
    }


def sync_kunlun_bills(date_from, date_to, on_progress=None, *, session_factory=None, on_batch_ready=None):
    today = datetime.now(ZoneInfo('Asia/Shanghai')).date()
    date_from, date_to = date_from or today.replace(day=1), date_to or today
    if date_from > date_to or (date_to - date_from).days > 366:
        raise RuntimeError('请选择有效日期范围，单次最多查询一年')
    emit = on_progress or (lambda _: None)
    module = _load_script(_script_path())
    totals = {key: 0 for key in ('record_written', 'record_inserted', 'record_updated', 'record_matched',
                               'record_missing_volume', 'record_missing_card')}
    completed = 0
    def save_batch(rows, start, end):
        nonlocal completed
        batch = import_bill_rows(rows, start, end, session_factory=session_factory)
        completed += 1
        for key in totals:
            totals[key] += batch[key]
        emit(f'已同步 {start} 至 {end}，累计 {totals["record_written"]} 条账单，继续查询其余区间…')
        if on_batch_ready:
            on_batch_ready({**batch, 'record_written_total': totals['record_written'], 'completed_windows': completed})
    try:
        fetch_bill_rows(module.load_login_module(), date_from, date_to, emit,
                        max_workers=4, window_days=7, on_batch_ready=save_batch)
    except Exception as exc:
        if completed:
            raise BillPlatformError(f'部分查询未完成：已同步 {completed} 个日期区间、{totals["record_written"]} 条账单；'
                                    '已同步数据保留，请重新查询补齐其余区间') from exc
        raise
    return {'ok': True, 'platform': 'kunlun', **totals, 'date_from': date_from.isoformat(),
            'date_to': date_to.isoformat(), 'completed_windows': completed}
