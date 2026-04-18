import unittest
from unittest.mock import patch

from src.collectors.exa_collector import ExaData, ExaResult
from src.collectors.exa_collector import ExaCollector
from src.collectors.social_collector import PlatformMetrics, SocialData
from src.collectors.web_collector import WebData
from src.collectors.web_collector import WebCollector
from src.features.coherencia import CoherenciaExtractor
from src.features.diferenciacion import DiferenciacionExtractor
from src.features.percepcion import PercepcionExtractor
from src.features.presencia import PresenciaExtractor
from src.features.vitalidad import VitalidadExtractor


class PercepcionExtractorTests(unittest.TestCase):
    def setUp(self):
        self.extractor = PercepcionExtractor()

    def test_sentiment_trend_uses_published_dates_not_result_order(self):
        exa = ExaData(
            brand_name="Test Brand",
            mentions=[
                ExaResult(
                    url="https://example.com/recent-1",
                    title="Recent positive",
                    text="excellent breakthrough",
                    published_date="2026-04-01",
                ),
                ExaResult(
                    url="https://example.com/old-1",
                    title="Old negative",
                    text="lawsuit outage",
                    published_date="2024-01-01",
                ),
                ExaResult(
                    url="https://example.com/recent-2",
                    title="Recent positive 2",
                    text="amazing reliable",
                    published_date="2026-03-15",
                ),
                ExaResult(
                    url="https://example.com/old-2",
                    title="Old negative 2",
                    text="fraud scam",
                    published_date="2024-02-01",
                ),
            ],
        )

        trend = self.extractor._sentiment_trend(exa)

        self.assertGreater(trend.value, 50.0)
        self.assertEqual(trend.confidence, 0.6)
        self.assertIn("dated_results=4", trend.raw_value)

    def test_sentiment_trend_returns_low_confidence_without_enough_dated_results(self):
        exa = ExaData(
            brand_name="Test Brand",
            mentions=[
                ExaResult(url="https://example.com/1", title="One", text="great", published_date=""),
                ExaResult(url="https://example.com/2", title="Two", text="great", published_date="2026-04-01"),
                ExaResult(url="https://example.com/3", title="Three", text="bad", published_date=""),
            ],
        )

        trend = self.extractor._sentiment_trend(exa)

        self.assertEqual(trend.value, 50.0)
        self.assertEqual(trend.confidence, 0.1)
        self.assertEqual(trend.raw_value, "insufficient dated mentions")

    def test_review_quality_is_neutral_when_brand_has_mentions_but_no_review_platforms(self):
        exa = ExaData(
            brand_name="Test Brand",
            mentions=[
                ExaResult(url=f"https://example.com/{idx}", title="Mention", text="strong traction")
                for idx in range(4)
            ],
            news=[
                ExaResult(url="https://news.example.com/item", title="Launch", text="new launch")
            ],
        )

        feature = self.extractor._review_quality(exa)

        self.assertEqual(feature.value, 50.0)
        self.assertEqual(feature.confidence, 0.2)
        self.assertIn("mentions=5", feature.raw_value)

    def test_review_quality_uses_review_platforms_when_present(self):
        exa = ExaData(
            brand_name="Test Brand",
            mentions=[
                ExaResult(
                    url="https://www.producthunt.com/posts/test-brand",
                    title="Product Hunt",
                    text="great innovative reliable product",
                ),
            ],
        )

        feature = self.extractor._review_quality(exa)

        self.assertGreater(feature.value, 50.0)
        self.assertIn("1 review platforms", feature.raw_value)


