"""Experimental Brand3 lab routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from ..brand3_lab_data import build_perceptual_narrative_comparison_model
from ..templates_env import templates

router = APIRouter()


@router.get("/brand3-lab/perceptual-narrative-comparison")
async def perceptual_narrative_comparison(request: Request):
    return templates.TemplateResponse(
        request,
        "perceptual_narrative_comparison.html.j2",
        {"model": build_perceptual_narrative_comparison_model()},
    )
