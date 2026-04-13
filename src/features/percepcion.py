"""
Percepción feature extractor.

Measures WHAT sentiment the brand generates — how people talk about it.
Data sources: Exa mentions, reviews, news

Sentiment analysis is heuristic-based (keyword approach).
TODO: LLM-based sentiment for higher accuracy.
"""

from datetime import datetime
from ..models.brand import FeatureValue
from ..collectors.web_collector import WebData
from ..collectors.exa_collector import ExaData


# Sentiment lexicons
POSITIVE_WORDS = {
    "excellent", "amazing", "outstanding", "great", "fantastic", "wonderful",
    "love", "best", "impressive", "innovative", "reliable", "trusted",
    "recommend", "quality", "exceptional", "superb", "brilliant",
    "perfect", "top", "leading", "popular", "successful", "growing",
    "award", "winner", "breakthrough", "powerful", "efficient",
}

NEGATIVE_WORDS = {
    "terrible", "awful", "worst", "horrible", "disappointing", "poor",
    "broken", "scam", "fraud", "complaint", "lawsuit", "controversy",
    "failed", "failure", "declining", "bankrupt", "layoff", "fired",
    "hack", "breach", "leak", "crash", "down", "outage", "bug",
    "overpriced", "expensive", "slow", "unreliable", "unresponsive",
    "toxic", "misleading", "deceptive", "ripoff", "rip off",
}

CONTROVERSY_WORDS = {
    "lawsuit", "sued", "legal action", "investigation", "fraud",
    "scandal", "controversy", "backlash", "boycott", "protest",
    "accused", "allegations", "violation", "fine", "penalty",
    "data breach", "privacy violation", "discrimination",
    "misconduct", "cover up", "whistleblower",
}


