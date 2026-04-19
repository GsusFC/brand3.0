"""GET /team/unlock — sets the signed team cookie when the token matches."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from ..config import settings
from ..middleware.team_cookie import create_serializer, set_team_cookie

router = APIRouter()


@router.get("/team/unlock")
async def team_unlock(request: Request, token: str | None = None):
    expected = settings.team_token
    if not expected:
        raise HTTPException(status_code=503, detail="team access not configured")
    if token != expected:
        raise HTTPException(status_code=403, detail="invalid team token")
    response = RedirectResponse("/", status_code=303)
    set_team_cookie(response, create_serializer(settings.cookie_secret))
    return response
