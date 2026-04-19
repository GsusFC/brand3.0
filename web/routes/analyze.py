"""POST /analyze — stub for Phase 1. Full flow arrives in Phase 3."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import PlainTextResponse

router = APIRouter()


@router.post("/analyze")
async def analyze(request: Request, url: str = Form(...)):
    return PlainTextResponse(
        "analysis pipeline not yet implemented — arrives in phase 3",
        status_code=501,
    )
