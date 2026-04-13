"""Apply approved calibration candidates to repository files."""

from __future__ import annotations

import re
from pathlib import Path


class CandidateApplyError(Exception):
    pass


def apply_dimension_weight(dimensions_path: str, dimension: str, proposed_weight: float) -> None:
    path = Path(dimensions_path)
    original = path.read_text(encoding="utf-8")

    pattern = re.compile(
        r'("' + re.escape(dimension) + r'"\s*:\s*\{.*?"weight":\s*)([0-9.]+)(\s*[,}])',
        re.DOTALL,
    )

    def replace(match):
        return f"{match.group(1)}{proposed_weight:.2f}{match.group(3)}"

    updated, count = pattern.subn(replace, original, count=1)
    if count != 1:
        raise CandidateApplyError(f"Could not locate dimension weight for {dimension}")

    path.write_text(updated, encoding="utf-8")


def apply_rule_threshold(engine_path: str, target: str, proposed_threshold: float) -> None:
    path = Path(engine_path)
    original = path.read_text(encoding="utf-8")

    if target != "diferenciacion.lenguaje_generico":
        raise CandidateApplyError(f"Unsupported rule threshold target: {target}")

    pattern = re.compile(
        r'(condition="lenguaje_generico",.*?generic_language_score", FeatureValue\("", 0\)\)\.value > )([0-9.]+)',
        re.DOTALL,
    )

    def replace(match):
        return f"{match.group(1)}{int(proposed_threshold) if proposed_threshold.is_integer() else proposed_threshold}"

    updated, count = pattern.subn(replace, original, count=1)
    if count != 1:
        raise CandidateApplyError(f"Could not locate rule threshold for {target}")

    path.write_text(updated, encoding="utf-8")


def apply_candidate(dimensions_path: str, engine_path: str, candidate: dict) -> dict:
    scope = candidate["scope"]
    target = candidate["target"]
    proposal = candidate["proposal"]

    if scope == "dimension_weight":
        apply_dimension_weight(dimensions_path, target, float(proposal["proposed_weight"]))
        return {"applied": True, "target": target, "scope": scope}

    if scope == "rule_threshold":
        apply_rule_threshold(engine_path, target, float(proposal["proposed_threshold"]))
        return {"applied": True, "target": target, "scope": scope}

    return {
        "applied": False,
        "target": target,
        "scope": scope,
        "reason": "Unsupported auto-apply scope",
    }
