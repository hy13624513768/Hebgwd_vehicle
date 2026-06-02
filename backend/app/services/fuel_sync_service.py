"""从网页触发中国石油油卡数据同步。"""

from __future__ import annotations

import asyncio
import importlib.util
import json
from datetime import date
from pathlib import Path
from typing import AsyncIterator

_sync_lock = asyncio.Lock()


def _load_oil_query_class():
    script = Path(__file__).resolve().parents[2] / "scripts" / "run_query.py"
    spec = importlib.util.spec_from_file_location("oil_run_query", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载油卡同步脚本：{script}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.OilCardBalanceQuery


async def stream_fuel_sync(
    date_from: date | None,
    date_to: date | None,
) -> AsyncIterator[str]:
    """执行油卡同步并以 NDJSON 流式返回进度与结果。"""
    if _sync_lock.locked():
        yield json.dumps(
            {"type": "error", "message": "已有同步任务进行中，请稍后再试"},
            ensure_ascii=False,
        ) + "\n"
        return

    queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()

    def on_progress(message: str) -> None:
        queue.put_nowait({"type": "progress", "message": message})

    async def worker() -> None:
        async with _sync_lock:
            try:
                query_cls = _load_oil_query_class()
                tool = query_cls(
                    date_from=date_from,
                    date_to=date_to,
                    on_progress=on_progress,
                )
                result = await tool.run_sync()
                if result.get("ok"):
                    await queue.put({"type": "done", **result})
                else:
                    await queue.put(
                        {
                            "type": "error",
                            "message": str(result.get("error") or "同步失败"),
                        }
                    )
            except Exception as exc:
                await queue.put({"type": "error", "message": str(exc)})

    task = asyncio.create_task(worker())
    try:
        while True:
            item = await queue.get()
            yield json.dumps(item, ensure_ascii=False) + "\n"
            if item.get("type") in ("done", "error"):
                break
    finally:
        await task
