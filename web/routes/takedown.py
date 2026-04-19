"""GET /takedown — static page with mailto for manual takedown."""

from fastapi import APIRouter, Request

from ..templates_env import templates

router = APIRouter()


@router.get("/takedown")
async def takedown(request: Request, domain: str | None = None):
    return templates.TemplateResponse(
        request,
        "takedown.html.j2",
        {"domain": domain or ""},
    )
