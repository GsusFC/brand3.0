"""FastAPI entrypoint for the Brand3 web app."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routes import analyze, brand, index, report, reports_list, status, takedown, team
from .templates_env import templates

log = logging.getLogger("brand3.web")

_STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 3 will start the AnalysisQueue worker here.
    log.info(
        "brand3.web starting — env=%s base_url=%s",
        settings.environment,
        settings.base_url,
    )
    yield
    log.info("brand3.web shutting down")


app = FastAPI(
    title="Brand3",
    description="Public brand health scorer — FLOC",
    version="0.1.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

for module in (index, analyze, status, report, reports_list, brand, team, takedown):
    app.include_router(module.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> HTMLResponse:
    if exc.status_code == 404:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": request.url.path},
            status_code=404,
        )
    return templates.TemplateResponse(
        request,
        "error.html.j2",
        {
            "status_code": exc.status_code,
            "error": exc.detail or "request failed",
        },
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> HTMLResponse:
    log.exception("unhandled error on %s", request.url.path)
    return templates.TemplateResponse(
        request,
        "error.html.j2",
        {
            "status_code": 500,
            "error": "internal server error",
        },
        status_code=500,
    )
