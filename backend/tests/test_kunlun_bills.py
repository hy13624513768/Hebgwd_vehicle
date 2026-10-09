"""账单同步回归：内存库和模拟平台，不读取真实账号。"""
import os
os.environ.update(DATABASE_URL='sqlite://', ENVIRONMENT='test', DEMO_SEEDING_ENABLED='false')

import unittest
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

import app.models
from app.db.base import Base
from app.models.fuel import FuelRecord, FuelCardLookup
from app.models.workshop import Workshop
from app.schemas.fuel import FuelSyncRequest
from app.services.kunlun_bill_service import fetch_bill_rows, import_bill_rows, _post, BillPlatformError


class KunlunBillTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine)
        self.start, self.end = date(2026, 10, 1), date(2026, 10, 8)
        self.row = dict(platform_record_id='kunlun:test', ewalletCardNo='CARD', licensePlate='CAR',
                        orderTime='2026-10-07 00:30:00', productQty='50', oilReceivedAmount='390.50',
                        actualPayTotalAmount='400', balanceAfTransaction='100', stationName='Test', oilName='柴油')

    def tearDown(self):
        self.engine.dispose()

    def test_repeat_sync_updates_without_duplicates_and_maps_workshop(self):
        with self.sessions.begin() as db:
            db.add(Workshop(name='Test workshop'))
            db.add(FuelCardLookup(card_no='CARD', workshop='Test workshop', vehicle_no='MAPPED'))
        first = import_bill_rows([self.row], self.start, self.end, session_factory=self.sessions)
        second = import_bill_rows([dict(self.row, oilReceivedAmount='399')], self.start, self.end, session_factory=self.sessions)
        self.assertEqual(first['record_inserted'], 1)
        self.assertEqual(second['record_updated'], 1)
        with self.sessions() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(FuelRecord)), 1)
            row = db.scalar(select(FuelRecord))
            self.assertEqual(row.car_no, 'MAPPED')
            self.assertIsNotNone(row.workshop_id)
            self.assertEqual(row.amount, Decimal('399'))
            self.assertEqual(row.occur_time, datetime(2026, 10, 6, 16, 30))

    def test_invalid_payload_preserves_previous_rows(self):
        import_bill_rows([self.row], self.start, self.end, session_factory=self.sessions)
        with self.assertRaises(RuntimeError):
            import_bill_rows([dict(self.row, oilReceivedAmount='10'),
                              dict(self.row, platform_record_id='other', oilReceivedAmount='NaN')],
                             self.start, self.end, session_factory=self.sessions)
        with self.sessions() as db:
            self.assertEqual(db.scalar(select(FuelRecord)).amount, Decimal('390.50'))

    def test_platform_business_fields_and_product_cache_are_preserved(self):
        item = dict(self.row, orderNo='ORDER', driverName='Test driver', access_token='must-not-store',
                    productDetails=[{'productName': 'Diesel', 'productQty': '50', 'unit': 'L'}])
        import_bill_rows([item], self.start, self.end, session_factory=self.sessions)
        import_bill_rows([dict(self.row, orderNo='ORDER', driverName='Updated driver')],
                         self.start, self.end, session_factory=self.sessions)
        with self.sessions() as db:
            row = db.scalar(select(FuelRecord))
            self.assertEqual(row.platform_data['orderNo'], 'ORDER')
            self.assertEqual(row.platform_data['driverName'], 'Updated driver')
            self.assertEqual(row.platform_data['productDetails'][0]['unit'], 'L')
            self.assertNotIn('access_token', row.platform_data)

    def test_empty_result_preserves_history(self):
        import_bill_rows([self.row], self.start, self.end, session_factory=self.sessions)
        result = import_bill_rows([], self.start, self.end, session_factory=self.sessions)
        self.assertEqual(result['record_written'], 0)
        with self.sessions() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(FuelRecord)), 1)

    def test_missing_values_are_explicit_and_amount_falls_back(self):
        result = import_bill_rows([dict(self.row, productQty='', balanceAfTransaction='',
                                       oilReceivedAmount=None, ewalletCardNo='')],
                                  self.start, self.end, session_factory=self.sessions)
        self.assertEqual(result['record_missing_volume'], 1)
        self.assertEqual(result['record_missing_card'], 1)
        with self.sessions() as db:
            row = db.scalar(select(FuelRecord))
            self.assertFalse(row.volume_available)
            self.assertFalse(row.balance_available)
            self.assertEqual(row.amount, Decimal('400'))

    def test_incomplete_or_duplicate_pages_are_rejected(self):
        client = SimpleNamespace(_headers=lambda: {}, session=Mock())
        login = SimpleNamespace(ensure_login=lambda: {'access_token': 'synthetic'},
                                KunlunLogin=lambda *_: client, BASE='https://synthetic.invalid')
        account = {'mainAccountNo': 'MAIN', 'enterpriseNo': 'ORG'}
        row = dict(self.row, orderNo='ORDER')
        for final_rows in ([], [row]):
            with self.subTest(final_rows=bool(final_rows)), patch('app.services.kunlun_bill_service._post', side_effect=[
                    [account], {'totalRows': 2, 'rows': [row]}, {'totalRows': 2, 'rows': final_rows}]):
                with self.assertRaises(RuntimeError):
                    fetch_bill_rows(login, self.start, self.end)
        self.assertTrue(client.session.close.called)

    def test_date_validation(self):
        with self.assertRaises(ValueError):
            FuelSyncRequest(target='bills', date_from=self.end, date_to=self.start)
        with self.assertRaises(ValueError):
            FuelSyncRequest(target='bills', date_from=date(2024, 1, 1), date_to=self.end)

    def test_windowing_and_detail_fallback(self):
        client = SimpleNamespace(_headers=lambda: {}, session=Mock())
        login = SimpleNamespace(ensure_login=lambda: {'access_token': 'synthetic'},
                                KunlunLogin=lambda *_: client, BASE='https://synthetic.invalid')
        calls = []
        def post(_client, _base, _headers, path, body):
            calls.append((path, body))
            if path.endswith('listMainAccount'):
                return [{'mainAccountNo': 'MAIN', 'enterpriseNo': 'ORG'}]
            if path.endswith('detail'):
                return [{'unit': 'L', 'productQty': '50'}]
            if body['businessDay'][0] == '2026-10-01':
                return {'totalRows': 1, 'rows': [dict(self.row, orderNo='ORDER', productQty='')]}
            return {'totalRows': 0, 'rows': []}
        with patch('app.services.kunlun_bill_service._post', side_effect=post):
            rows = fetch_bill_rows(login, self.start, date(2026, 11, 2))
        self.assertEqual(rows[0]['productQty'], Decimal('50'))
        self.assertEqual(rows[0]['productDetails'][0]['productQty'], '50')
        windows = [body['businessDay'] for path, body in calls if path.endswith('/page')]
        self.assertEqual(sorted(windows), [['2026-10-01', '2026-10-28'], ['2026-10-29', '2026-11-02']])

    def test_platform_retry_and_specific_failure(self):
        bad = Mock(status_code=500)
        good = Mock(status_code=200)
        good.json.return_value = {'success': True, 'data': {'rows': []}}
        client = SimpleNamespace(session=Mock())
        client.session.post.side_effect = [bad, good]
        with patch('app.services.kunlun_bill_service.time.sleep'):
            self.assertEqual(_post(client, 'https://synthetic.invalid', {}, 'consumptionRecord/page', {}), {'rows': []})
        self.assertEqual(client.session.post.call_count, 2)
        client.session.post.side_effect = [bad, bad, bad]
        with patch('app.services.kunlun_bill_service.time.sleep'), self.assertRaises(BillPlatformError) as caught:
            _post(client, 'https://synthetic.invalid', {}, 'consumptionRecord/page',
                  {'businessDay': ['2026-09-01', '2026-10-08'], 'pageNum': 2})
        self.assertIn('2026-09-01', str(caught.exception))
        self.assertIn('HTTP 500', str(caught.exception))

    def test_failed_large_range_is_requeried_without_partial_rows(self):
        client = SimpleNamespace(_headers=lambda: {}, session=Mock())
        login = SimpleNamespace(ensure_login=lambda: {'access_token': 'synthetic'},
                                KunlunLogin=lambda *_: client, BASE='https://synthetic.invalid')
        calls = []
        def post(_client, _base, _headers, path, body):
            if path.endswith('listMainAccount'):
                return [{'mainAccountNo': 'MAIN', 'enterpriseNo': 'ORG'}]
            calls.append(body['businessDay'])
            if body['businessDay'] == ['2026-10-01', '2026-10-08']:
                if body['pageNum'] == 1:
                    return {'totalRows': 2, 'rows': [dict(self.row, orderNo='ORDER')]}
                raise BillPlatformError('synthetic', 500)
            if body['businessDay'][0] == '2026-10-01':
                return {'totalRows': 1, 'rows': [dict(self.row, orderNo='ORDER')]}
            return {'totalRows': 0, 'rows': []}
        with patch('app.services.kunlun_bill_service._post', side_effect=post):
            rows = fetch_bill_rows(login, self.start, self.end)
        self.assertEqual(len(rows), 1)
        self.assertIn(['2026-10-01', '2026-10-04'], calls)
        self.assertIn(['2026-10-05', '2026-10-08'], calls)

    def test_four_independent_connections_login_once_and_publish_batches(self):
        from threading import Barrier, Lock
        barrier, lock = Barrier(4), Lock()
        active = peak = 0
        clients, batches = [], []
        def make_client(*_):
            client = SimpleNamespace(_headers=lambda: {}, session=Mock())
            clients.append(client)
            return client
        login = SimpleNamespace(ensure_login=Mock(return_value={'access_token': 'synthetic'}),
                                KunlunLogin=make_client, BASE='https://synthetic.invalid')
        def post(client, base, headers, path, body):
            nonlocal active, peak
            if path.endswith('listMainAccount'):
                return [{'mainAccountNo': 'MAIN', 'enterpriseNo': 'ORG'}]
            with lock:
                active += 1
                peak = max(peak, active)
            barrier.wait(timeout=3)
            with lock:
                active -= 1
            return {'totalRows': 1, 'rows': [dict(self.row, orderNo=body['businessDay'][0])]}
        with patch('app.services.kunlun_bill_service._post', side_effect=post):
            rows = fetch_bill_rows(login, self.start, date(2026, 10, 28), window_days=7,
                                   on_batch_ready=lambda rows, start, end: batches.append((rows, start, end)))
        self.assertEqual(peak, 4)
        self.assertEqual(len(rows), 4)
        self.assertEqual(len(batches), 4)
        self.assertEqual(len({id(c.session) for c in clients}), 5)
        self.assertTrue(all(c.session.close.called for c in clients))
        login.ensure_login.assert_called_once()

    def test_progressive_commit_survives_later_window_failure(self):
        from app.services.kunlun_bill_service import sync_kunlun_bills
        callbacks = []
        def fetch(login, start, end, emit, **kwargs):
            kwargs['on_batch_ready']([self.row], self.start, self.end)
            raise BillPlatformError('synthetic', 500)
        module = SimpleNamespace(load_login_module=lambda: None)
        with patch('app.services.kunlun_bill_service._script_path'), \
             patch('app.services.kunlun_bill_service._load_script', return_value=module), \
             patch('app.services.kunlun_bill_service.fetch_bill_rows', side_effect=fetch), \
             self.assertRaises(BillPlatformError) as caught:
            sync_kunlun_bills(self.start, self.end, session_factory=self.sessions,
                              on_batch_ready=callbacks.append)
        self.assertIn('部分查询未完成', str(caught.exception))
        self.assertEqual(callbacks[0]['record_written_total'], 1)
        with self.sessions() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(FuelRecord)), 1)


if __name__ == '__main__':
    unittest.main()
