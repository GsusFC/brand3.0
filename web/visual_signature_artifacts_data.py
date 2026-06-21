"""Path and artifact helpers for the Visual Signature web lab."""

from __future__ import annotations

import os
from hashlib import sha256
from pathlib import Path

from .visual_signature_constants import ARTIFACTS
from .visual_signature_constants import DEFAULT_VISUAL_SIGNATURE_ROOT
HUMAN_REVIEW_SCRIPT_PATH = Path(__file__).resolve().parent / "static" / "visual_signature_human_review.js"


def visual_signature_root() -> Path:
    return Path(os.environ.get("BRAND3_VISUAL_SIGNATURE_ROOT", str(DEFAULT_VISUAL_SIGNATURE_ROOT)))


def visual_signature_human_review_script_version() -> str:
    try:
        return sha256(HUMAN_REVIEW_SCRIPT_PATH.read_bytes()).hexdigest()[:12]
    except OSError:
        return "dev"


def artifact_path(key: str, *, root: Path | None = None) -> Path | None:
    spec = ARTIFACTS.get(key)
    if not spec:
        return None
    root = root or visual_signature_root()
    return root / spec["path"]


def artifact_file_response_payload(key: str) -> tuple[Path, str] | None:
    spec = ARTIFACTS.get(key)
    path = artifact_path(key)
    if not spec or path is None or not path.exists() or not _is_under_root(path):
        return None
    media_type = {
        "json": "application/json",
        "markdown": "text/markdown; charset=utf-8",
        "html": "text/html; charset=utf-8",
    }.get(spec["type"], "text/plain; charset=utf-8")
    return path, media_type


def screenshot_file_response_payload(filename: str) -> tuple[Path, str] | None:
    path = visual_signature_root() / "screenshots" / filename
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        return None
    if not path.exists() or not _is_under_root(path):
        return None
    media_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }[path.suffix.lower()]
    return path, media_type


def _is_under_root(path: Path) -> bool:
    try:
        path.resolve().relative_to(visual_signature_root().resolve())
    except ValueError:
        return False
    return True
