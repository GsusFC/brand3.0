"""JSON helpers for the Visual Signature web lab."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else {"items": value}


def pretty_json(payload: dict[str, Any] | None) -> str:
    if payload is None:
        return ""
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def nested(payload: dict[str, Any], key: str, nested_key: str) -> Any:
    value = payload.get(key)
    return value.get(nested_key) if isinstance(value, dict) else None