class PercepcionExtractor:
    """Extract percepción features from mentions and coverage."""

    @staticmethod
    def _parse_published_date(value: str) -> datetime | None:
        """Parse common Exa date formats into datetimes."""
        if not value or value == "None":
            return None

        candidate = value.strip()
        if candidate.endswith("Z"):
            candidate = candidate[:-1] + "+00:00"

        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            pass

        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%B %d, %Y"):
            try:
                return datetime.strptime(value[:19], fmt)
            except ValueError:
                continue
        return None

    def extract(self, web: WebData = None, exa: ExaData = None) -> dict[str, FeatureValue]:
        features = {}
        features["sentiment_score"] = self._sentiment_score(exa)
        features["mention_volume"] = self._mention_volume(exa)
        features["sentiment_trend"] = self._sentiment_trend(exa)
        features["review_quality"] = self._review_quality(exa)
        features["controversy_flag"] = self._controversy_flag(exa)
        return features

    def _sentiment_score(self, exa: ExaData = None) -> FeatureValue:
        """Overall sentiment from mentions — positive vs negative ratio."""
        if not exa or not exa.mentions:
            return FeatureValue("sentiment_score", 50.0, confidence=0.3, source="none")

        all_text = " ".join(
            ((r.text or "") + " " + (r.summary or "")).lower()
            for r in exa.mentions + exa.news
        )

        pos_count = sum(1 for w in POSITIVE_WORDS if w in all_text)
        neg_count = sum(1 for w in NEGATIVE_WORDS if w in all_text)

        total = pos_count + neg_count
        if total == 0:
            score = 50.0  # neutral
        else:
            # 0% positive = 0, 100% positive = 100
            score = (pos_count / total) * 100

        return FeatureValue(
            "sentiment_score",
            score,
            raw_value=f"positive={pos_count}, negative={neg_count}",
            confidence=0.6,
            source="exa",
        )

    def _mention_volume(self, exa: ExaData = None) -> FeatureValue:
        """How much is the brand talked about? Absolute + relative."""
        if not exa:
            return FeatureValue("mention_volume", 10.0, confidence=0.4, source="none")

        total_mentions = len(exa.mentions) + len(exa.news)

        if total_mentions >= 15:
            score = 95.0
        elif total_mentions >= 10:
            score = 80.0
        elif total_mentions >= 5:
            score = 60.0
        elif total_mentions >= 3:
            score = 40.0
        elif total_mentions >= 1:
            score = 25.0
        else:
            score = 10.0

        return FeatureValue(
            "mention_volume",
            score,
            raw_value=f"{total_mentions} total mentions",
            confidence=0.7,
            source="exa",
        )

    def _sentiment_trend(self, exa: ExaData = None) -> FeatureValue:
        """Is sentiment improving or declining over time?"""
        if not exa or not exa.mentions:
            return FeatureValue("sentiment_trend", 50.0, confidence=0.3, source="none")

        dated_results = []
        for result in exa.mentions + exa.news:
            parsed_date = self._parse_published_date(result.published_date)
            if parsed_date is not None:
                dated_results.append((parsed_date, result))

        if len(dated_results) < 4:
            return FeatureValue(
                "sentiment_trend",
                50.0,
                raw_value="insufficient dated mentions",
                confidence=0.1,
                source="exa",
            )

        dated_results.sort(key=lambda item: item[0])
        results = [result for _, result in dated_results]

        mid = len(results) // 2
        older_text = " ".join(((r.text or "") + " " + (r.summary or "")).lower() for r in results[:mid])
        newer_text = " ".join(((r.text or "") + " " + (r.summary or "")).lower() for r in results[mid:])

        def sentiment_ratio(text):
            pos = sum(1 for w in POSITIVE_WORDS if w in text)
            neg = sum(1 for w in NEGATIVE_WORDS if w in text)
            total = pos + neg
            return pos / total if total > 0 else 0.5

        older_ratio = sentiment_ratio(older_text)
        newer_ratio = sentiment_ratio(newer_text)

        # Positive trend: newer is more positive than older
        delta = newer_ratio - older_ratio
        score = 50 + (delta * 100)  # centered at 50
        score = max(0, min(100, score))

        return FeatureValue(
            "sentiment_trend",
            score,
            raw_value=f"dated_results={len(results)}, older={older_ratio:.2f}, newer={newer_ratio:.2f}, delta={delta:.2f}",
            confidence=0.6,
            source="exa",
        )

    def _review_quality(self, exa: ExaData = None) -> FeatureValue:
        """Quality and quantity of reviews — do people review this brand?"""
        if not exa:
            return FeatureValue("review_quality", 30.0, confidence=0.3, source="none")

        review_platforms = [
            "trustpilot.com", "g2.com", "capterra.com", "yelp.com",
            "glassdoor.com", "google.com/maps", "appstore", "play store",
            "producthunt.com", "reviews.io",
        ]

        review_results = [
            r for r in exa.mentions
            if any(p in r.url.lower() for p in review_platforms)
        ]

        if not review_results:
            # No review presence at all
            return FeatureValue(
                "review_quality", 25.0,
                raw_value="no review platforms found",
                confidence=0.5, source="exa",
            )

        # Analyze sentiment in review content
        review_text = " ".join(
            ((r.text or "") + " " + (r.summary or "")).lower()
            for r in review_results
        )

        pos = sum(1 for w in POSITIVE_WORDS if w in review_text)
        neg = sum(1 for w in NEGATIVE_WORDS if w in review_text)
        total = pos + neg

        if total == 0:
            score = 45.0
        else:
            score = (pos / total) * 80  # cap at 80 — reviews alone don't = quality

        # Bonus for having reviews at all
        score += min(len(review_results) * 10, 20)

        return FeatureValue(
            "review_quality",
            min(score, 100.0),
            raw_value=f"{len(review_results)} review platforms, pos={pos}, neg={neg}",
            confidence=0.6,
            source="exa",
        )

    def _controversy_flag(self, exa: ExaData = None) -> FeatureValue:
        """Is there controversy, crisis, or significant negative events?"""
        if not exa:
            return FeatureValue("controversy_flag", 0.0, confidence=0.3, source="none")

        all_text = " ".join(
            ((r.text or "") + " " + (r.summary or "")).lower()
            for r in exa.mentions + exa.news
        )

        # Require compound phrases, not single words (avoid false positives on generic fintech terms)
        controversy_phrases = [
            "filed a lawsuit", "class action", "facing lawsuit", "sued by",
            "under investigation", "federal investigation", "doj investigation",
            "fined by", "regulatory action", "sec charges",
            "data breach", "security breach", "privacy violation",
            "major scandal", "controversy surrounding", "backlash over",
            "accused of fraud", "allegations of", "charged with",
            "forced to lay off", "mass layoffs", "company collapse",
            "criminal charges", "indicted", "convicted of",
            "consumer complaints", "fda warning", "product recall",
        ]
        phrase_count = sum(1 for p in controversy_phrases if p in all_text)

        # Also check single strong words but require context
        strong_controversy = {"fraud", "scandal", "breach", "lawsuit", "indicted", "convicted"}

        # Negative context words EXCLUDING the controversy words themselves
        # (avoids "fraud" matching itself as context)
        negative_context = NEGATIVE_WORDS - strong_controversy

        # Count how many INDIVIDUAL ARTICLES contain controversy signals
        # (one article with "breach" ≠ a brand-wide controversy)
        articles_with_controversy = 0
        for r in exa.mentions + exa.news:
            article_text = ((r.text or "") + " " + (r.summary or "")).lower()
            article_hits = sum(1 for p in controversy_phrases if p in article_text)
            # Also check strong words with context — require other negative words nearby
            for word in strong_controversy:
                if word in article_text:
                    idx = article_text.find(word)
                    context = article_text[max(0, idx-50):idx+50]
                    if any(n in context for n in negative_context):
                        article_hits += 1
            if article_hits > 0:
                articles_with_controversy += 1

        word_count = 0
        for word in strong_controversy:
            if word in all_text:
                idx = all_text.find(word)
                context = all_text[max(0, idx-50):idx+50]
                if any(n in context for n in negative_context):
                    word_count += 1

        total = phrase_count + word_count

        # Scale by how many articles mention controversy (not just total hits)
        # 1 article = minor incident, 3+ articles = real controversy
        if articles_with_controversy >= 4:
            score = 90.0  # Major controversy across multiple sources
        elif articles_with_controversy >= 3:
            score = 65.0
        elif articles_with_controversy >= 2:
            score = 40.0
        elif articles_with_controversy >= 1:
            score = 15.0  # Single mention — probably an isolated incident
        else:
            score = 0.0  # No controversy

        return FeatureValue(
            "controversy_flag",
            score,
            raw_value=f"{phrase_count} phrases, {word_count} contextual words",
            confidence=0.8,
            source="exa",
        )
