"""Offline calibration and recommendation helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Any

from ..dimensions import DIMENSIONS


@dataclass
class CalibrationRecommendation:
    scope: str
    target: str
    severity: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class CalibrationCandidate:
    scope: str
    target: str
    proposal: dict[str, Any]
    rationale: str
    severity: str
    evidence: dict[str, Any] = field(default_factory=dict)


class CalibrationAnalyzer:
    """Generates human-reviewable recommendations from annotated runs."""

    def analyze_snapshot(self, snapshot: dict[str, Any]) -> list[CalibrationRecommendation]:
        recommendations: list[CalibrationRecommendation] = []
        if not snapshot or not snapshot.get("annotations"):
            return recommendations

        score_map = {item["dimension_name"]: item for item in snapshot.get("scores", [])}
        feature_rows = snapshot.get("features", [])

        for annotation in snapshot["annotations"]:
            dimension = annotation.get("dimension_name")
            feature = annotation.get("feature_name")
            expected = annotation.get("expected_score")
            actual = annotation.get("actual_score")

            if dimension and expected is not None:
                if actual is None and dimension in score_map:
                    actual = score_map[dimension]["score"]
                if actual is not None:
                    delta = expected - actual
                    if abs(delta) >= 15:
                        recommendations.append(
                            CalibrationRecommendation(
                                scope="dimension",
                                target=dimension,
                                severity="high" if abs(delta) >= 25 else "medium",
                                message=(
                                    f"Human feedback differs from scored {dimension} by {delta:.1f} points. "
                                    "Review weights, caps, and extraction quality."
                                ),
                                evidence={
                                    "expected_score": expected,
                                    "actual_score": actual,
                                    "delta": round(delta, 1),
                                    "rules": score_map.get(dimension, {}).get("rules_json", "[]"),
                                    "note": annotation.get("note", ""),
                                },
                            )
                        )

            if dimension and feature:
                matching = [row for row in feature_rows if row["dimension_name"] == dimension and row["feature_name"] == feature]
                if matching:
                    item = matching[0]
                    confidence = float(item["confidence"])
                    if confidence < 0.6:
                        recommendations.append(
                            CalibrationRecommendation(
                                scope="feature",
                                target=f"{dimension}.{feature}",
                                severity="medium",
                                message="Annotated disagreement landed on a low-confidence feature. Improve extraction or sourcing.",
                                evidence={
                                    "value": item["value"],
                                    "confidence": confidence,
                                    "source": item["source"],
                                    "note": annotation.get("note", ""),
                                },
                            )
                        )

        recommendations.extend(self._detect_generic_rule_pressure(snapshot))
        return recommendations

    def analyze_annotations(self, annotations: list[dict[str, Any]]) -> list[CalibrationRecommendation]:
        if not annotations:
            return []

        grouped: dict[str, list[float]] = {}
        for item in annotations:
            dimension = item.get("dimension_name")
            expected = item.get("expected_score")
            actual = item.get("actual_score")
            if not dimension or expected is None or actual is None:
                continue
            grouped.setdefault(dimension, []).append(expected - actual)

        recommendations = []
        for dimension, deltas in grouped.items():
            avg_delta = mean(deltas)
            if abs(avg_delta) >= 10:
                recommendations.append(
                    CalibrationRecommendation(
                        scope="dimension-trend",
                        target=dimension,
                        severity="high" if abs(avg_delta) >= 20 else "medium",
                        message=(
                            f"Historical feedback shows consistent bias in {dimension}: "
                            f"average delta {avg_delta:.1f}. Revisit thresholds/weights."
                        ),
                        evidence={
                            "average_delta": round(avg_delta, 1),
                            "annotation_count": len(deltas),
                            "dimension_weight": DIMENSIONS.get(dimension, {}).get("weight"),
                        },
                    )
                )
        return recommendations

    def _detect_generic_rule_pressure(self, snapshot: dict[str, Any]) -> list[CalibrationRecommendation]:
        # The `lenguaje_generico` rule now reads `uniqueness` (opción B del
        # refactor de Diferenciación). Low uniqueness = generic language.
        recs = []
        feature_rows = snapshot.get("features", [])
        uniqueness_scores = [
            row["value"] for row in feature_rows
            if row["feature_name"] == "uniqueness"
        ]
        if uniqueness_scores and min(uniqueness_scores) < 20:
            recs.append(
                CalibrationRecommendation(
                    scope="rule",
                    target="diferenciacion.lenguaje_generico",
                    severity="medium",
                    message="Uniqueness dropped near the generic language cap threshold. Validate if the threshold is too aggressive.",
                    evidence={"uniqueness_min": min(uniqueness_scores)},
                )
            )
        return recs

    def propose_candidates(
        self,
        brand_report: dict[str, Any],
        annotations: list[dict[str, Any]],
    ) -> list[CalibrationCandidate]:
        candidates: list[CalibrationCandidate] = []

        grouped: dict[str, list[float]] = {}
        for item in annotations:
            dimension = item.get("dimension_name")
            expected = item.get("expected_score")
            actual = item.get("actual_score")
            if not dimension or expected is None or actual is None:
                continue
            grouped.setdefault(dimension, []).append(expected - actual)

        for dimension, deltas in grouped.items():
            avg_delta = mean(deltas)
            if abs(avg_delta) >= 10:
                current_weight = DIMENSIONS.get(dimension, {}).get("weight", 0.0)
                adjustment = 0.02 if avg_delta > 0 else -0.02
                proposed_weight = max(0.05, min(0.4, round(current_weight + adjustment, 3)))
                candidates.append(
                    CalibrationCandidate(
                        scope="dimension_weight",
                        target=dimension,
                        proposal={
                            "current_weight": current_weight,
                            "proposed_weight": proposed_weight,
                            "delta": round(proposed_weight - current_weight, 3),
                        },
                        rationale=(
                            f"Historical annotations suggest {dimension} is systematically "
                            f"{'undervalued' if avg_delta > 0 else 'overvalued'}."
                        ),
                        severity="high" if abs(avg_delta) >= 20 else "medium",
                        evidence={
                            "average_annotation_delta": round(avg_delta, 1),
                            "annotation_count": len(deltas),
                        },
                    )
                )

        # Post-refactor: `generic_language_score` was replaced by `uniqueness`
        # (inverted semantics: low uniqueness = generic).
        generic_annotations = [
            item for item in annotations
            if item.get("feature_name") == "uniqueness"
            and item.get("expected_score") is not None
            and item.get("actual_score") is not None
            and (item["expected_score"] - item["actual_score"]) >= 15
        ]
        if len(generic_annotations) >= 1:
            candidates.append(
                CalibrationCandidate(
                    scope="rule_threshold",
                    target="diferenciacion.lenguaje_generico",
                    proposal={
                        "current_threshold": 80,
                        "proposed_threshold": 85,
                        "cap": 25,
                    },
                    rationale="Feedback repeatedly indicates the generic-language cap may be too aggressive.",
                    severity="medium",
                    evidence={
                        "supporting_annotations": len(generic_annotations),
                    },
                )
            )

        dimension_series = brand_report.get("dimension_series", {})
        for dimension, series in dimension_series.items():
            if len(series) < 3:
                continue
            values = [item["score"] for item in series]
            if max(values) - min(values) >= 30:
                candidates.append(
                    CalibrationCandidate(
                        scope="stability_review",
                        target=dimension,
                        proposal={
                            "range": round(max(values) - min(values), 1),
                            "latest": values[0],
                            "oldest": values[-1],
                        },
                        rationale="Dimension shows high variance across runs; check collector stability and thresholds.",
                        severity="medium",
                        evidence={"samples": len(values)},
                    )
                )

        return candidates
