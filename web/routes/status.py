"""GET /r/{token}/status — placeholder in Phase 1."""

from fastapi import APIRouter, Request

from ..templates_env import templates

router = APIRouter()


@router.get("/r/{token}/status")
async def analysis_status(request: Request, token: str):
    return templates.TemplateResponse(
        request,
        "status.html.j2",
        {
            "token": token,
            "brand_slug": "stub",
            "status": "queued",
            "elapsed_seconds": 0,
            "error_message": None,
        },
    )
