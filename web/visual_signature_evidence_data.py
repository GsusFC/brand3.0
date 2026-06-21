"""Evidence-model helpers for the Visual Signature web lab."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .visual_signature_artifacts_data import _is_under_root
from .visual_signature_artifacts_data import visual_signature_root
from .visual_signature_json_data import as_list
from .visual_signature_json_data import load_json
from .visual_signature_json_data import nested


def visual_evidence_model() -> dict[str, Any]:
    root = visual_signature_root()
    screenshots_dir = root / "screenshots"
    capture_manifest = load_json(root / "screenshots" / "capture_manifest.json") or {}
    dismissal_audit = load_json(root / "screenshots" / "dismissal_audit.json") or {}
    rows = as_list(capture_manifest.get("results"))
    audit_rows = {
        str(row.get("brand_name") or "").lower(): row
        for row in as_list(dismissal_audit.get("results"))
        if isinstance(row, dict)
    }

    items = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        brand_name = str(row.get("brand_name") or "Unknown brand")
        audit = audit_rows.get(brand_name.lower()) or {}
        variants = _screenshot_variants(row, screenshots_dir=screenshots_dir)
        items.append(
            {
                "brand_name": brand_name,
                "capture_id": _slugify(brand_name),
                "website_url": row.get("website_url") or row.get("page_url") or "",
                "capture_status": row.get("status") or "available",
                "obstruction_type": nested(row, "before_obstruction", "type") or "unknown",
                "obstruction_severity": nested(row, "before_obstruction", "severity") or "unknown",
                "dismissal_attempted": bool(row.get("dismissal_attempted")),
                "dismissal_successful": bool(row.get("dismissal_successful")),
                "perceptual_state": row.get("perceptual_state") or audit.get("perceptual_state") or "evidence_record",
                "evidence_notes": as_list(row.get("evidence_integrity_notes"))[:4],
                "variants": variants,
            }
        )

    if not items and screenshots_dir.exists():
        grouped: dict[str, dict[str, Any]] = {}
        for path in sorted(screenshots_dir.glob("*")):
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                continue
            brand, label = _variant_from_filename(path)
            grouped.setdefault(
                brand,
                {
                    "brand_name": brand.replace("-", " ").title(),
                    "capture_id": brand,
                    "website_url": "",
                    "capture_status": "available",
                    "obstruction_type": "unknown",
                    "obstruction_severity": "unknown",
                    "dismissal_attempted": False,
                    "dismissal_successful": False,
                    "perceptual_state": "evidence_record",
                    "evidence_notes": [],
                    "variants": [],
                },
            )["variants"].append(_screenshot_variant_payload(label, path))
        items = list(grouped.values())

    variant_counts = {
        "raw viewport": sum(1 for item in items for variant in item["variants"] if variant["label"] == "raw viewport" and variant["exists"]),
        "clean attempt": sum(1 for item in items for variant in item["variants"] if variant["label"] == "clean attempt" and variant["exists"]),
        "full page": sum(1 for item in items for variant in item["variants"] if variant["label"] == "full page" and variant["exists"]),
    }
    return {
        "summary": {
            "capture_count": len(items),
            "raw_viewport_count": variant_counts["raw viewport"],
            "clean_attempt_count": variant_counts["clean attempt"],
            "full_page_count": variant_counts["full page"],
        },
        "items": items,
    }


def _related_variant_payload(variant: dict[str, Any], selected_filename: str) -> dict[str, Any]:
    payload = dict(variant)
    payload["is_current"] = payload.get("filename") == selected_filename
    return payload


def _find_manifest_row(payload: dict[str, Any], brand_name: str) -> dict[str, Any] | None:
    target = brand_name.lower()
    for row in as_list(payload.get("results")):
        if isinstance(row, dict) and str(row.get("brand_name") or "").lower() == target:
            return row
    return None


def _slugify(value: str) -> str:
    normalized = "".join(char.lower() if char.isalnum() else "-" for char in value)
    return "-".join(part for part in normalized.split("-") if part)


def _screenshot_variants(row: dict[str, Any], *, screenshots_dir: Path) -> list[dict[str, Any]]:
    brand_slug = _slugify(str(row.get("brand_name") or ""))
    candidates = [
        ("raw viewport", row.get("raw_screenshot_path") or row.get("screenshot_path") or screenshots_dir / f"{brand_slug}.png"),
        ("clean attempt", row.get("clean_attempt_screenshot_path") or screenshots_dir / f"{brand_slug}.clean-attempt.png"),
        ("full page", row.get("secondary_screenshot_path") or screenshots_dir / f"{brand_slug}.full-page.png"),
    ]
    return [_screenshot_variant_payload(label, Path(path)) for label, path in candidates if path]


def _screenshot_variant_payload(label: str, path: Path) -> dict[str, Any]:
    resolved = path if path.is_absolute() else (visual_signature_root() / path)
    exists = resolved.exists() and _is_under_root(resolved)
    filename = resolved.name
    return {
        "label": label,
        "exists": exists,
        "filename": filename,
        "path": str(resolved),
        "href": f"/visual-signature/screenshots/{filename}",
        "preview_href": f"/visual-signature/screenshots/{filename}/preview",
        "alt": f"{label} screenshot: {filename}",
    }


def _variant_from_filename(path: Path) -> tuple[str, str]:
    name = path.name
    stem = path.stem
    if stem.endswith(".clean-attempt"):
        return stem.removesuffix(".clean-attempt"), "clean attempt"
    if stem.endswith(".full-page"):
        return stem.removesuffix(".full-page"), "full page"
    return stem, "raw viewport"
