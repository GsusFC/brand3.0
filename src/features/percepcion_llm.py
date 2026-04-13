"""
Percepción feature extractor — LLM-powered.

Uses LLM for nuanced sentiment analysis instead of keyword counting.
Falls back to heuristic if LLM fails.
"""

from ..models.brand import FeatureValue
from ..collectors.web_collector import WebData
from ..collectors.exa_collector import ExaData
from .llm_analyzer import LLMAnalyzer
from .percepcion import PercepcionExtractor


class PercepcionLLMExtractor(PercepcionExtractor):
    """LLM-enhanced percepción extractor."""

    def __init__(self, llm: LLMAnalyzer = None):
        super().__init__()
        self.llm = llm or LLMAnalyzer()

    def extract(self, web: WebData = None, exa: ExaData = None) -> dict[str, FeatureValue]:
        # Start with heuristic features
        features = super().extract(web, exa)

        if not exa or not self.llm.api_key:
            return features

        # ── LLM: Sentiment analysis ──
        print("  [LLM] Analyzing sentiment...")
        mentions_text = [
            ((r.text or "") + " " + (r.summary or ""))[:300]
            for r in exa.mentions + exa.news
            if (r.text or r.summary)
        ]

        if not mentions_text:
            return features

        sentiment = self.llm.analyze_sentiment(
            mentions_text, exa.brand_name
        )

        if sentiment:
            # Override sentiment_score with LLM judgment
            llm_score = sentiment.get("sentiment_score", 50)
            features["sentiment_score"] = FeatureValue(
                "sentiment_score",
                llm_score,
                raw_value=f"LLM: {sentiment.get('overall_sentiment', '?')}, "
                          f"positive: {sentiment.get('positive_signals', [])[:2]}, "
                          f"negative: {sentiment.get('negative_signals', [])[:2]}",
                confidence=0.85,
                source="llm",
            )

            # Override controversy_flag with LLM judgment
            controversy = sentiment.get("controversy_detected", False)
            if controversy:
                details = sentiment.get("controversy_details", "")
                features["controversy_flag"] = FeatureValue(
                    "controversy_flag", 75.0,
                    raw_value=f"LLM detected: {details}",
                    confidence=0.9,
                    source="llm",
                )
            else:
                features["controversy_flag"] = FeatureValue(
                    "controversy_flag", 0.0,
                    raw_value="LLM: no controversy detected",
                    confidence=0.9,
                    source="llm",
                )

        return features
