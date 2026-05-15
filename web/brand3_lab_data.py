"""Static data builders for experimental Brand3 lab views."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVALUATION_PATH = PROJECT_ROOT / "examples" / "brand3_platform" / "perceptual_narrative_evaluation.json"
STRESS_TEST_PATH = (
    PROJECT_ROOT
    / "examples"
    / "perceptual_library"
    / "patterns"
    / "perceptual_reasoning_stress_test.json"
)
OVERREACH_TAXONOMY_PATH = (
    PROJECT_ROOT
    / "examples"
    / "perceptual_library"
    / "patterns"
    / "perceptual_overreach_taxonomy.json"
)

GENERIC_PHRASES = [
    "premium",
    "polished",
    "sophisticated",
    "modern",
    "strong",
    "robust",
    "cohesive",
    "leadership",
    "trusted",
    "supportive",
    "accessible",
    "clear benefits",
    "clean interface",
    "differentiated",
]


def build_perceptual_narrative_comparison_model() -> dict[str, Any]:
    evaluation = _load_json(EVALUATION_PATH)
    stress_test = _load_json(STRESS_TEST_PATH)
    taxonomy = _load_json(OVERREACH_TAXONOMY_PATH)

    pairs = [
        _format_pair(index, pair)
        for index, pair in enumerate(evaluation.get("paired_outputs", []), start=1)
        if isinstance(pair, dict)
    ]
    failure_modes = [
        {
            "id": str(item.get("id") or ""),
            "name": str(item.get("name") or ""),
            "warning_signs": _string_list(item.get("observable_warning_signs"))[:3],
        }
        for item in taxonomy.get("failure_modes", [])
        if isinstance(item, dict)
    ]

    return {
        "title": "Perceptual Narrative Comparison",
        "intro": (
            "Experimental lab viewer for comparing baseline findings against "
            "perceptual-augmented findings before any rollout decision."
        ),
        "guardrails": [
            "experimental lab only",
            "draft only",
            "no persistence",
            "no scoring impact",
            "no prompt changes",
            "no report renderer changes",
            "no Visual Signature changes",
        ],
        "pairs": pairs,
        "pair_count": len(pairs),
        "review_options": [
            "baseline_better",
            "perceptual_better",
            "mixed",
            "unsafe_overreach",
        ],
        "aggregate": evaluation.get("aggregate_assessment", {}),
        "recommendation": evaluation.get("recommendation", {}),
        "safe_deployment_zones": _string_list(stress_test.get("safe_deployment_zones")),
        "unsafe_deployment_zones": _string_list(stress_test.get("unsafe_deployment_zones")),
        "failure_modes": failure_modes,
        "source_paths": [
            str(EVALUATION_PATH.relative_to(PROJECT_ROOT)),
            str(STRESS_TEST_PATH.relative_to(PROJECT_ROOT)),
            str(OVERREACH_TAXONOMY_PATH.relative_to(PROJECT_ROOT)),
        ],
    }


def _format_pair(index: int, pair: dict[str, Any]) -> dict[str, Any]:
    brand = str(pair.get("brand") or f"Case {index}")
    baseline = str(pair.get("baseline_narrative") or "")
    perceptual = str(pair.get("perceptual_augmented_narrative") or "")
    comparison = pair.get("comparison") if isinstance(pair.get("comparison"), dict) else {}
    strengths = _string_list(pair.get("strengths"))
    weaknesses = _string_list(pair.get("weaknesses"))
    overreach_flags = _string_list(pair.get("overreach_flags"))

    perceptual_gains = [
        _humanize_metric(key, value)
        for key, value in comparison.items()
        if key.endswith("_delta") and str(value).startswith(("improves", "reduced", "lower"))
    ]

    return {
        "id": _slugify(brand),
        "index": index,
        "brand": brand,
        "baseline_narrative": baseline,
        "perceptual_augmented_narrative": perceptual,
        "better_specificity": _better_specificity(comparison),
        "perceptual_gains": perceptual_gains[:6],
        "overreach_risks": [*overreach_flags, *weaknesses],
        "generic_phrases": _find_generic_phrases(baseline, perceptual),
        "comparison": comparison,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "overreach_flags": overreach_flags,
        "brand3_confidence": str(comparison.get("feels_brand3_floc_confidence") or "unrated"),
    }


def _better_specificity(comparison: dict[str, Any]) -> list[str]:
    items: list[str] = []
    for key in (
        "specificity_delta",
        "observational_grounding_delta",
        "tension_quality_delta",
    ):
        value = str(comparison.get(key) or "")
        if value:
            items.append(_humanize_metric(key, value))
    return items


def _humanize_metric(key: str, value: Any) -> str:
    label = key.replace("_delta", "").replace("_", " ")
    return f"{label}: {str(value).replace('_', ' ')}"


def _find_generic_phrases(*texts: str) -> list[str]:
    haystack = " ".join(texts).lower()
    found = [phrase for phrase in GENERIC_PHRASES if phrase in haystack]
    return sorted(set(found))


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item]


def _slugify(value: str) -> str:
    out = []
    last_dash = False
    for char in value.lower():
        if char.isalnum():
            out.append(char)
            last_dash = False
        elif not last_dash:
            out.append("-")
            last_dash = True
    return "".join(out).strip("-") or "case"