class DiferenciacionExtractorTests(unittest.TestCase):
    def setUp(self):
        self.extractor = DiferenciacionExtractor()

    def test_unique_value_prop_rewards_specific_technical_positioning_and_proof(self):
        web = WebData(
            url="https://priorlabs.ai",
            title="One Model, Infinite Predictions",
            markdown_content=(
                "# One Model, Infinite Predictions\n\n"
                "Pre-trained tabular foundation models for making predictions on structured data.\n\n"
                "6K GITHUB STARS\n"
                "3M DOWNLOADS\n"
                "PUBLISHED IN NATURE\n"
            ),
        )

        feature = self.extractor._unique_value_prop(web)

        self.assertGreaterEqual(feature.value, 60.0)
        self.assertIn("specificity_hits=", feature.raw_value)
        self.assertIn("proof_points=", feature.raw_value)

    def test_unique_value_prop_stays_low_for_generic_claims_without_proof(self):
        web = WebData(
            url="https://generic.example",
            title="Generic SaaS",
            markdown_content=(
                "# Generic SaaS\n\n"
                "We help businesses grow and improve efficiency.\n"
                "Save time. Save money. Better results.\n"
            ),
        )

        feature = self.extractor._unique_value_prop(web)

        self.assertLessEqual(feature.value, 35.0)

    def test_unique_value_prop_rewards_signature_and_proof_language_for_frontier_brands(self):
        web = WebData(
            url="https://ricursive.com",
            title="Ricursive",
            markdown_content=(
                "# Ricursive\n\n"
                "We develop frontier AI methods to reinvent chip development.\n"
                "Ricursive Intelligence is a frontier AI lab focused on building self-improving systems.\n"
                "We are the team behind AlphaChip (Nature 2021) and DAC Best Paper 2023.\n"
            ),
        )

        feature = self.extractor._unique_value_prop(web)

        self.assertGreaterEqual(feature.value, 50.0)
        self.assertIn("proof_points=", feature.raw_value)
        self.assertIn("signature_hits=", feature.raw_value)

    def test_unique_value_prop_rewards_control_and_surface_bundle_for_cause_platforms(self):
        web = WebData(
            url="https://movements.mov/en",
            title="MOVEMENTS",
            markdown_content=(
                "# MOVEMENTS\n\n"
                "Convert your cause into an unstoppable movement. MOVEMENTS offers petitions, community, content and subscriptions to drive change.\n"
                "No algorithms limiting your reach. You maintain complete control over your audience.\n"
            ),
        )

        feature = self.extractor._unique_value_prop(web)

        self.assertGreaterEqual(feature.value, 45.0)
        self.assertIn("control_hits=", feature.raw_value)
        self.assertIn("cause_terms=", feature.raw_value)

    def test_generic_language_is_normalized_by_content_length(self):
        short_web = WebData(
            url="https://short.example",
            title="Short",
            markdown_content=(
                "We are a leading provider. "
                "Our innovative solutions help teams save time. "
                "We deliver scalable solutions. "
                "We help businesses grow."
            ),
        )
        long_web = WebData(
            url="https://long.example",
            title="Long",
            markdown_content=(
                " ".join(
                    [
                        "This product helps finance teams reconcile multi-entity close workflows with auditable approvals."
                    ] * 24
                )
                + " Leading provider. Innovative solutions. Save time. We help businesses grow."
            ),
        )

        short_score = self.extractor._generic_language(short_web)
        long_score = self.extractor._generic_language(long_web)

        self.assertGreater(short_score.value, long_score.value)
        self.assertIn("ratio=", short_score.raw_value)
        self.assertIn("ratio=", long_score.raw_value)

    def test_generic_language_low_ratio_stays_low_even_with_some_generic_phrases(self):
        web = WebData(
            url="https://example.com",
            title="Example",
            markdown_content=(
                " ".join(
                    [
                        "This platform automates supplier onboarding across legal, procurement, and finance systems."
                    ] * 18
                )
                + " Save time."
            ),
        )

        score = self.extractor._generic_language(web)

        self.assertLessEqual(score.value, 30.0)

    def test_brand_vocabulary_detects_signature_phrases_and_repeated_acronyms(self):
        web = WebData(
            url="https://ctgt.ai",
            title="CTGT",
            markdown_content=(
                "# CTGT\n\n"
                "The deterministic layer for frontier intelligence.\n"
                "CTGT helps teams govern mission critical applications.\n"
                "CTGT introduces a deterministic layer for frontier intelligence.\n"
            ),
        )

        feature = self.extractor._brand_vocabulary(web, exa=None, competitor_data=None)

        self.assertGreaterEqual(feature.value, 20.0)
        self.assertIn("acronyms=", feature.raw_value)
        self.assertIn("signature_phrases=", feature.raw_value)

    def test_brand_vocabulary_detects_repeated_all_caps_brand_name(self):
        web = WebData(
            url="https://movements.mov/en",
            title="MOVEMENTS",
            markdown_content=(
                "# MOVEMENTS\n\n"
                "MOVEMENTS helps you organize, scale and sustain your cause.\n"
                "At MOVEMENTS, everything you generate is yours.\n"
            ),
        )

        feature = self.extractor._brand_vocabulary(web, exa=None, competitor_data=None)

        self.assertGreaterEqual(feature.value, 10.0)
        self.assertIn("all_caps=", feature.raw_value)


