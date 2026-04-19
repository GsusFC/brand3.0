"""GET /reports — public observatory listing. Populated in Phase 4."""

from fastapi import APIRouter, Request

from ..templates_env import templates

router = APIRouter()


@router.get("/reports")
async def reports_list(
    request: Request,
    q: str | None = None,
    sort: str = "newest",
    page: int = 1,
):
    return templates.TemplateResponse(
        request,
        "reports_list.html.j2",
        {
            "rows": [],
            "query": q or "",
            "sort": sort,
            "page": page,
            "has_prev": False,
            "has_next": False,
        },
    )
