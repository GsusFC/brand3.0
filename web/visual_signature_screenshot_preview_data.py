"""Screenshot preview builders for the Visual Signature web lab."""

from __future__ import annotations

from typing import Any

from .visual_signature_artifacts_data import screenshot_file_response_payload
from .visual_signature_artifacts_data import visual_signature_root
from .visual_signature_display_data import visual_signature_nav
from .visual_signature_evidence_data import _find_manifest_row
from .visual_signature_evidence_data import _related_variant_payload
from .visual_signature_evidence_data import _screenshot_variant_payload
from .visual_signature_evidence_data import _variant_from_filename
from .visual_signature_evidence_data import visual_evidence_model
from .visual_signature_json_data import load_json
from .visual_signature_json_data import pretty_json


def build_screenshot_preview_model(filename: str) -> dict[str, Any] | None:
    return build_screenshot_preview_model_for_lang(filename, "es")


def build_screenshot_preview_model_for_lang(filename: str, lang: str = "es") -> dict[str, Any] | None:
    payload = screenshot_file_response_payload(filename)
    if payload is None:
        return None

    selected_path, _media_type = payload
    selected_brand, selected_label = _variant_from_filename(selected_path)
    evidence = visual_evidence_model()
    selected_item = None
    for item in evidence["items"]:
        if item.get("capture_id") == selected_brand:
            selected_item = item
            break
    if selected_item is None:
        selected_item = {
            "brand_name": selected_brand.replace("-", " ").title(),
            "capture_id": selected_brand,
            "website_url": "",
            "capture_status": "available",
            "obstruction_type": "unknown",
            "obstruction_severity": "unknown",
            "dismissal_attempted": False,
            "dismissal_successful": False,
            "perceptual_state": "evidence_record",
            "evidence_notes": [],
            "variants": [
                _screenshot_variant_payload("raw viewport", visual_signature_root() / "screenshots" / f"{selected_brand}.png"),
                _screenshot_variant_payload("clean attempt", visual_signature_root() / "screenshots" / f"{selected_brand}.clean-attempt.png"),
                _screenshot_variant_payload("full page", visual_signature_root() / "screenshots" / f"{selected_brand}.full-page.png"),
            ],
        }

    selected_variant = None
    for variant in selected_item["variants"]:
        if variant["filename"] == selected_path.name:
            selected_variant = dict(variant)
            break
    if selected_variant is None:
        selected_variant = _screenshot_variant_payload(selected_label, selected_path)

    root = visual_signature_root()
    capture_manifest = load_json(root / "screenshots" / "capture_manifest.json") or {}
    dismissal_audit = load_json(root / "screenshots" / "dismissal_audit.json") or {}
    capture_entry = _find_manifest_row(capture_manifest, selected_item["brand_name"])
    dismissal_entry = _find_manifest_row(dismissal_audit, selected_item["brand_name"])
    related = [_related_variant_payload(variant, selected_variant["filename"]) for variant in selected_item["variants"]]
    available_related = [variant for variant in related if variant["exists"]]
    current_index = next(
        (index for index, variant in enumerate(available_related) if variant["filename"] == selected_variant["filename"]),
        -1,
    )
    previous_variant = available_related[current_index - 1] if current_index > 0 else None
    next_variant = available_related[current_index + 1] if 0 <= current_index < len(available_related) - 1 else None

    return {
        "title": f"{selected_item['brand_name']} {'vista previa de captura' if lang == 'es' else 'screenshot preview'}",
        "brand_name": selected_item["brand_name"],
        "capture_id": selected_item["capture_id"],
        "website_url": selected_item.get("website_url") or "",
        "screenshot_type": selected_variant["label"],
        "selected": selected_variant,
        "related": related,
        "previous": previous_variant,
        "next": next_variant,
        "capture_status": selected_item.get("capture_status") or "available",
        "obstruction_type": selected_item.get("obstruction_type") or "unknown",
        "obstruction_severity": selected_item.get("obstruction_severity") or "unknown",
        "perceptual_state": selected_item.get("perceptual_state") or "evidence_record",
        "evidence_notes": selected_item.get("evidence_notes") or [],
        "source_artifacts": [
            {
                "label": "capture_manifest.json",
                "href": "/visual-signature/artifacts/capture_manifest",
                "path": str(root / "screenshots" / "capture_manifest.json"),
                "raw_json": pretty_json(capture_entry) if capture_entry else "",
            },
            {
                "label": "dismissal_audit.json",
                "href": "/visual-signature/artifacts/dismissal_audit",
                "path": str(root / "screenshots" / "dismissal_audit.json"),
                "raw_json": pretty_json(dismissal_entry) if dismissal_entry else "",
            },
        ],
        "nav": visual_signature_nav(lang, active_section="overview"),
    }