class PresenciaExtractorTests(unittest.TestCase):
    def setUp(self):
        self.extractor = PresenciaExtractor()

    def _exa_mentions(self, brand_name: str = "Acme") -> ExaData:
        return ExaData(
            brand_name=brand_name,
            mentions=[
                ExaResult(
                    url="https://acme.com/blog/launch",
                    title="Acme launches new product",
                    text="Acme expands its launch motion with a new platform release.",
                    summary="Acme expands with a product release.",
                    score=0.9,
                ),
                ExaResult(
                    url="https://techcrunch.com/acme-funding",
                    title="Acme raises funding",
                    text="Acme is highlighted as a growing company.",
                    summary="Growing company profile.",
                    score=0.8,
                ),
                ExaResult(
                    url="https://random.com/roundup",
                    title="AI roundup",
                    text="Many vendors are covered in this roundup.",
                    summary="General roundup with many names.",
                    score=0.3,
                ),
            ],
            ai_visibility_results=[
                ExaResult(
                    url="https://example.com/acme-best-tools",
                    title="Acme in top AI tools",
                    text="Acme is recommended for enterprise teams.",
                    score=0.8,
                ),
                ExaResult(
                    url="https://example.com/general-roundup",
                    title="General AI roundup",
                    text="Acme appears in a broader list.",
                    score=0.5,
                ),
            ],
        )

    def test_web_presence_placeholder_page_scores_minimal(self):
        web = WebData(
            url="http://placeholder.example",
            title="Coming Soon",
            markdown_content="Coming soon. Buy this domain today.",
        )

        feature = self.extractor._web_presence(web)

        self.assertEqual(feature.value, 5.0)
        self.assertEqual(feature.raw_value["page_status"], "placeholder")
        self.assertIn("placeholder_detected", feature.raw_value["signals_detected"])

    def test_web_presence_normal_site_scores_high_with_structured_raw_value(self):
        web = WebData(
            url="https://example.com",
            title="Example Platform",
            meta_description="Example Platform helps finance teams move faster.",
            markdown_content=(
                "# Example Platform\n\n"
                "Example Platform helps finance teams move faster with approvals, docs, and automation.\n"
                "Pricing About Contact Docs Features Get started Privacy Terms.\n"
            ),
        )

        feature = self.extractor._web_presence(web)

        self.assertGreaterEqual(feature.value, 75.0)
        self.assertTrue(feature.raw_value["has_https"])
        self.assertEqual(feature.raw_value["page_status"], "live")
        self.assertIsInstance(feature.raw_value["evidence_snippet"], str)
        self.assertIn("https", feature.raw_value["signals_detected"])

    def test_web_presence_without_https_loses_signal(self):
        secure = WebData(
            url="https://example.com",
            title="Example",
            meta_description="Example is a real product site.",
            markdown_content="# Example\n\nExample is a real product site with pricing and contact.",
        )
        insecure = WebData(
            url="http://example.com",
            title="Example",
            meta_description="Example is a real product site.",
            markdown_content="# Example\n\nExample is a real product site with pricing and contact.",
        )

        secure_feature = self.extractor._web_presence(secure)
        insecure_feature = self.extractor._web_presence(insecure)

        self.assertGreater(secure_feature.value, insecure_feature.value)
        self.assertFalse(insecure_feature.raw_value["has_https"])

    def test_web_presence_without_meaningful_content_stays_low(self):
        web = WebData(
            url="https://example.com",
            title="Example",
            markdown_content="Login",
        )

        feature = self.extractor._web_presence(web)

        self.assertLessEqual(feature.value, 35.0)
        self.assertEqual(feature.raw_value["page_status"], "minimal")

    def test_social_footprint_without_social_data_degrades_gracefully(self):
        feature = self.extractor._social_footprint(social=None)

        self.assertEqual(feature.value, 15.0)
        self.assertEqual(feature.confidence, 0.3)
        self.assertEqual(feature.raw_value["reason"], "no_social_data")

    def test_social_footprint_with_multiple_platforms_is_structured(self):
        social = SocialData(
            brand_name="Example",
            platforms={
                "linkedin": PlatformMetrics(
                    platform="linkedin",
                    profile_url="https://linkedin.com/company/example",
                    followers_count=12000,
                    verified=True,
                    last_post_date="2026-04-10",
                    posts_last_30_days=6,
                ),
                "instagram": PlatformMetrics(
                    platform="instagram",
                    profile_url="https://instagram.com/example",
                    followers_count=8000,
                    verified=False,
                    last_post_date="2026-04-12",
                    posts_last_30_days=8,
                ),
            },
            total_followers=20000,
            avg_post_frequency=3,
        )

        feature = self.extractor._social_footprint(social=social)

        self.assertGreaterEqual(feature.value, 55.0)
        self.assertEqual(feature.raw_value["total_followers"], 20000)
        self.assertEqual(feature.raw_value["active_platforms_count"], 2)
        self.assertTrue(feature.raw_value["professional_presence"])
        self.assertTrue(feature.raw_value["consumer_presence"])
        self.assertEqual(len(feature.raw_value["platforms"]), 2)

    def test_social_footprint_rewards_verified_accounts(self):
        unverified = SocialData(
            brand_name="Example",
            platforms={
                "linkedin": PlatformMetrics(
                    platform="linkedin",
                    profile_url="https://linkedin.com/company/example",
                    followers_count=12000,
                    verified=False,
                    last_post_date="2026-04-10",
                    posts_last_30_days=3,
                )
            },
            total_followers=12000,
            avg_post_frequency=2,
        )
        verified = SocialData(
            brand_name="Example",
            platforms={
                "linkedin": PlatformMetrics(
                    platform="linkedin",
                    profile_url="https://linkedin.com/company/example",
                    followers_count=12000,
                    verified=True,
                    last_post_date="2026-04-10",
                    posts_last_30_days=3,
                )
            },
            total_followers=12000,
            avg_post_frequency=2,
        )

        unverified_feature = self.extractor._social_footprint(social=unverified)
        verified_feature = self.extractor._social_footprint(social=verified)

        self.assertGreater(verified_feature.value, unverified_feature.value)
        self.assertTrue(verified_feature.raw_value["platforms"][0]["verified"])

    def test_search_visibility_without_results_returns_low_neutral(self):
        feature = self.extractor._search_visibility(exa=None)

        self.assertEqual(feature.value, 15.0)
        self.assertEqual(feature.raw_value["search_results_count"], 0)
        self.assertEqual(feature.raw_value["evidence"], [])

    def test_search_visibility_with_few_results_stays_mid_low(self):
        exa = ExaData(
            brand_name="Acme",
            mentions=[
                ExaResult(
                    url="https://acme.com/about",
                    title="Acme",
                    text="Acme builds software for teams.",
                    score=0.7,
                ),
                ExaResult(
                    url="https://news.example.com/acme",
                    title="Acme profile",
                    text="Acme is covered in a profile.",
                    score=0.5,
                ),
            ],
        )

        feature = self.extractor._search_visibility(exa)

        self.assertGreaterEqual(feature.value, 20.0)
        self.assertLess(feature.value, 50.0)
        self.assertEqual(feature.raw_value["relevant_results_count"], 2)

    def test_search_visibility_rewards_many_results_and_own_url_top3(self):
        exa = self._exa_mentions()
        exa.mentions.extend(
            [
                ExaResult(
                    url=f"https://coverage{i}.example.com/acme",
                    title=f"Acme mention {i}",
                    text="Acme is the main subject of this article.",
                    score=0.7,
                )
                for i in range(6)
            ]
        )

        feature = self.extractor._search_visibility(exa)

        self.assertGreaterEqual(feature.value, 70.0)
        self.assertTrue(feature.raw_value["own_url_in_top3"])
        self.assertGreaterEqual(feature.raw_value["ai_visibility_signals"], 1)
        self.assertEqual(len(feature.raw_value["evidence"]), 3)

    def test_search_visibility_filters_low_subject_relevance(self):
        exa = ExaData(
            brand_name="Acme",
            mentions=[
                ExaResult(
                    url="https://roundup.example.com",
                    title="General software roundup",
                    text="Many brands are discussed here without focusing on one.",
                    score=0.8,
                ),
                ExaResult(
                    url="https://acme.com",
                    title="Acme",
                    text="Acme is the main subject here.",
                    score=0.8,
                ),
            ],
        )

        feature = self.extractor._search_visibility(exa)

        self.assertEqual(feature.raw_value["search_results_count"], 2)
        self.assertEqual(feature.raw_value["relevant_results_count"], 1)
        self.assertEqual(len(feature.raw_value["evidence"]), 1)

    def test_directory_presence_without_directories_is_zero(self):
        exa = ExaData(
            brand_name="Acme",
            mentions=[ExaResult(url="https://acme.com", title="Acme", text="Owned site")],
        )

        feature = self.extractor._directory_presence(exa)

        self.assertEqual(feature.value, 0.0)
        self.assertEqual(feature.raw_value["total_points"], 0)

    def test_directory_presence_with_only_tier2_is_limited(self):
        exa = ExaData(
            brand_name="Acme",
            mentions=[
                ExaResult(
                    url="https://producthunt.com/posts/acme",
                    title="Acme on Product Hunt",
                    text="Listing",
                ),
                ExaResult(
                    url="https://trustpilot.com/review/acme.com",
                    title="Acme reviews",
                    text="Review listing",
                ),
            ],
        )

        feature = self.extractor._directory_presence(exa)

        self.assertEqual(feature.value, 16.0)
        self.assertEqual(len(feature.raw_value["tier2_found"]), 2)
        self.assertEqual(feature.raw_value["tier1_found"], [])

    def test_directory_presence_with_tier1_and_tier2_mix_scores_higher(self):
        exa = ExaData(
            brand_name="Acme",
            mentions=[
                ExaResult(url="https://crunchbase.com/organization/acme", title="Crunchbase", text="Listing"),
                ExaResult(url="https://linkedin.com/company/acme", title="LinkedIn", text="Listing"),
                ExaResult(url="https://producthunt.com/posts/acme", title="Product Hunt", text="Listing"),
            ],
        )

        feature = self.extractor._directory_presence(exa)

        self.assertEqual(feature.value, 48.0)
        self.assertEqual(len(feature.raw_value["tier1_found"]), 2)
        self.assertEqual(len(feature.raw_value["tier2_found"]), 1)


