"""GET / — landing form + latest analyses list."""

from fastapi import APIRouter, Request

from ..templates_env import templates

router = APIRouter()


@router.get("/")
async def index(request: Request):
    # REVIEW: latest_analyses populated in Phase 4.
    return templates.TemplateResponse(
        request,
        "index.html.j2",
        {"latest_analyses": []},
    )
