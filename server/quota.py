"""일 N건 한도 (SQLite). 날짜는 KST 기준, 자정에 초기화.

Render 무료 플랜은 재시작 시 파일이 사라진다 → 그때 카운트도 초기화 (소실 허용).
"""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, time, timedelta, timezone

KST = timezone(timedelta(hours=9))


class Quota:
    def __init__(self, path: str, limit: int, now=lambda: datetime.now(KST)):
        self.path, self.limit, self._now = path, limit, now
        self._lock = threading.Lock()
        with self._conn() as c:
            c.execute("CREATE TABLE IF NOT EXISTS usage (day TEXT, client TEXT, used INTEGER, PRIMARY KEY (day, client))")

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=5)

    def _day(self) -> str:
        return self._now().date().isoformat()

    def _info(self, used: int) -> dict:
        tomorrow = self._now().date() + timedelta(days=1)
        reset_at = datetime.combine(tomorrow, time(0), KST)
        return {"used": used, "limit": self.limit, "reset_at": reset_at.isoformat()}

    def status(self, client: str) -> dict:
        with self._conn() as c:
            row = c.execute("SELECT used FROM usage WHERE day=? AND client=?", (self._day(), client)).fetchone()
        return self._info(row[0] if row else 0)

    def exceeded(self, client: str) -> bool:
        return self.status(client)["used"] >= self.limit

    def consume(self, client: str) -> dict:
        """1건 차감 후 현재 상태."""
        day = self._day()
        with self._lock, self._conn() as c:
            c.execute(
                "INSERT INTO usage (day, client, used) VALUES (?, ?, 1) "
                "ON CONFLICT (day, client) DO UPDATE SET used = used + 1",
                (day, client),
            )
            c.execute("DELETE FROM usage WHERE day < ?", (day,))
            used = c.execute("SELECT used FROM usage WHERE day=? AND client=?", (day, client)).fetchone()[0]
        return self._info(used)
