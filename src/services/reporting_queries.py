"""Read-side reporting helpers for Brand3."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from statistics import mean

from src.config import BRAND3_DB_PATH
from src.niche import list_calibration_profiles
from src.quality.dimension_confidence import dimension_confidence_from_snapshot
from src.quality.evidence_summary import summarize_evidence_records
from src.quality.trust import quality_label
from src.services.benchmark_reporting import benchmark_profiles as _benchmark_profiles_impl
from src.services.benchmark_reporting import compare_benchmarks as _compare_benchmarks_impl
from src.services.brand_reporting import brand_report as _brand_report_impl
from src.services.report_summaries import _trust_summary_payload
from src.storage.sqlite_store import SQLiteStore


def learn(
    run_id: int | None = None,
    brand_name: str | None = None,
    url: str | None = None,
    *,
    db_path: str = BRAND3_DB_PATH,
) -> list[dict]:
    store = SQLiteStore(db_path)
    try:
        target_run_id = run_id or store.get_latest_run_id(brand_name=brand_name, url=url)
        if not target_run_id:
            raise ValueError("No matching run found for learning analysis")

        snapshot = store.get_run_snapshot(target_run_id)
        from src.learning.calibration import CalibrationAnalyzer

        analyzer = CalibrationAnalyzer()
        recommendations = analyzer.analyze_snapshot(snapshot)
        recommendations.extend(analyzer.analyze_annotations(store.list_annotations(brand_name=brand_name)))

        payload = [
            {
                "scope": rec.scope,
                "target": rec.target,
                "severity": rec.severity,
                "message": rec.message,
                "evidence": rec.evidence,
            }
            for rec in recommendations
        ]
        print(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()


def list_runs(
    brand_name: str | None = None,
    url: str | None = None,
    limit: int = 20,
    *,
    db_path: str = BRAND3_DB_PATH,
) -> list[dict]:
    store = SQLiteStore(db_path)
    try:
        runs = store.list_runs(brand_name=brand_name, url=url, limit=limit)
        print(json.dumps(runs, indent=2))
        return runs
    finally:
        store.close()


def list_brands(limit: int = 50, *, db_path: str = BRAND3_DB_PATH) -> list[dict]:
    store = SQLiteStore(db_path)
    try:
        brands = store.list_brands(limit=limit)
        print(json.dumps(brands, indent=2))
        return brands
    finally:
        store.close()


def list_profiles() -> list[dict]:
    profiles = list_calibration_profiles()
    print(json.dumps(profiles, indent=2))
    return profiles


def benchmark_profiles(
    spec_path: str,
    *,
    profiles: list[str] | None = None,
    include_auto: bool = True,
    use_llm: bool = True,
    use_social: bool = True,
    use_competitors: bool = True,
    run_fn=None,
) -> dict:
    return _benchmark_profiles_impl(
        spec_path,
        profiles=profiles,
        include_auto=include_auto,
        use_llm=use_llm,
        use_social=use_social,
        use_competitors=use_competitors,
        run_fn=run_fn,
    )


def compare_benchmarks(before_path: str, after_path: str) -> dict:
    return _compare_benchmarks_impl(before_path, after_path)


def list_feedback(brand_name: str | None = None, *, db_path: str = BRAND3_DB_PATH) -> list[dict]:
    store = SQLiteStore(db_path)
    try:
        feedback = store.list_feedback(brand_name=brand_name)
        print(json.dumps(feedback, indent=2))
        return feedback
    finally:
        store.close()


def _context_readiness_from_snapshot(snapshot: dict) -> dict:
    for item in reversed(snapshot.get("raw_inputs") or []):
        if item.get("source") != "context" or not isinstance(item.get("payload"), dict):
            continue
        payload = item["payload"]
        coverage = float(payload.get("coverage") or 0.0)
        confidence = float(payload.get("confidence") or 0.0)
        if coverage < 0.3:
            status = "insufficient_data"
        elif confidence < 0.6:
            status = "degraded"
        else:
            status = "good"
        return {
            "available": True,
            "coverage": coverage,
            "confidence": confidence,
            "coverage_label": quality_label(coverage),
            "confidence_label": quality_label(confidence),
            "status": status,
            "confidence_reason": payload.get("confidence_reason") or [],
            "context_score": payload.get("context_score"),
        }
    return {
        "available": False,
        "coverage": 0.0,
        "confidence": 0.0,
        "coverage_label": "baja",
        "confidence_label": "baja",
        "status": "insufficient_data",
        "confidence_reason": ["context_scan_unavailable"],
    }


def show_run(run_id: int, *, db_path: str = BRAND3_DB_PATH) -> dict:
    store = SQLiteStore(db_path)
    try:
        snapshot = store.get_run_snapshot(run_id)
        if not snapshot:
            raise ValueError(f"Run {run_id} not found")
        context_summary = _context_readiness_from_snapshot(snapshot)
        trust_summary = snapshot["audit"].get("trust_summary") if snapshot.get("audit") else None
        if not trust_summary:
            trust_summary = {
                "data_quality": snapshot["run"].get("data_quality"),
                "context_summary": context_summary,
                "evidence_summary": snapshot["audit"].get("evidence_summary") if snapshot.get("audit") else None,
                "dimension_confidence": snapshot["audit"].get("dimension_confidence") if snapshot.get("audit") else None,
            }
        payload = {
            "run_id": run_id,
            **snapshot["run"],
            "audit": snapshot["audit"],
            "brand_profile": snapshot["brand_profile"],
            "context_readiness": context_summary,
            "trust_summary": trust_summary,
        }
        print(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()


def run_evidence_summary(run_id: int, *, db_path: str = BRAND3_DB_PATH) -> dict:
    store = SQLiteStore(db_path)
    try:
        snapshot = store.get_run_snapshot(run_id)
        if not snapshot:
            raise ValueError(f"Run {run_id} not found")
        audit = snapshot.get("run", {}).get("audit") or {}
        summary = summarize_evidence_records(
            snapshot.get("features") or [],
            evidence_items=snapshot.get("evidence_items") or [],
        )
        summary = audit.get("evidence_summary") or summary
        print(json.dumps(summary, indent=2))
        return summary
    finally:
        store.close()


def run_dimension_confidence(run_id: int, *, db_path: str = BRAND3_DB_PATH) -> dict:
    store = SQLiteStore(db_path)
    try:
        snapshot = store.get_run_snapshot(run_id)
        if not snapshot:
            raise ValueError(f"Run {run_id} not found")
        audit = snapshot.get("run", {}).get("audit") or {}
        summary = audit.get("dimension_confidence") or dimension_confidence_from_snapshot(snapshot)
        print(json.dumps(summary, indent=2))
        return summary
    finally:
        store.close()


def run_trust_summary(run_id: int, *, db_path: str = BRAND3_DB_PATH) -> dict:
    store = SQLiteStore(db_path)
    try:
        snapshot = store.get_run_snapshot(run_id)
        if not snapshot:
            raise ValueError(f"Run {run_id} not found")
        run_payload = snapshot.get("run") or {}
        context_summary = _context_readiness_from_snapshot(snapshot)
        evidence_summary = summarize_evidence_records(
            snapshot.get("features") or [],
            evidence_items=snapshot.get("evidence_items") or [],
        )
        dimension_confidence = dimension_confidence_from_snapshot(snapshot)
        trust_summary = _trust_summary_payload(
            data_quality=run_payload.get("data_quality") or "unknown",
            context_summary=context_summary,
            evidence_summary=evidence_summary,
            dimension_confidence=dimension_confidence,
        )
        summary = {
            "run_id": run_id,
            **trust_summary,
            "trust_summary": trust_summary,
            "context_readiness": context_summary,
            "evidence_summary": evidence_summary,
            "dimension_confidence": dimension_confidence,
        }
        print(json.dumps(summary, indent=2))
        return summary
    finally:
        store.close()


def brand_report(brand_name: str, limit: int = 10) -> dict:
    return _brand_report_impl(brand_name, limit=limit, db_path=BRAND3_DB_PATH)
