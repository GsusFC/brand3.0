"""
Vitalidad feature extractor.

Measures if the brand is ALIVE — publishing, evolving, active.
Data sources: web scrape, Exa search, social APIs (TODO)
"""

import re
from datetime import datetime, timedelta
from ..models.brand import FeatureValue
from ..collectors.web_collector import WebData
from ..collectors.exa_collector import ExaData


class VitalidadExtractor:
    """Extract vitalidad features."""

    def extract(self, web: WebData = None, exa: ExaData = None) -> dict[str, FeatureValue]:
        features = {}
        features["content_frequency"] = self._content_frequency(web, exa)
        features["content_recency"] = self._content_recency(web, exa)
        features["growth_signals"] = self._growth_signals(exa)
        features["tech_modernity"] = self._tech_modernity(web)
        features["evolution_signs"] = self._evolution_signs(exa)
        return features

    def _content_frequency(self, web: WebData = None, exa: ExaData = None) -> FeatureValue:
        """How often does the brand publish content?"""
        # TODO: Real social API for post frequency
        # For now, proxy from Exa news coverage + web content signals

        content = ""
        if web:
            content = web.markdown_content.lower()

        # Blog signals
        has_blog = any(s in content for s in ["blog", "articles", "posts", "news"])
        date_patterns = re.findall(r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2},?\s+\d{4}', content)
        date_patterns += re.findall(r'\d{1,2}/\d{1,2}/\d{4}', content)
        date_patterns += re.findall(r'\d{4}-\d{2}-\d{2}', content)

        score = 0.0
        if has_blog:
            score += 30
        if len(date_patterns) >= 5:
            score += 40
        elif len(date_patterns) >= 2:
            score += 20
        elif len(date_patterns) >= 1:
            score += 10

        # Exa news volume as proxy for publishing frequency
        if exa and len(exa.news) >= 5:
            score += 30
        elif exa and len(exa.news) >= 2:
            score += 15

        return FeatureValue(
            "content_frequency",
            min(score, 100.0),
            raw_value=f"blog={has_blog}, dates_found={len(date_patterns)}, news={len(exa.news) if exa else 0}",
            confidence=0.5,
            source="web_scrape+exa",
        )

    def _content_recency(self, web: WebData = None, exa: ExaData = None) -> FeatureValue:
        """When was the last time content was published?"""
        dates = []

        # Extract dates from Exa results
        if exa:
            for result in exa.mentions + exa.news:
                if result.published_date and result.published_date != "None":
                    try:
                        # Try parsing various date formats
                        for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%B %d, %Y"]:
                            try:
                                d = datetime.strptime(result.published_date[:10], fmt)
                                dates.append(d)
                                break
                            except ValueError:
                                continue
                    except Exception:
                        pass

        if not dates:
            return FeatureValue("content_recency", 30.0, confidence=0.3, source="none")

        most_recent = max(dates)
        now = datetime.now()
        days_ago = (now - most_recent).days

        if days_ago <= 7:
            score = 100.0
        elif days_ago <= 30:
            score = 85.0
        elif days_ago <= 90:
            score = 65.0
        elif days_ago <= 180:
            score = 40.0
        elif days_ago <= 365:
            score = 20.0
        else:
            score = 10.0

        return FeatureValue(
            "content_recency",
            score,
            raw_value=f"most recent: {most_recent.strftime('%Y-%m-%d')} ({days_ago} days ago)",
            confidence=0.7,
            source="exa",
        )

    def _growth_signals(self, exa: ExaData = None) -> FeatureValue:
        """Is the brand growing? Hiring, new products, expansion?"""
        if not exa:
            return FeatureValue("growth_signals", 30.0, confidence=0.3, source="none")

        growth_keywords = [
            "raised", "funding", "series", "hiring", "expanding",
            "new product", "launched", "growth", "revenue",
            "partnership", "acquisition", "ipo", "new office",
            "headcount", "employees doubled", "record",
        ]

        mentions_text = " ".join(
            (r.text or "") + " " + (r.summary or "")
            for r in exa.mentions + exa.news
        ).lower()

        hits = sum(1 for kw in growth_keywords if kw in mentions_text)

        if hits >= 5:
            score = 90.0
        elif hits >= 3:
            score = 70.0
        elif hits >= 1:
            score = 45.0
        else:
            score = 25.0

        return FeatureValue(
            "growth_signals",
            score,
            raw_value=f"{hits} growth keywords found",
            confidence=0.6,
            source="exa",
        )

    def _tech_modernity(self, web: WebData = None) -> FeatureValue:
        """Does the website use modern technology?"""
        if not web or web.error:
            return FeatureValue("tech_modernity", 0.0, confidence=0.5, source="web_scrape")

        content = web.markdown_content.lower()
        score = 50.0  # neutral baseline

        # Modern signals
        modern_tech = [
            "react", "next.js", "nextjs", "vercel", "cloudflare",
            "tailwind", "stripe", "supabase", "prisma", "graphql",
            "typescript", "webpack", "vite", "svelte",
        ]
        modern_hits = sum(1 for t in modern_tech if t in content)
        score += min(modern_hits * 8, 30)

        # Negative signals (outdated)
        outdated_signals = ["jquery", "bootstrap 3", "flash", "internet explorer", "ie8"]
        outdated_hits = sum(1 for s in outdated_signals if s in content)
        score -= outdated_hits * 15

        # HTTPS (basic modern signal)
        if web.url.startswith("https://"):
            score += 10

        return FeatureValue(
            "tech_modernity",
            max(0, min(score, 100.0)),
            raw_value=f"modern={modern_hits}, outdated={outdated_hits}",
            confidence=0.4,
            source="web_scrape",
        )

    def _evolution_signs(self, exa: ExaData = None) -> FeatureValue:
        """Is the brand evolving? Rebranding, new markets, pivots?"""
        if not exa:
            return FeatureValue("evolution_signs", 30.0, confidence=0.3, source="none")

        evolution_keywords = [
            "rebrand", "new look", "redesign", "pivot", "expanding to",
            "new market", "new category", "evolved", "refresh", "v2",
            "next generation", "reimagined", "transformation",
        ]

        mentions_text = " ".join(
            (r.text or "") + " " + (r.summary or "")
            for r in exa.mentions
        ).lower()

        hits = sum(1 for kw in evolution_keywords if kw in mentions_text)

        if hits >= 3:
            score = 80.0
        elif hits >= 1:
            score = 55.0
        else:
            score = 35.0

        return FeatureValue(
            "evolution_signs",
            score,
            raw_value=f"{hits} evolution keywords",
            confidence=0.5,
            source="exa",
        )
