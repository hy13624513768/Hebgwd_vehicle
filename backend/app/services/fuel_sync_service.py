"""同步在线程中执行，进度流不阻塞 API，客户端断开不取消已开始的写入。"""
import asyncio
import json
import logging
from threading import Lock

_sync_lock = Lock()
logger = logging.getLogger(__name__)


async def stream_fuel_sync(date_from=None, date_to=None, user_id=None):
    if not _sync_lock.acquire(blocking=False):
        yield json.dumps({"type": "error", "message": "已有同步任务进行中，请稍后再试"}, ensure_ascii=False) + "\n"
        return
    loop = asyncio.get_running_loop()
    queue = asyncio.Queue()

    def publish(item):
        if not loop.is_closed():
            loop.call_soon_threadsafe(queue.put_nowait, item)

    def worker():
        success = False
        try:
            from app.services.kunlun_balance_service import sync_kunlun_balances
            result = sync_kunlun_balances(
                on_progress=lambda message: publish({"type": "progress", "message": message})
            )
            success = bool(result.get("ok"))
            final = {"type": "done", **result} if success else {"type": "error", "message": result.get("error") or "同步失败"}
        except Exception:
            logger.exception("昆仑油卡余额同步失败")
            final = {"type": "error", "message": "余额同步未完成，原有数据已保留；请检查本地昆仑脚本配置或后台日志"}
        finally:
            try:
                from app.services.fuel_sync_stats_service import record_fuel_sync_log
                record_fuel_sync_log(user_id, success=success)
            except Exception:
                logger.exception("保存同步日志失败")
            _sync_lock.release()
        publish(final)

    future = loop.run_in_executor(None, worker)
    try:
        while True:
            item = await queue.get()
            yield json.dumps(item, ensure_ascii=False) + "\n"
            if item["type"] in {"done", "error"}:
                break
    finally:
        await asyncio.shield(future)
