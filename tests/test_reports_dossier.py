import unittest
from unittest.mock import MagicMock

from src.reports.dossier import build_brand_dossier
from tests.test_reports_renderer import _sample_snapshot


class BrandDossierTests(unittest.TestCase):
    def test_build_brand_dossier_applies_narrative_overlays(self):
        analyzer = MagicMock()
        synthesis_prompts: list[str] = []

        def _call(system: str, user: str, max_tokens: int = 1200):
            synthesis_prompts.append(user)
            return "Narrative synthesis for the report."

        analyzer._call.side_effect = _call

        def _call_json(system: str, user: str, max_tokens: int = 2000):
            if '"tension"' in user:
                return {"tension": "One meaningful tension."}
            return {"findings": [{"title": "f", "prose": "p", "evidence_urls": []}]}

        analyzer._call_json.side_effect = _call_json

        dossier = build_brand_dossier(_sample_snapshot(), analyzer=analyzer)

        self.assertEqual(dossier["synthesis_prose"], "Narrative synthesis for the report.")
        self.assertEqual(dossier["summary"], "Narrative synthesis for the report.")
        self.assertEqual(dossier["tensions_prose"], "One meaningful tension.")
        self.assertEqual(len(synthesis_prompts), 1)
        self.assertIn("One meaningful tension.", synthesis_prompts[0])
        self.assertIn("evaluation", dossier)
        self.assertIn("narrative", dossier)
        self.assertIn("sources", dossier)
        self.assertIn("audit", dossier)
        self.assertIn("ui", dossier)
        self.assertEqual(dossier["evaluation"]["composite_display"], "74")
        self.assertEqual(dossier["narrative"]["summary"], "Narrative synthesis for the report.")
        self.assertEqual(len(dossier["dimensions"]), 5)
        self.assertTrue(all("findings" in dim for dim in dossier["dimensions"]))

    def test_perceptual_narrative_experiment_preserves_scores_and_structure(self):
        snapshot = _sample_snapshot()

        def _analyzer() -> MagicMock:
            analyzer = MagicMock()
            analyzer._call.return_value = "Narrative synthesis for the report."
            analyzer._call_json.side_effect = lambda system, user, max_tokens=2000: (
                {"tension": "One meaningful tension."}
                if '"tension"' in user
                else {"findings": [{"title": "f", "prose": "p", "evidence_urls": []}]}
            )
            return analyzer

        base = build_brand_dossier(snapshot, analyzer=_analyzer())
        experimental = build_brand_dossier(
            snapshot,
            analyzer=_analyzer(),
            enable_perceptual_narrative=True,
        )

        self.assertEqual(experimental["evaluation"], base["evaluation"])
        self.assertEqual(experimental["score"], base["score"])
        self.assertEqual(
            experimental["evaluation"]["band_letter"],
            base["evaluation"]["band_letter"],
        )
        self.assertEqual(set(experimental.keys()), set(base.keys()))
        self.assertEqual(len(experimental["dimensions"]), len(base["dimensions"]))

    def test_perceptual_narrative_experiment_is_off_by_default(self):
        prompts: list[str] = []
        analyzer = MagicMock()
        analyzer._call.return_value = "Narrative synthesis for the report."

        def _call_json(system: str, user: str, max_tokens: int = 2000):
            prompts.append(user)
            if '"tension"' in user:
                return {"tension": "One meaningful tension."}
            return {"findings": [{"title": "f", "prose": "p", "evidence_urls": []}]}

        analyzer._call_json.side_effect = _call_json

        build_brand_dossier(_sample_snapshot(), analyzer=analyzer)

        self.assertTrue(prompts)
        self.assertFalse(
            any("EXPERIMENTAL PERCEPTUAL NARRATIVE HINTS" in prompt for prompt in prompts)
        )


if __name__ == "__main__":
    unittest.main()
