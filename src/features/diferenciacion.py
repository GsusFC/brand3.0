"""
Diferenciación feature extractor.

Measures if the brand says something DIFFERENT from competitors,
or if it's generic noise.

Data sources: web scrape, Exa competitor analysis, competitor web comparison
"""

import re
from collections import Counter
from ..models.brand import FeatureValue
from ..collectors.web_collector import WebData
from ..collectors.exa_collector import ExaData
from .authenticity import AuthenticityAnalyzer
from ..collectors.competitor_collector import CompetitorData


# Massively generic marketing phrases — red flag for differentiation
GENERIC_PHRASES = [
    "best in class", "cutting edge", "world class", "state of the art",
    "innovative solutions", "leading provider", "industry leading",
    "next level", "game changer", "disrupting", "revolutionary",
    "seamless", "end to end", "one stop shop", "turnkey",
    "synergy", "empower", "leverage", "holistic approach",
    "customer centric", "data driven", "scalable solutions",
    "we are passionate", "our mission is", "we believe in",
    "driving results", "unlocking potential", "transforming",
    "award winning", "trusted by", "global leader",
    "committed to excellence", "quality service", "exceed expectations",
    "value added", "best practices", "thought leader",
    "strategic partner", "trusted partner", "results oriented",
]

# Generic value propositions
GENERIC_VALUE_PROPS = [
    "save time", "save money", "increase revenue", "reduce costs",
    "improve efficiency", "boost productivity", "streamline operations",
    "better results", "faster growth", "competitive advantage",
    "easy to use", "user friendly", "all in one",
    "we help businesses grow", "we help companies succeed",
]


