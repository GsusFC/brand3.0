import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.services import benchmark_reporting, brand_reporting


class _BrandReportStore:
    def __init__(self, report: dict):
        self.report = report
        self.closed = False

    def get_brand_report(self, brand_name: str, limit: int = 10):
        self.brand_name = brand_name
        self.limit = limit
        return self.report

    def close(self):
        self.closed = True


class ReportingHelperTests(unittest.TestCase):
    def test_brand_report_computes_summary_from_store_snapshot(self):
        report = {
            "brand_profile": {"brand_name": "Example"},
            "runs": [
                {
                    "composite_score": 81.0,
                    "scoring_state_fingerprint": "fp-1",
                    "predicted_niche": "software",
                    "predicted_subtype": "saas",
                    "niche_confidence": 0.9,
                    "calibration_profile": "base",
                },
                {
                    "composite_score": 75.0,
                    "scoring_state_fingerprint": "fp-2",
                    "predicted_niche": "software",
                    "predicted_subtype": "saas",
                    "niche_confidence": 0.8,
                    "calibration_profile": "base",
                },
            ],
            "dimension_series": {
                "coherencia": [{"score": 72.0}, {"score": 66.0}],
            },
            "annotations": [
                {"dimension_name": "coherencia"},
                {"dimension_name": "presencia"},
            ],
        }

        store = _BrandReportStore(report)

        with patch.object(brand_reporting, "SQLiteStore", return_value=store):
            payload = brand_reporting.brand_report("Example", limit=5, db_path=":memory:")

        self.assertTrue(store.closed)
        self.assertEqual(store.brand_name, "Example")
        self.assertEqual(store.limit, 5)
        self.assertEqual(payload["run_count"], 2)
        self.assertEqual(payload["latest_composite"], 81.0)
        self.assertEqual(payload["average_composite"], 78.0)
        self.assertEqual(payload["composite_trend"], 6.0)
        self.assertEqual(payload["dimensions"]["coherencia"]["samples"], 2)
        self.assertEqual(payload["feedback"]["count"], 2)
        self.assertEqual(payload["scoring_states"]["fp-1"], 1)

    def test_benchmark_profiles_uses_selected_profiles_and_writes_output(self):
        spec = {
            "name": "Sample benchmark",
            "brands": [
                {"brand_name": "Example", "url": "https://example.com", "expected_niche": "software"},
            ],
        }

        fake_run_result = {
            "run_id": 123,
            "composite_score": 88.0,
            "dimensions": {"coherencia": 80.0},
            "niche_classification": {
                "predicted_niche": "software",
                "predicted_subtype": "saas",
                "confidence": 0.9,
            },
            "profile_source": "manual",
            "calibration_profile": "base",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            spec_path = Path(tmpdir) / "spec.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")

            def fake_save(payload):
                return Path(tmpdir) / "benchmark.json"

            with (
                patch.object(
                    benchmark_reporting,
                    "list_calibration_profiles",
                    return_value=[{"profile_id": "base"}],
                ),
                patch.object(benchmark_reporting, "_save_benchmark_result", side_effect=fake_save),
            ):
                payload = benchmark_reporting.benchmark_profiles(
                    str(spec_path),
                    profiles=["base"],
                    include_auto=False,
                    run_fn=lambda *args, **kwargs: fake_run_result,
                )

        self.assertEqual(payload["benchmark_name"], "Sample benchmark")
        self.assertEqual(payload["summary"]["variants"]["base"]["count"], 1)
        self.assertEqual(payload["summary"]["variants"]["base"]["average_composite"], 88.0)
        self.assertEqual(payload["brands"][0]["results"][0]["niche_match"], True)
        self.assertEqual(str(payload["output_path"]), str(Path(tmpdir) / "benchmark.json"))

    def test_compare_benchmarks_reports_shared_brand_deltas(self):
        before = {
            "benchmark_name": "Before",
            "brands": [
                {
                    "brand_name": "Example",
                    "url": "https://example.com",
                    "results": [
                        {
                            "variant": "base",
                            "composite_score": 70.0,
                            "dimensions": {"coherencia": 60.0},
                            "niche_match": False,
                            "subtype_match": False,
                            "predicted_niche": "other",
                            "predicted_subtype": "other",
                        }
                    ],
                }
            ],
        }
        after = {
            "benchmark_name": "After",
            "brands": [
                {
                    "brand_name": "Example",
                    "url": "https://example.com",
                    "results": [
                        {
                            "variant": "base",
                            "composite_score": 80.0,
                            "dimensions": {"coherencia": 66.0},
                            "niche_match": True,
                            "subtype_match": True,
                            "predicted_niche": "software",
                            "predicted_subtype": "saas",
                        }
                    ],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            before_path = Path(tmpdir) / "before.json"
            after_path = Path(tmpdir) / "after.json"
            before_path.write_text(json.dumps(before), encoding="utf-8")
            after_path.write_text(json.dumps(after), encoding="utf-8")

            with patch.object(
                benchmark_reporting,
                "_save_benchmark_comparison_result",
                return_value=Path(tmpdir) / "comparison.json",
            ):
                payload = benchmark_reporting.compare_benchmarks(str(before_path), str(after_path))

        self.assertEqual(payload["summary"]["shared_brands"], 1)
        self.assertEqual(payload["summary"]["variant_deltas"]["base"]["count"], 1)
        self.assertEqual(payload["summary"]["variant_deltas"]["base"]["average_composite_delta"], 10.0)
        self.assertEqual(payload["summary"]["variant_deltas"]["base"]["niche_match_improved"], 1)
        self.assertEqual(payload["summary"]["variant_deltas"]["base"]["subtype_match_improved"], 1)
        self.assertEqual(str(payload["output_path"]), str(Path(tmpdir) / "comparison.json"))
