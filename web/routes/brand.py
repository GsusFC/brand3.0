"""GET /brand/{domain} — per-brand history + ASCII evolution chart."""

from fastapi import APIRouter, Request

from ..presenters import enrich
from ..storage import list_brand_history
from ..templates_env import templates

router = APIRouter()


@router.get("/brand/{domain}")
async def brand_history(request: Request, domain: str):
    analyses = enrich(list_brand_history(domain))
    return templates.TemplateResponse(
        request,
        "brand_history.html.j2",
        {
            "domain": domain,
            "analyses": analyses,
        },
    )
