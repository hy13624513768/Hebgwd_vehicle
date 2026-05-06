from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass
class _SliderRecord:
    created_at: datetime
    completed: bool = False


class SliderSessionStore:
    """内存滑块会话：与原页面“先完成滑块再登录”一致，会话一次性使用。"""

    def __init__(self, ttl_minutes: int = 10) -> None:
        self._ttl = timedelta(minutes=ttl_minutes)
        self._lock = threading.Lock()
        self._sessions: dict[str, _SliderRecord] = {}

    def start(self) -> str:
        sid = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        with self._lock:
            self._purge_unlocked(now)
            self._sessions[sid] = _SliderRecord(created_at=now, completed=False)
        return sid

    def complete(self, session_id: str) -> bool:
        now = datetime.now(timezone.utc)
        with self._lock:
            self._purge_unlocked(now)
            rec = self._sessions.get(session_id)
            if not rec:
                return False
            if now - rec.created_at > self._ttl:
                del self._sessions[session_id]
                return False
            rec.completed = True
            return True

    def is_ready(self, session_id: str) -> bool:
        """滑块已完成且未过期（允许多次尝试登录，与原页面一致）。"""
        now = datetime.now(timezone.utc)
        with self._lock:
            self._purge_unlocked(now)
            rec = self._sessions.get(session_id)
            if not rec:
                return False
            if now - rec.created_at > self._ttl:
                del self._sessions[session_id]
                return False
            return rec.completed

    def consume(self, session_id: str) -> bool:
        """登录成功后移除会话，防止 token 复用。"""
        now = datetime.now(timezone.utc)
        with self._lock:
            self._purge_unlocked(now)
            rec = self._sessions.pop(session_id, None)
            if not rec:
                return False
            if now - rec.created_at > self._ttl:
                return False
            return rec.completed

    def _purge_unlocked(self, now: datetime) -> None:
        expired = [k for k, v in self._sessions.items() if now - v.created_at > self._ttl]
        for k in expired:
            self._sessions.pop(k, None)


slider_store = SliderSessionStore()
