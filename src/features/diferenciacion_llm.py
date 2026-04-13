"""
Diferenciación feature extractor — LLM-powered.

Uses LLM to judge brand uniqueness instead of keyword counting.
Falls back to heuristic if LLM fails.
"""

from ..models.brand import FeatureValue
from ..collectors.web_collector import WebData
from ..collectors.exa_collector import ExaData
from ..collectors.competitor_collector import CompetitorData
from .llm_analyzer import LLMAnalyzer
from .diferenciacion import DiferenciacionExtractor


class DiferenciacionLLMExtractor(DiferenciacionExtractor):
    """LLM-enhanced diferenciación extractor."""

    def __init__(self, llm: LLMAnalyzer = None):
        super().__init__()
        self.llm = llm or LLMAnalyzer()

    def extract(self, web: WebData = None, exa: ExaData = None,
                competitor_webs: list = None,
                competitor_data = None,
                screenshot_url: str = None) -> dict[str, FeatureValue]:

        # Start with heuristic features (includes authenticity)
        features = super().extract(web, exa, competitor_webs, competitor_data, screenshot_url)

        if not web or web.error or not self.llm.api_key:
            return features

        # ── LLM: Positioning analysis ──
        print("  [LLM] Analyzing positioning...")
        positioning = self.llm.analyze_positioning(web.markdown_content, exa.brand_name if exa else "unknown")
        if positioning:
            # Override unique_value_prop based on LLM judgment
            clarity = positioning.get("positioning_clarity", 50)
            distinctive = len(positioning.get("distinctive_concepts", []))
            uvp_score = min(clarity + (distinctive * 10), 100)
            features["unique_value_prop"] = FeatureValue(
                "unique_value_prop", uvp_score,
                raw_value=f"category: {positioning.get('category', '?')}, "
                          f"audience: {positioning.get('target_audience', '?')}, "
                          f"distinctive: {positioning.get('distinctive_concepts', [])}",
                confidence=0.85,
                source="llm",
            )

        # ── LLM: Differentiation analysis ──
        print("  [LLM] Analyzing differentiation...")
        comp_text = ""
        if exa and exa.competitors:
            comp_text = " ".join((r.text or "")[:300] for r in exa.competitors[:3])

        diff = self.llm.analyze_differentiation(
            web.markdown_content, exa.brand_name if exa else "unknown", comp_text
        )
        if diff:
            uniqueness = diff.get("uniqueness_score", 50)
            features["generic_language_score"] = FeatureValue(
                "generic_language_score",
                100 - uniqueness,  # inverted: high uniqueness = low generic
                raw_value=f"uniqueness={uniqueness}, "
                          f"generic: {diff.get('generic_phrases', [])[:3]}, "
                          f"unique: {diff.get('unique_phrases', [])[:3]}",
                confidence=0.85,
                source="llm",
            )

        return features
