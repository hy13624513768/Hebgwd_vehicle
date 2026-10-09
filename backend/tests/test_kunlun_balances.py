"""并发余额查询的连接隔离与分页完整性测试。"""
import os
os.environ.update(DATABASE_URL='sqlite://', ENVIRONMENT='test', DEMO_SEEDING_ENABLED='false')
import unittest
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import Mock, patch
from app.services.kunlun_balance_service import fetch_staff_balances


class BalanceFetchTests(unittest.TestCase):
    def login(self):
        clients = []
        def create(*_):
            client = SimpleNamespace(_headers=lambda: {}, session=Mock())
            clients.append(client)
            return client
        login = SimpleNamespace(ensure_login=Mock(return_value={'access_token': 'synthetic'}),
                                KunlunLogin=create, BASE='https://synthetic.invalid')
        return login, clients

    def page(self, total, number):
        start = (number - 1) * 100
        return {'totalRows': total, 'rows': [{'cardNo': str(i), 'availableAmount': '100'}
                                           for i in range(start, min(start + 100, total))]}

    def test_first_two_pages_parallel_and_login_once(self):
        login, clients = self.login()
        barrier = Barrier(2)
        def post(client, base, headers, path, body):
            if path.endswith('listMainAccount'):
                return [{'enterpriseAccountNo': 'MAIN'}]
            barrier.wait(timeout=3)
            return self.page(176, body['pageNum'])
        with patch('app.services.kunlun_balance_service._balance_post', side_effect=post):
            rows = fetch_staff_balances(login, str)
        self.assertEqual(len(rows), 176)
        self.assertEqual(len({id(c.session) for c in clients}), 3)
        self.assertTrue(all(c.session.close.called for c in clients))
        login.ensure_login.assert_called_once()

    def test_remaining_pages_follow_actual_total(self):
        login, clients = self.login()
        requested = []
        def post(client, base, headers, path, body):
            if path.endswith('listMainAccount'):
                return [{'enterpriseAccountNo': 'MAIN'}]
            requested.append(body['pageNum'])
            return self.page(355, body['pageNum'])
        with patch('app.services.kunlun_balance_service._balance_post', side_effect=post):
            rows = fetch_staff_balances(login, str)
        self.assertEqual(len(rows), 355)
        self.assertEqual(sorted(requested), [1, 2, 3, 4])
        self.assertEqual(rows[0]['卡号'], '0')
        self.assertEqual(rows[-1]['卡号'], '354')

    def test_unused_prefetch_error_does_not_fail_single_page(self):
        login, clients = self.login()
        def post(client, base, headers, path, body):
            if path.endswith('listMainAccount'):
                return [{'enterpriseAccountNo': 'MAIN'}]
            if body['pageNum'] == 2:
                raise RuntimeError('unused out of range page')
            return self.page(10, 1)
        with patch('app.services.kunlun_balance_service._balance_post', side_effect=post):
            self.assertEqual(len(fetch_staff_balances(login, str)), 10)
        self.assertTrue(all(c.session.close.called for c in clients))

    def test_incomplete_changed_or_duplicate_page_is_rejected(self):
        for mode in ['incomplete', 'changed', 'duplicate']:
            with self.subTest(mode=mode):
                login, _ = self.login()
                def post(client, base, headers, path, body):
                    if path.endswith('listMainAccount'):
                        return [{'enterpriseAccountNo': 'MAIN'}]
                    page = self.page(176, body['pageNum'])
                    if body['pageNum'] == 2:
                        if mode == 'incomplete':
                            page['rows'].pop()
                        elif mode == 'changed':
                            page['totalRows'] = 175
                        else:
                            page['rows'][0]['cardNo'] = '0'
                    return page
                with patch('app.services.kunlun_balance_service._balance_post', side_effect=post):
                    with self.assertRaises(RuntimeError):
                        fetch_staff_balances(login, str)
