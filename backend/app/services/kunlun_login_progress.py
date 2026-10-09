"""将本地登录脚本的真实阶段转成页面进度，不读取或输出验证码内容。"""
from functools import wraps


def ensure_login_with_progress(login_module, on_progress=None):
    emit = on_progress or (lambda _: None)
    patched = []
    attempts = 0

    def hook(class_name, method_name, before, after=None):
        cls = getattr(login_module, class_name, None)
        original = getattr(cls, method_name, None)
        if not isinstance(cls, type) or not callable(original):
            return

        @wraps(original)
        def wrapped(*args, **kwargs):
            before()
            result = original(*args, **kwargs)
            if after is not None:
                after(result)
            return result

        setattr(cls, method_name, wrapped)
        patched.append((cls, method_name, original))

    def poll():
        nonlocal attempts
        attempts += 1
        emit(f"等待验证码：正在第 {attempts} 次检查短信转发邮件…")

    def received(result):
        if result:
            emit("已获取验证码，正在准备登录验证…")
        else:
            emit("尚未收到验证码邮件，等待短信转发后自动重试…")

    emit("正在检查昆仑平台登录状态…")
    try:
        hook("KunlunLogin", "pre_check", lambda: emit("登录已失效，正在进行平台登录校验…"))
        hook("KunlunLogin", "get_slide_images", lambda: emit("正在获取图形验证码并完成滑块验证…"))
        hook("KunlunLogin", "check_slide", lambda: emit("正在提交滑块验证码校验…"))
        hook("KunlunLogin", "send_sms_code", lambda: emit("正在向平台请求发送短信验证码…"),
             lambda _: emit("验证码请求已完成，正在等待验证码送达…"))
        hook("QqMailSmsReader", "wait_for_code", lambda: emit("等待验证码：系统正在自动读取短信转发邮件，请稍候…"))
        hook("QqMailSmsReader", "fetch_latest_code", poll, received)
        hook("KunlunLogin", "login_with_sms", lambda: emit("已获取验证码，正在提交登录验证…"))
        token = login_module.ensure_login()
        emit("登录验证完成，正在获取平台账户信息…")
        return token
    finally:
        for cls, name, original in reversed(patched):
            setattr(cls, name, original)
