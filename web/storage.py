"""Thin SQLite access for the `web_requests` table.

Opens its own connection per call — SQLite in WAL mode handles this fine and
we avoid threading the engine's SQLiteStore into middleware. Writes are rare
and short-lived, reads are bounded by a handful of queries per request.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from src.config import BRAND3_DB_PATH
from src.storage.sqlite_store import SQLiteStore


def _db_path() -> Path:
    return Path(BRAND3_DB_PATH)


def ensure_schema() -> None:
    """Apply engine schema + file migrations. Call once on startup."""
    store = SQLiteStore(str(_db_path()))
    store.close()


@contextmanager
def _connect():
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def count_recent_analyses_for_ip(ip: str, hours: int = 24) -> int:
    """How many analyses this IP requested within the last `hours`."""
    if not ip:
        return 0
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM web_requests
            WHERE requester_ip = ?
              AND created_at > datetime('now', ?)
            """,
            (ip, f"-{hours} hours"),
        )
        row = cur.fetchone()
    return int(row["c"]) if row else 0
