"""GET /r/{token} — returns the rendered HTML report. Stubbed in Phase 1."""

from fastapi import APIRouter, Request

from ..templates_env import templates

router = APIRouter()


@router.get("/r/{token}")
async def report(request: Request, token: str):
    return templates.TemplateResponse(
        request,
        "not_found.html.j2",
        {"resource": f"report {token}"},
        status_code=404,
    )