class VitalidadExtractorTests(unittest.TestCase):
    """Cover the 3 features (content_recency, publication_cadence, momentum)."""

    def setUp(self):
        self.extractor = VitalidadExtractor()

    # ── content_recency ────────────────────────────────────────────────

    def _exa_with_dates(self, days_ago_list: list[int]) -> ExaData:
        from datetime import datetime, timedelta
        base = datetime.now()
        mentions = [
            ExaResult(
                url=f"https://example.com/article-{i}",
                title=f"Article {i}",
                text="content",
                published_date=(base - timedelta(days=d)).strftime("%Y-%m-%d"),
            )
            for i, d in enumerate(days_ago_list)
        ]
        return ExaData(brand_name="Test", mentions=mentions)

    def test_content_recency_recent_publication_scores_high(self):
        exa = self._exa_with_dates([3])
        features = self.extractor.extract(exa=exa)
        self.assertEqual(features["content_recency"].value, 100.0)

    def test_content_recency_30_days_is_mid_high(self):
        exa = self._exa_with_dates([25])
        features = self.extractor.extract(exa=exa)
        self.assertEqual(features["content_recency"].value, 85.0)

    def test_content_recency_6_months_drops_to_mid(self):
        exa = self._exa_with_dates([150])
        features = self.extractor.extract(exa=exa)
        self.assertEqual(features["content_recency"].value, 40.0)

    def test_content_recency_past_year_is_low(self):
        exa = self._exa_with_dates([250])
        features = self.extractor.extract(exa=exa)
        self.assertEqual(features["content_recency"].value, 20.0)

    def test_content_recency_over_365_days_is_very_low(self):
        exa = self._exa_with_dates([400])
        features = self.extractor.extract(exa=exa)
        self.assertEqual(features["content_recency"].value, 10.0)

    def test_content_recency_no_dates_returns_neutral_with_reason(self):
        import json
        features = self.extractor.extract(exa=None)
        fv = features["content_recency"]
        self.assertEqual(fv.value, 30.0)
        self.assertEqual(fv.source, "none")
        payload = json.loads(fv.raw_value)
        self.assertIsNone(payload["most_recent_date"])
        self.assertIsNone(payload["days_ago"])
        self.assertIsNone(payload["evidence_url"])
        self.assertEqual(payload["reason"], "no_dates_found")

    # ── publication_cadence ────────────────────────────────────────────

    def test_publication_cadence_fewer_than_2_dates_is_low(self):
        import json
        exa = self._exa_with_dates([15])
        features = self.extractor.extract(exa=exa)
        fv = features["publication_cadence"]
        self.assertEqual(fv.value, 20.0)
        payload = json.loads(fv.raw_value)
        self.assertEqual(payload["reason"], "insufficient_dates_12m")

    def test_publication_cadence_regular_rhythm_scores_high(self):
        # 3 dates roughly ~20 days apart → mean_gap < 30 → 90
        exa = self._exa_with_dates([10, 35, 60])
        features = self.extractor.extract(exa=exa)
        self.assertEqual(features["publication_cadence"].value, 90.0)

    def test_publication_cadence_moderate_rhythm_scores_mid(self):
        # 3 dates ~100 days apart → 90 <= mean < 180 → 50
        exa = self._exa_with_dates([5, 110, 215])
        features = self.extractor.extract(exa=exa)
        self.assertEqual(features["publication_cadence"].value, 50.0)

    # ── momentum ───────────────────────────────────────────────────────

    def test_momentum_without_llm_returns_heuristic_fallback(self):
        import json
        exa = self._exa_with_dates([30, 60])
        features = self.extractor.extract(exa=exa)
        fv = features["momentum"]
        self.assertEqual(fv.value, 50.0)
        self.assertEqual(fv.source, "heuristic_fallback")
        self.assertEqual(fv.confidence, 0.3)
        payload = json.loads(fv.raw_value)
        self.assertEqual(payload["reason"], "llm_unavailable")

    def test_momentum_with_llm_uses_structured_verdict(self):
        import json

        class FakeLLM:
            api_key = "sk-test"

            def analyze_momentum(self, mentions, brand_name):
                return {
                    "momentum_score": 82,
                    "verdict": "building",
                    "evidence": [
                        {
                            "quote": "shipped a new inference runtime",
                            "source_url": "https://example.com/article-0",
                            "signal": "positive",
                        }
                    ],
                    "reasoning": "Fresh product launches in the last quarter.",
                }

        extractor = VitalidadExtractor(llm=FakeLLM())
        exa = self._exa_with_dates([10, 40])
        features = extractor.extract(exa=exa)

        fv = features["momentum"]
        self.assertEqual(fv.value, 82.0)
        self.assertEqual(fv.source, "llm")
        self.assertEqual(fv.confidence, 0.85)
        payload = json.loads(fv.raw_value)
        self.assertEqual(payload["verdict"], "building")
        self.assertEqual(len(payload["evidence"]), 1)
        self.assertIn("shipped a new inference runtime", payload["evidence"][0]["quote"])

    def test_momentum_with_unclear_verdict_has_lower_confidence(self):
        import json

        class FakeLLM:
            api_key = "sk-test"

            def analyze_momentum(self, mentions, brand_name):
                return {
                    "momentum_score": 50,
                    "verdict": "unclear",
                    "evidence": [],
                    "reasoning": "Evidence insufficient.",
                }

        extractor = VitalidadExtractor(llm=FakeLLM())
        exa = self._exa_with_dates([20])
        features = extractor.extract(exa=exa)
        fv = features["momentum"]
        self.assertEqual(fv.confidence, 0.5)
        self.assertEqual(json.loads(fv.raw_value)["verdict"], "unclear")

    def test_momentum_with_no_recent_mentions_returns_fallback(self):
        import json

        class FakeLLM:
            api_key = "sk-test"

            def analyze_momentum(self, mentions, brand_name):
                raise AssertionError("should not be called when no recent mentions")

        extractor = VitalidadExtractor(llm=FakeLLM())
        # Only old mentions, outside the 6-month window
        exa = self._exa_with_dates([400, 500])
        features = extractor.extract(exa=exa)
        fv = features["momentum"]
        self.assertEqual(fv.source, "heuristic_fallback")
        self.assertEqual(json.loads(fv.raw_value)["reason"], "no_recent_mentions_6m")

    def test_extract_always_returns_three_features(self):
        features = self.extractor.extract(web=None, exa=None)
        self.assertEqual(
            set(features.keys()),
            {"content_recency", "publication_cadence", "momentum"},
        )

    # ── momentum — LLM contract negative tests ─────────────────────────

    def _make_momentum_llm(self, payload):
        """Helper: fake LLMAnalyzer that returns a fixed payload from analyze_momentum."""

        class FakeLLM:
            api_key = "sk-test"

            def analyze_momentum(self, mentions, brand_name):
                return payload

        return FakeLLM()

    def test_momentum_with_invalid_verdict_falls_back(self):
        import json

        llm = self._make_momentum_llm({
            "momentum_score": 80,
            "verdict": "thriving",  # not in the enum
            "evidence": [
                {
                    "quote": "shipped v2",
                    "source_url": "https://example.com/article-0",
                    "signal": "positive",
                }
            ],
            "reasoning": "Good stuff.",
        })
        extractor = VitalidadExtractor(llm=llm)
        features = extractor.extract(exa=self._exa_with_dates([10]))
        fv = features["momentum"]
        self.assertEqual(fv.source, "heuristic_fallback")
        self.assertEqual(fv.value, 50.0)
        payload = json.loads(fv.raw_value)
        self.assertEqual(payload["reason"], "llm_invalid_verdict")
        self.assertEqual(payload["got"], "thriving")

    def test_momentum_with_non_list_evidence_degrades_confidence(self):
        import json

        llm = self._make_momentum_llm({
            "momentum_score": 72,
            "verdict": "building",
            "evidence": "they shipped a lot",  # should be list
            "reasoning": "Clearly active.",
        })
        extractor = VitalidadExtractor(llm=llm)
        features = extractor.extract(exa=self._exa_with_dates([10]))
        fv = features["momentum"]
        # Still source=llm because verdict is valid, but degraded confidence.
        self.assertEqual(fv.source, "llm")
        self.assertEqual(fv.value, 72.0)
        self.assertEqual(fv.confidence, 0.5)
        payload = json.loads(fv.raw_value)
        self.assertEqual(payload["reason"], "llm_partial_evidence")
        self.assertEqual(payload["evidence"], [])

    def test_momentum_with_malformed_evidence_items_are_filtered(self):
        import json

        llm = self._make_momentum_llm({
            "momentum_score": 82,
            "verdict": "building",
            "evidence": [
                # Missing signal → dropped.
                {"quote": "launched new runtime", "source_url": "https://x.com/1"},
                # Wrong signal value → dropped.
                {"quote": "grew 3x", "source_url": "https://x.com/2", "signal": "bullish"},
                # Non-str quote → dropped.
                {"quote": 123, "source_url": "https://x.com/3", "signal": "positive"},
                # Valid → kept.
                {"quote": "hired 40 engineers",
                 "source_url": "https://x.com/4",
                 "signal": "positive"},
                # Non-dict → dropped.
                "random string",
            ],
            "reasoning": "Mix.",
        })
        extractor = VitalidadExtractor(llm=llm)
        features = extractor.extract(exa=self._exa_with_dates([10]))
        fv = features["momentum"]
        self.assertEqual(fv.source, "llm")
        self.assertEqual(fv.confidence, 0.5)
        payload = json.loads(fv.raw_value)
        self.assertEqual(len(payload["evidence"]), 1)
        self.assertEqual(payload["evidence"][0]["quote"], "hired 40 engineers")
        self.assertEqual(payload["reason"], "llm_partial_evidence")

    def test_momentum_with_all_evidence_items_malformed_flags_partial(self):
        import json

        llm = self._make_momentum_llm({
            "momentum_score": 64,
            "verdict": "maintaining",
            "evidence": [
                {"quote": "something"},  # missing fields → dropped
                "not a dict",
            ],
            "reasoning": "Little signal.",
        })
        extractor = VitalidadExtractor(llm=llm)
        features = extractor.extract(exa=self._exa_with_dates([10]))
        fv = features["momentum"]
        self.assertEqual(fv.source, "llm")
        self.assertEqual(fv.value, 64.0)
        self.assertEqual(fv.confidence, 0.5)
        payload = json.loads(fv.raw_value)
        self.assertEqual(payload["reason"], "llm_partial_evidence")
        self.assertEqual(payload["evidence"], [])


