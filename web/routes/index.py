"""GET / — landing form + latest 10 public analyses."""

from fastapi import APIRouter, Request

from ..presenters import enrich
from ..storage import list_latest_public
from ..templates_env import templates

router = APIRouter()


@router.get("/")
async def index(request: Request):
    rows = enrich(list_latest_public(limit=10))
    return templates.TemplateResponse(
        request,
        "index.html.j2",
        {"latest_analyses": rows},
    )
