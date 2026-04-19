"""GET /_health — lightweight JSON probe for Fly health checks."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..storage import _db_path
from ..workers.queue import get_queue

router = APIRouter()


@router.get("/_health", include_in_schema=False)
async def health() -> JSONResponse:
    stats = get_queue().stats()
    db_status = "ok"
    last_completed: str | None = None
    try:
        with sqlite3.connect(str(_db_path())) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT completed_at FROM web_requests "
                "WHERE status = 'ready' ORDER BY completed_at DESC LIMIT 1"
            ).fetchone()
            last_completed = row["completed_at"] if row else None
    except sqlite3.Error as exc:
        db_status = f"error: {exc}"
    payload = {
        "status": "ok" if db_status == "ok" else "degraded",
        "queue_size": stats.queued,
        "running": stats.running,
        "db": db_status,
        "last_analysis_completed_at": last_completed,
    }
    code = 200 if payload["status"] == "ok" else 503
    return JSONResponse(payload, status_code=code)