class WebCollectorTests(unittest.TestCase):
    def test_clean_markdown_removes_cookie_banner_noise(self):
        collector = WebCollector()
        raw = """
![Revisit consent button](https://example.com/revisit.svg)
We value your privacy
Accept All
Reject All
Customise

# Prior Labs

Tabular foundation models for real-world data.
"""
        cleaned = collector._clean_markdown_content(raw)

        self.assertNotIn("We value your privacy", cleaned)
        self.assertNotIn("Accept All", cleaned)
        self.assertIn("# Prior Labs", cleaned)
        self.assertIn("Tabular foundation models", cleaned)

    def test_clean_markdown_trims_leading_ui_preamble(self):
        collector = WebCollector()
        raw = """
NecessaryAlways Active

Functional

Analytics

[Deploy now](https://example.com/deploy)

One Model, Infinite Predictions

Tabular foundation models for real-world data.
"""

        cleaned = collector._clean_markdown_content(raw)

        self.assertTrue(cleaned.startswith("One Model, Infinite Predictions"))
        self.assertNotIn("NecessaryAlways Active", cleaned)
        self.assertNotIn("Functional", cleaned)

    def test_clean_markdown_discards_firecrawl_auth_prompt(self):
        collector = WebCollector()
        raw = """
Turn websites into LLM-ready data

Welcome! To get started, authenticate with your Firecrawl account.

1. Login with browser
2. Enter API key manually
"""

        cleaned = collector._clean_markdown_content(raw)

        self.assertEqual(cleaned, "")

    def test_trim_to_title_drops_navigation_before_detected_title(self):
        collector = WebCollector()
        content = """
Models

Deployment

One Model, Infinite Predictions

Tabular foundation models for real-world data.
"""

        trimmed = collector._trim_to_title(content.strip(), "One Model, Infinite Predictions")

        self.assertTrue(trimmed.startswith("One Model, Infinite Predictions"))
        self.assertNotIn("Models", trimmed)

    def test_html_to_markdown_fallback_extracts_title_meta_and_body(self):
        collector = WebCollector()
        html = """
<html>
  <head>
    <title>CTGT</title>
    <meta name="description" content="Deterministic intelligence control for frontier AI." />
  </head>
  <body>
    <nav>Home Pricing Docs</nav>
    <h1>Deterministic control for frontier AI</h1>
    <p>Runtime policy enforcement, steering, and audit trails for production systems.</p>
    <script>console.log("ignore me")</script>
  </body>
</html>
"""

        content = collector._html_to_markdown_fallback(html)

        self.assertIn("# CTGT", content)
        self.assertIn("Deterministic intelligence control for frontier AI.", content)
        self.assertIn("Runtime policy enforcement, steering, and audit trails", content)
        self.assertNotIn("ignore me", content)

    def test_extract_canonical_metadata_captures_alternate_domains(self):
        collector = WebCollector()
        html = """
<html>
  <head>
    <link rel="canonical" href="https://movements.dev/en" />
    <link rel="alternate" href="https://movements.dev/es" hreflang="es" />
    <meta property="og:url" content="https://movements.dev/en" />
    <script type="application/ld+json">{"url":"https://movements.dev/en/search?q=test"}</script>
  </head>
</html>
"""

        canonical_url, alternate_domains = collector._extract_canonical_metadata(html)

        self.assertEqual(canonical_url, "https://movements.dev/en")
        self.assertIn("movements.dev", alternate_domains)

    def test_scrape_uses_html_fallback_when_firecrawl_is_empty(self):
        collector = WebCollector()
        html = """
<html>
  <head>
    <title>Poetiq</title>
    <meta name="description" content="The fastest path to safe super intelligence." />
  </head>
  <body>
    <h1>The fastest path to safe super intelligence</h1>
    <p>Better reasoning systems for aligned advanced AI.</p>
  </body>
</html>
"""

        with patch.object(WebCollector, "_run_firecrawl", return_value={"content": ""}):
            with patch.object(WebCollector, "_fetch_html_fallback", return_value=(html, "")):
                data = collector.scrape("https://poetiq.ai/")

        self.assertEqual(data.title, "Poetiq")
        self.assertIn("safe super intelligence", data.markdown_content.lower())
        self.assertEqual(data.meta_description, "The fastest path to safe super intelligence.")
        self.assertEqual(data.error, "")


