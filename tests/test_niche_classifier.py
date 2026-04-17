import unittest

from src.niche.classifier import classify_brand_niche, select_calibration_profile


class NicheClassifierTests(unittest.TestCase):
    def test_frontier_model_lab_is_classified_to_frontier_ai(self):
        payload = classify_brand_niche(
            "Prior Labs",
            "https://priorlabs.ai",
            web_title="Prior Labs builds tabular foundation models",
            web_content=(
                "Pre-trained tabular foundation models for enterprise data. "
                "Open source research and benchmark results for foundation-model systems."
            ),
            exa_texts=["Tabular foundation model startup with open source research"],
            competitor_names=["Hugging Face", "Anthropic"],
        )

        self.assertEqual(payload["predicted_niche"], "frontier_ai")
        self.assertEqual(payload["predicted_subtype"], "model_lab")
        self.assertGreaterEqual(payload["confidence"], 0.65)
        self.assertTrue(any("foundation" in item.lower() or "research" in item.lower() for item in payload["evidence"]))

    def test_startup_studio_stays_on_base_profile_but_is_not_low_confidence_noise(self):
        payload = classify_brand_niche(
            "Jetty AI",
            "https://jettyai.cloud",
            web_title="Jetty AI startup foundry",
            web_content="A venture studio and startup foundry building AI products.",
        )

        profile, source = select_calibration_profile(payload, min_confidence=0.65)

        self.assertEqual(payload["predicted_niche"], "base")
        self.assertEqual(payload["predicted_subtype"], "startup_studio")
        self.assertEqual(profile, "base")
        self.assertEqual(source, "auto")

    def test_community_platform_stays_on_base_and_beats_noisy_exa_ai_signals(self):
        payload = classify_brand_niche(
            "Movements",
            "https://movements.mov/en",
            web_title="MOVEMENTS",
            web_content=(
                "Convert your cause into an unstoppable movement. "
                "MOVEMENTS offers petitions, community, content and subscriptions to drive change. "
                "We are the new platform for those who want to organize, scale and sustain their cause. "
                "No algorithms limiting your reach. You maintain complete control over your audience."
            ),
            exa_texts=["frontier hardware model startup"],
        )

        profile, source = select_calibration_profile(payload, min_confidence=0.65)

        self.assertEqual(payload["predicted_niche"], "base")
        self.assertEqual(payload["predicted_subtype"], "community_platform")
        self.assertGreaterEqual(payload["confidence"], 0.65)
        self.assertEqual(profile, "base")
        self.assertEqual(source, "auto")

    def test_low_confidence_prediction_falls_back_to_base_profile(self):
        payload = {
            "predicted_niche": "enterprise_ai",
            "confidence": 0.42,
        }

        profile, source = select_calibration_profile(payload, min_confidence=0.65)

        self.assertEqual(profile, "base")
        self.assertEqual(source, "fallback")

    def test_llm_framework_signals_classify_to_base_subtype(self):
        payload = classify_brand_niche(
            "LangChain",
            "https://langchain.com",
            web_title="Leading open-source framework for LLM applications",
            web_content=(
                "Build LLM applications with an open-source framework, orchestration tools, "
                "SDKs, and developer libraries."
            ),
        )

        profile, source = select_calibration_profile(payload, min_confidence=0.65)

        self.assertEqual(payload["predicted_niche"], "base")
        self.assertEqual(payload["predicted_subtype"], "llm_framework")
        self.assertEqual(profile, "base")
        self.assertEqual(source, "auto")

    def test_agent_tooling_signals_classify_to_base_subtype(self):
        payload = classify_brand_niche(
            "Kura",
            "https://kura.ai",
            web_title="AI agent tools for browsing and web interaction",
            web_content=(
                "High-accuracy AI agent tooling for web automation, browsing, and "
                "engineering validation workflows."
            ),
        )

        profile, source = select_calibration_profile(payload, min_confidence=0.65)

        self.assertEqual(payload["predicted_niche"], "base")
        self.assertEqual(payload["predicted_subtype"], "agent_tooling")
        self.assertEqual(profile, "base")
        self.assertEqual(source, "auto")

    def test_workforce_marketplace_signals_classify_to_base_subtype(self):
        payload = classify_brand_niche(
            "Traba",
            "https://traba.work",
            web_title="Industrial workforce marketplace",
            web_content=(
                "Marketplace platform for industrial labor, staffing operations, "
                "and supply chain workforce management."
            ),
        )

        profile, source = select_calibration_profile(payload, min_confidence=0.65)

        self.assertEqual(payload["predicted_niche"], "base")
        self.assertEqual(payload["predicted_subtype"], "workforce_marketplace")
        self.assertEqual(profile, "base")
        self.assertEqual(source, "auto")

    def test_productivity_addon_signals_classify_to_base_subtype(self):
        payload = classify_brand_niche(
            "Melder",
            "https://melder.ai",
            web_title="AI Excel add-on for structured analysis",
            web_content=(
                "Excel add-on for structured data analysis, spreadsheet workflows, "
                "and document processing."
            ),
        )

        profile, source = select_calibration_profile(payload, min_confidence=0.65)

        self.assertEqual(payload["predicted_niche"], "base")
        self.assertEqual(payload["predicted_subtype"], "productivity_addon")
        self.assertEqual(profile, "base")
        self.assertEqual(source, "auto")

    def test_engineering_validation_signals_classify_to_base_subtype(self):
        payload = classify_brand_niche(
            "Cognition AI",
            "https://cognition.ai",
            web_title="Autonomous software engineering",
            web_content=(
                "Known for Devin and specialized AI engineering validation with "
                "agent evaluation and software engineering workflows."
            ),
        )

        profile, source = select_calibration_profile(payload, min_confidence=0.65)

        self.assertEqual(payload["predicted_niche"], "base")
        self.assertEqual(payload["predicted_subtype"], "engineering_validation")
        self.assertEqual(profile, "base")
        self.assertEqual(source, "auto")

    def test_frontier_research_is_not_dragged_to_community_by_noisy_mentions(self):
        payload = classify_brand_niche(
            "Thinking Machines Lab",
            "https://thinkingmachines.ai",
            web_title="AI research lab for multimodal foundation models",
            web_content=(
                "Research lab building foundation models and open research artifacts "
                "for multimodal reasoning systems."
            ),
            exa_texts=[
                "community petition and audience growth tactics",
                "cause movement examples",
            ],
        )

        self.assertEqual(payload["predicted_niche"], "frontier_ai")
        self.assertIn(payload.get("predicted_subtype"), {"ai_research_lab", "model_lab"})

    def test_agent_tooling_is_not_triggered_by_validation_word_alone(self):
        payload = classify_brand_niche(
            "ConcertAI",
            "https://concertai.com",
            web_title="Applied AI for clinical trials",
            web_content=(
                "Applied AI platform for oncology and clinical-trial intelligence "
                "with validated real-world evidence."
            ),
            exa_texts=[
                "validation workflows for healthcare outcomes",
                "enterprise platform for life sciences",
            ],
        )

        self.assertEqual(payload["predicted_niche"], "base")
        self.assertLess(payload["confidence"], 0.65)


if __name__ == "__main__":
    unittest.main()
