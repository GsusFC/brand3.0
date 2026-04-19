"""GET /r/{token}/status — polling page for in-flight analyses."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from ..storage import get_request
from ..templates_env import templates

router = APIRouter()


@router.get("/r/{token}/status")
async def analysis_status(request: Request, token: str):
    row = get_request(token)
    if row is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"request {token}"},
            status_code=404,
        )
    if row["status"] == "ready":
        return RedirectResponse(f"/r/{token}", status_code=303)

    return templates.TemplateResponse(
        request,
        "status.html.j2",
        {
            "token": token,
            "brand_slug": row["brand_slug"],
            "status": row["status"],
            "elapsed_seconds": _elapsed(row["started_at"]),
            "error_message": row["error_message"],
        },
    )


def _elapsed(started_at: str | None) -> int:
    if not started_at:
        return 0
    try:
        dt = datetime.fromisoformat(started_at.replace(" ", "T"))
    except ValueError:
        return 0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0, int((datetime.now(timezone.utc) - dt).total_seconds()))