class DiferenciacionExtractor:
    """Extract diferenciación features."""

    @staticmethod
    def _sentence_count(content: str) -> int:
        """Count substantial sentence-like chunks for normalization."""
        chunks = re.split(r"[.!?\n]+", content)
        substantial = [chunk for chunk in chunks if len(chunk.split()) >= 3]
        return max(len(substantial), 1)

    def extract(self, web: WebData = None, exa: ExaData = None,
                competitor_webs: list[WebData] = None,
                competitor_data: CompetitorData = None,
                screenshot_url: str = None) -> dict[str, FeatureValue]:
        features = {}
        features["unique_value_prop"] = self._unique_value_prop(web)
        features["generic_language_score"] = self._generic_language(web)
        features["competitor_distance"] = self._competitor_distance(
            web, exa, competitor_webs, competitor_data
        )
        features["brand_vocabulary"] = self._brand_vocabulary(web, exa, competitor_data)

        # ── Brand authenticity analysis ──
        if web and not web.error:
            auth_analyzer = AuthenticityAnalyzer()
            auth_result = auth_analyzer.analyze(web, exa, screenshot_url)

            features["content_authenticity"] = FeatureValue(
                "content_authenticity",
                auth_result.content_authenticity,
                raw_value=f"AI patterns detected, score={auth_result.content_authenticity:.0f}",
                confidence=auth_result.confidence,
                source="content_analysis",
            )
            features["brand_personality"] = FeatureValue(
                "brand_personality",
                auth_result.brand_personality,
                raw_value=f"personality score={auth_result.brand_personality:.0f}",
                confidence=auth_result.confidence,
                source="content_analysis",
            )

        return features

    def _unique_value_prop(self, web: WebData = None) -> FeatureValue:
        """Does the brand clearly articulate what makes it different?"""
        if not web or web.error:
            return FeatureValue("unique_value_prop", 0.0, confidence=0.3, source="none")

        content = web.markdown_content.lower()

        # Look for differentiation signals
        diff_signals = [
            "unlike", "different from", "only one", "first to",
            "unique", "exclusively", "pioneered", "invented",
            "here's what makes us", "why we're different",
            "our approach", "how we're different",
            "what sets us apart", "we don't",
        ]

        diff_count = sum(1 for s in diff_signals if s in content)

        # Look for specific numbers/proof points
        proof_signals = re.findall(r'\d+%\s+\w+|\d+x\s+\w+|\$\d+|\d+\+?\s+(?:customers|users|clients|companies)', content)
        has_proof = len(proof_signals) > 0

        score = 20.0  # baseline
        score += min(diff_count * 15, 50)
        if has_proof:
            score += 20

        # Check first 500 chars for a clear positioning statement
        first_chunk = web.markdown_content[:500].lower()
        has_positioning = any(s in first_chunk for s in [
            "we are the", "we're the", "the only", "built for",
            "designed for", "made for", "for teams who",
        ])
        if has_positioning:
            score += 10

        return FeatureValue(
            "unique_value_prop",
            min(score, 100.0),
            raw_value=f"diff_signals={diff_count}, proof_points={len(proof_signals)}",
            confidence=0.6,
            source="web_scrape",
        )

    def _generic_language(self, web: WebData = None) -> FeatureValue:
        """
        How much generic vs specific language does the brand use?
        Returns HIGH score = more generic (inverted in rules to cap diferenciación).
        """
        if not web or web.error:
            return FeatureValue("generic_language_score", 50.0, confidence=0.3, source="none")

        content = web.markdown_content.lower()
        sentence_count = self._sentence_count(content)

        # Count generic phrases
        generic_hits = sum(content.count(p) for p in GENERIC_PHRASES)
        generic_prop_hits = sum(content.count(p) for p in GENERIC_VALUE_PROPS)

        total_generic = generic_hits + generic_prop_hits
        generic_ratio = total_generic / sentence_count

        # Ratio of generic statements to meaningful sentences.
        if generic_ratio >= 0.35:
            score = 90.0  # Very generic
        elif generic_ratio >= 0.20:
            score = 70.0
        elif generic_ratio >= 0.10:
            score = 50.0
        elif generic_ratio >= 0.03:
            score = 30.0
        else:
            score = 15.0  # Very specific/original

        return FeatureValue(
            "generic_language_score",
            score,
            raw_value=(
                f"generic_occurrences={total_generic}, "
                f"sentences={sentence_count}, ratio={generic_ratio:.2f}"
            ),
            confidence=0.7,
            source="web_scrape",
        )

    def _competitor_distance(self, web: WebData = None, exa: ExaData = None,
                              competitor_webs: list[WebData] = None,
                              competitor_data: CompetitorData = None) -> FeatureValue:
        """
        How different is this brand from its competitors?
        Uses real competitor web content when available for deep comparison.
        """
        if not web or web.error:
            return FeatureValue("competitor_distance", 30.0, confidence=0.3, source="none")

        # Best path: use CompetitorData with full web comparisons
        if competitor_data and competitor_data.comparisons:
            return self._distance_from_competitor_data(competitor_data)

        # Fallback: use competitor_webs list (legacy path)
        if competitor_webs:
            return self._distance_from_web_list(web, competitor_webs)

        # Fallback: use Exa competitor snippets
        if exa and exa.competitors:
            return self._distance_from_exa(web, exa)

        # No data
        return FeatureValue(
            "competitor_distance", 50.0,
            raw_value="no competitor data",
            confidence=0.3, source="web_scrape",
        )

    def _distance_from_competitor_data(self, competitor_data: CompetitorData) -> FeatureValue:
        """Compute distance using real competitor web comparisons."""
        comparisons = competitor_data.comparisons
        if not comparisons:
            return FeatureValue("competitor_distance", 50.0, confidence=0.3, source="none")

        # Use average distance across all competitors
        avg_dist = competitor_data.avg_distance
        score = avg_dist * 100  # Convert to 0-100 scale

        # Find the closest competitor (most similar = least differentiated)
        closest = min(comparisons, key=lambda c: c.overall_distance)
        most_different = max(comparisons, key=lambda c: c.overall_distance)

        raw_parts = [
            f"avg_distance={avg_dist:.2f}",
            f"closest={closest.competitor_name}({closest.overall_distance:.2f})",
            f"most_different={most_different.competitor_name}({most_different.overall_distance:.2f})",
            f"competitors_analyzed={len(comparisons)}",
        ]

        # Bonus: if brand has unique terms vs all competitors
        all_brand_unique = set()
        for c in comparisons:
            all_brand_unique.update(c.brand_unique_terms)
        if len(all_brand_unique) > 10:
            score = min(score + 5, 100.0)

        return FeatureValue(
            "competitor_distance",
            round(score, 1),
            raw_value=" | ".join(raw_parts),
            confidence=0.8,
            source="competitor_web_comparison",
        )

    def _distance_from_web_list(self, web: WebData, competitor_webs: list[WebData]) -> FeatureValue:
        """Compute distance using a simple list of competitor WebData."""
        brand_keywords = self._extract_keywords(web.markdown_content)
        comp_text = " ".join(w.markdown_content[:2000] for w in competitor_webs if w and not w.error)
        comp_keywords = self._extract_keywords(comp_text)

        if not comp_keywords:
            return FeatureValue("competitor_distance", 50.0, confidence=0.3, source="web_scrape")

        overlap = len(brand_keywords & comp_keywords)
        total = len(brand_keywords | comp_keywords)
        similarity = overlap / total if total > 0 else 0
        distance = (1 - similarity) * 100

        return FeatureValue(
            "competitor_distance",
            distance,
            raw_value=f"keyword_similarity={similarity:.2f}, competitors={len(competitor_webs)}",
            confidence=0.55,
            source="web_scrape+competitor_webs",
        )

    def _distance_from_exa(self, web: WebData, exa: ExaData) -> FeatureValue:
        """Fallback: compute distance using Exa competitor text snippets."""
        brand_keywords = self._extract_keywords(web.markdown_content)
        competitor_text = " ".join(
            (r.text or "")[:1000] for r in exa.competitors[:5]
        )
        comp_keywords = self._extract_keywords(competitor_text)

        if not comp_keywords:
            return FeatureValue("competitor_distance", 50.0, confidence=0.3, source="web_scrape")

        overlap = len(brand_keywords & comp_keywords)
        total = len(brand_keywords | comp_keywords)
        similarity = overlap / total if total > 0 else 0
        distance = (1 - similarity) * 100

        return FeatureValue(
            "competitor_distance",
            distance,
            raw_value=f"keyword_similarity={similarity:.2f} (from exa snippets)",
            confidence=0.4,
            source="web_scrape+exa",
        )

    def _brand_vocabulary(self, web: WebData = None, exa: ExaData = None,
                          competitor_data: CompetitorData = None) -> FeatureValue:
        """
        Does the brand have its own recognizable terms, phrases, or concepts?
        Bonus if terms are unique vs competitors.
        """
        if not web or web.error:
            return FeatureValue("brand_vocabulary", 0.0, confidence=0.3, source="none")

        content = web.markdown_content

        # Look for trademark symbols
        trademarks = re.findall(r'\b\w+[®™]\b', content)

        # Look for branded terms (capitalized multi-word phrases that appear 2+ times)
        # This catches things like "SmartDeploy", "CloudSync" etc.
        branded_pattern = re.findall(r'\b[A-Z][a-z]+[A-Z][a-zA-Z]*\b', content)
        branded_counter = Counter(branded_pattern)
        branded_terms = [t for t, c in branded_counter.items() if c >= 2]

        # Look for coined phrases in quotes
        coined = re.findall(r'"([^"]{5,40})"', content)

        score = 0.0
        score += min(len(trademarks) * 20, 40)
        score += min(len(branded_terms) * 15, 40)
        score += min(len(coined) * 5, 20)

        raw_parts = [
            f"trademarks={len(trademarks)}",
            f"branded_terms={len(branded_terms)}",
            f"coined={len(coined)}",
        ]

        # Bonus: check if branded terms are unique vs competitors
        if competitor_data and competitor_data.comparisons:
            brand_kw = set(t.lower() for t in branded_terms)
            if brand_kw:
                all_comp_kw = set()
                for comp in competitor_data.competitors:
                    if comp.web_data and comp.web_data.markdown_content:
                        comp_branded = re.findall(
                            r'\b[A-Z][a-z]+[A-Z][a-zA-Z]*\b',
                            comp.web_data.markdown_content
                        )
                        all_comp_kw.update(t.lower() for t in comp_branded)

                unique_terms = brand_kw - all_comp_kw
                if unique_terms:
                    uniqueness_bonus = min(len(unique_terms) * 10, 25)
                    score += uniqueness_bonus
                    raw_parts.append(f"unique_vs_competitors={len(unique_terms)}")

        return FeatureValue(
            "brand_vocabulary",
            min(score, 100.0),
            raw_value=", ".join(raw_parts),
            confidence=0.7,
            source="web_scrape" + ("+competitor_comparison" if competitor_data else ""),
        )

    @staticmethod
    def _extract_keywords(text: str, top_n: int = 30) -> set:
        """Extract top keywords from text."""
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                     "being", "have", "has", "had", "do", "does", "did", "will",
                     "would", "could", "should", "may", "might", "can", "shall",
                     "to", "of", "in", "for", "on", "with", "at", "by", "from",
                     "as", "into", "through", "during", "before", "after", "and",
                     "but", "or", "nor", "not", "so", "yet", "both", "either",
                     "its", "our", "your", "their", "this", "that", "these",
                     "it", "we", "you", "they", "he", "she", "i", "me",
                     "more", "most", "other", "some", "such", "no", "only",
                     "own", "same", "than", "too", "very", "just", "about"}
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        words = [w for w in words if w not in stopwords]
        return set(w for w, _ in Counter(words).most_common(top_n))
