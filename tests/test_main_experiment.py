import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main
from src.models.brand import BrandScore, DimensionScore
from src.storage.sqlite_store import SQLiteStore


class MainExperimentTests(unittest.TestCase):
    def test_run_experiment_applies_candidates_reruns_and_persists_delta(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")
            before_run = store.create_run(brand_id, "Example", "https://example.com", True, False)
            store.save_scores(
                before_run,
                BrandScore(
                    url="https://example.com",
                    brand_name="Example",
                    dimensions={
                        "presencia": DimensionScore(name="presencia", score=60.0, insights=[], rules_applied=[], features={}),
                        "diferenciacion": DimensionScore(name="diferenciacion", score=40.0, insights=[], rules_applied=[], features={}),
                    },
                    composite_score=50.0,
                ),
            )
            store.finalize_run(before_run, 50.0, True, False, "/tmp/before.json", "before")
            store.save_run_audit(
                before_run,
                {
                    "gate_config": {"max_composite_drop": 0.0, "max_dimension_drops": {}},
                    "active_baseline": None,
                    "scoring_state_fingerprint": "before-fingerprint",
                },
            )
            store.close()

            def fake_run(url, brand_name=None, use_llm=True, use_social=True):
                inner = SQLiteStore(str(db_path))
                try:
                    brand_key = inner.upsert_brand(brand_name, url)
                    run_id = inner.create_run(brand_key, brand_name, url, use_llm, use_social)
                    inner.save_scores(
                        run_id,
                        BrandScore(
                            url=url,
                            brand_name=brand_name,
                            dimensions={
                                "presencia": DimensionScore(name="presencia", score=66.0, insights=[], rules_applied=[], features={}),
                                "diferenciacion": DimensionScore(name="diferenciacion", score=48.0, insights=[], rules_applied=[], features={}),
                            },
                            composite_score=57.0,
                        ),
                    )
                    inner.finalize_run(run_id, 57.0, use_llm, use_social, "/tmp/after.json", "after")
                    inner.save_run_audit(
                        run_id,
                        {
                            "gate_config": {"max_composite_drop": 0.0, "max_dimension_drops": {}},
                            "active_baseline": None,
                            "scoring_state_fingerprint": "after-fingerprint",
                        },
                    )
                    return {
                        "brand": brand_name,
                        "url": url,
                        "run_id": run_id,
                        "composite_score": 57.0,
                    }
                finally:
                    inner.close()

            with patch.object(main, "BRAND3_DB_PATH", str(db_path)):
                with patch.object(main, "apply_candidates", return_value=[{"candidate_id": 9, "applied": True}]):
                    with patch.object(main, "run", side_effect=fake_run):
                        payload = main.run_experiment("Example")

            self.assertEqual(payload["summary"]["composite"]["before"], 50.0)
            self.assertEqual(payload["summary"]["composite"]["after"], 57.0)
            self.assertEqual(payload["summary"]["composite"]["delta"], 7.0)
            self.assertEqual(payload["summary"]["dimensions"]["diferenciacion"]["delta"], 8.0)

            verify = SQLiteStore(str(db_path))
            try:
                experiments = verify.list_experiments("Example", limit=10)
            finally:
                verify.close()

            self.assertEqual(len(experiments), 1)
            self.assertEqual(experiments[0]["candidate_ids"], [9])
            self.assertEqual(experiments[0]["summary"]["after_run_id"], payload["summary"]["after_run_id"])
            self.assertEqual(experiments[0]["before_scoring_state_fingerprint"], "before-fingerprint")
            self.assertEqual(experiments[0]["after_scoring_state_fingerprint"], "after-fingerprint")


if __name__ == "__main__":
    unittest.main()