class ExaCollectorTests(unittest.TestCase):
    def test_brand_query_includes_domain_anchor_when_available(self):
        collector = ExaCollector(api_key="test")

        query = collector._brand_query("Movements", "https://movements.mov/en", "news")

        self.assertIn('"Movements"', query)
        self.assertIn('"movements.mov"', query)
        self.assertTrue(query.endswith("news"))

    def test_brand_query_works_without_domain(self):
        collector = ExaCollector(api_key="test")

        query = collector._brand_query("CTGT", None, "brand company")

        self.assertEqual(query, '"CTGT" brand company')


class CoherenciaExtractorTests(unittest.TestCase):
    def test_skip_visual_analysis_uses_heuristic_fallback(self):
        web = WebData(
            url="https://example.com",
            title="Example",
            markdown_content="Brand guidelines and logo usage live here.",
        )
        extractor = CoherenciaExtractor(skip_visual_analysis=True)

        feature = extractor._visual_consistency(web)

        self.assertEqual(feature.source, "web_scrape_heuristic")
        self.assertIn("visual analysis skipped", feature.raw_value)

    def test_messaging_consistency_extracts_category_from_hero_copy(self):
        web = WebData(
            url="https://priorlabs.ai",
            title="One Model, Infinite Predictions",
            markdown_content=(
                "# One Model, Infinite Predictions\n\n"
                "Pre-trained tabular foundation models for making predictions on structured data.\n\n"
                "Talk to sales\n"
            ),
        )
        exa = ExaData(
            brand_name="Prior Labs",
            mentions=[
                ExaResult(
                    url="https://example.com/post-1",
                    title="Prior Labs launches tabular foundation model",
                    text="The company builds pre-trained foundation models for structured data prediction.",
                )
            ],
        )
        extractor = CoherenciaExtractor()

        feature = extractor._messaging_consistency(web, exa)

        self.assertGreater(feature.value, 60.0)
        self.assertIn("tabular foundation models", feature.raw_value)

    def test_messaging_consistency_with_web_category_but_no_exa_data_is_not_default_failure(self):
        web = WebData(
            url="https://example.com",
            title="Deterministic AI",
            markdown_content=(
                "# Deterministic AI\n\n"
                "A deterministic policy layer for enterprise AI governance.\n"
            ),
        )
        extractor = CoherenciaExtractor()

        feature = extractor._messaging_consistency(web, exa=None)

        self.assertEqual(feature.value, 55.0)
        self.assertIn("policy layer", feature.raw_value)

    def test_cross_channel_coherence_is_not_overly_punitive_for_startup_touchpoints(self):
        web = WebData(
            url="https://poetiq.ai/",
            title="Poetiq",
            markdown_content=(
                "# Poetiq\n\n"
                "Secure your place for the next generation of reasoning.\n"
                "Your request has been received. We will be in touch shortly.\n"
            ),
        )
        exa = ExaData(
            brand_name="Poetiq",
            mentions=[
                ExaResult(
                    url="https://poetiq.ai/blog/launch",
                    title="Poetiq launch",
                    text="Poetiq launches reasoning research platform.",
                )
            ],
        )
        extractor = CoherenciaExtractor()

        feature = extractor._cross_channel_coherence(web, exa)

        self.assertGreaterEqual(feature.value, 50.0)
        self.assertIn("touchpoint=True", feature.raw_value)
        self.assertIn("brand_url_mentioned=True", feature.raw_value)

    def test_cross_channel_coherence_stays_low_when_site_has_no_touchpoints(self):
        web = WebData(
            url="https://example.com/",
            title="Example",
            markdown_content="# Example\n\nMinimal landing page.\n",
        )
        extractor = CoherenciaExtractor()

        feature = extractor._cross_channel_coherence(web, exa=None)

        self.assertLessEqual(feature.value, 25.0)

    def test_cross_channel_coherence_recognizes_membership_and_creation_flows(self):
        web = WebData(
            url="https://movements.mov/en",
            title="MOVEMENTS",
            markdown_content=(
                "# MOVEMENTS\n\n"
                "Start the movement.\n"
                "Sign In\n"
                "Sign Up\n"
                "Create your petition\n"
                "All-in-one to create a movement.\n"
                "Privacy Policy\n"
                "Terms\n"
            ),
        )
        extractor = CoherenciaExtractor()

        feature = extractor._cross_channel_coherence(web, exa=None)

        self.assertGreaterEqual(feature.value, 50.0)
        self.assertIn("touchpoint=True", feature.raw_value)
        self.assertIn("owned_surface=True", feature.raw_value)

    def test_cross_channel_coherence_accepts_alternate_domains_as_brand_mentions(self):
        web = WebData(
            url="https://movements.mov/en",
            canonical_url="https://movements.dev/en",
            alternate_domains=["movements.dev"],
            title="MOVEMENTS",
            markdown_content="# MOVEMENTS\n\nJoin the movement.\n",
        )
        exa = ExaData(
            brand_name="Movements",
            mentions=[
                ExaResult(
                    url="https://movements.dev/en/blog/launch",
                    title="MOVEMENTS launch",
                    text="Movements launches its petition platform.",
                )
            ],
        )
        extractor = CoherenciaExtractor()

        feature = extractor._cross_channel_coherence(web, exa)

        self.assertIn("brand_url_mentioned=True", feature.raw_value)
        self.assertIn("movements.dev", feature.raw_value)


if __name__ == "__main__":
    unittest.main()
