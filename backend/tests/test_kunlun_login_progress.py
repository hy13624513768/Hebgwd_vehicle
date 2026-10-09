import unittest
from types import SimpleNamespace

from app.services.kunlun_login_progress import ensure_login_with_progress


class LoginProgressTests(unittest.TestCase):
    def module(self, fail=False):
        class KunlunLogin:
            def pre_check(self): pass
            def get_slide_images(self): pass
            def check_slide(self): pass
            def send_sms_code(self): pass
            def login_with_sms(self, code):
                if fail:
                    raise RuntimeError("synthetic login failure")
                return {"access_token": "synthetic-secret-token"}

        class QqMailSmsReader:
            def __init__(self): self.calls = 0
            def fetch_latest_code(self, after_time=None):
                self.calls += 1
                return "synthetic-secret-code" if self.calls == 2 else None
            def wait_for_code(self):
                self.fetch_latest_code()
                return self.fetch_latest_code()

        def login():
            client = KunlunLogin()
            client.pre_check()
            client.get_slide_images()
            client.check_slide()
            client.send_sms_code()
            return client.login_with_sms(QqMailSmsReader().wait_for_code())

        return SimpleNamespace(KunlunLogin=KunlunLogin, QqMailSmsReader=QqMailSmsReader, ensure_login=login)

    def test_real_stages_and_poll_attempts_without_secret_contents(self):
        module = self.module()
        original = module.KunlunLogin.send_sms_code
        events = []
        token = ensure_login_with_progress(module, events.append)
        text = "\n".join(events)
        self.assertEqual(token["access_token"], "synthetic-secret-token")
        for stage in ("平台登录校验", "滑块验证", "发送短信验证码", "等待验证码", "第 2 次", "提交登录验证", "登录验证完成"):
            self.assertIn(stage, text)
        self.assertNotIn("synthetic-secret", text)
        self.assertIs(module.KunlunLogin.send_sms_code, original)

    def test_cached_session_does_not_claim_to_wait_for_code(self):
        module = SimpleNamespace(ensure_login=lambda: {"access_token": "cached"})
        events = []
        ensure_login_with_progress(module, events.append)
        self.assertEqual(len(events), 2)
        self.assertNotIn("验证码", "\n".join(events))

    def test_methods_restored_when_login_fails(self):
        module = self.module(fail=True)
        original = module.KunlunLogin.login_with_sms
        original_poll = module.QqMailSmsReader.fetch_latest_code
        with self.assertRaises(RuntimeError):
            ensure_login_with_progress(module)
        self.assertIs(module.KunlunLogin.login_with_sms, original)
        self.assertIs(module.QqMailSmsReader.fetch_latest_code, original_poll)


if __name__ == "__main__":
    unittest.main()
