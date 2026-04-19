"""GET /brand/{domain} — per-brand history. Populated in Phase 4."""

from fastapi import APIRouter, Request

from ..templates_env import templates

router = APIRouter()


@router.get("/brand/{domain}")
async def brand_history(request: Request, domain: str):
    return templates.TemplateResponse(
        request,
        "brand_history.html.j2",
        {
            "domain": domain,
            "analyses": [],
        },
    )
