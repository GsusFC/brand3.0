"""
Brand Authenticity Analyzer.

Detects whether a brand feels REAL vs AI-generated/template.
This is the key differentiator for FLOC* — anyone can score presence,
but judging authenticity requires taste.

Combines:
1. Visual analysis (screenshot → design quality, template detection)
2. Content pattern analysis (copy → AI-written vs human)
3. Structural analysis (layout repetition, CTA density)
"""

import re
from collections import Counter
from dataclasses import dataclass, field

from ..models.brand import FeatureValue
from ..collectors.web_collector import WebData
from ..collectors.exa_collector import ExaData
from .visual_analyzer import VisualAnalyzer


# ── AI writing pattern detection ──

AI_PHRASES = [
    # Classic LLM marketing phrases
    "in weeks, not quarters",
    "game changer",
    "at scale",
    "seamlessly",
    "leverage",
    "empower",
    "unlock",
    "transform",
    "revolutionize",
    "cutting-edge",
    "state-of-the-art",
    "best-in-class",
    "world-class",
    "industry-leading",
    "next-generation",
    "paradigm shift",
    "holistic approach",
    "synergy",
    "robust",
    "streamline",
    "foster",
    "delve",
    "tapestry",
    "landscape",
    "navigate",
    "harness",
    "elevate",
    "reimagine",
    "pioneer",
    "spearhead",
    "catalyst",
    "labyrinth",
    "multifaceted",
    "myriad",
    "plethora",
]

# Patterns that suggest AI-generated structure
AI_STRUCTURAL_PATTERNS = [
    r"(?i)your\s+pain\s+point",
    r"(?i)how\s+we\s+(?:solve|help)",
    r"(?i)what\s+you\s+get",
    r"(?i)common\s+use\s+cases",
    r"(?i)the\s+(?:real|key)\s+(?:problem|solution|difference)",
    r"(?i)here'?s\s+(?:how|why|what)",
    r"(?i)let'?s\s+(?:dive|break)\s+(?:in|down)",
    r"(?i)without\s+(?:the|all\s+the)\s+\w+",
    r"(?i)from\s+\w+\s+to\s+\w+\s+in\s+\w+",
]


@dataclass
class AuthenticityResult:
    """Result of brand authenticity analysis."""
    design_authenticity: float = 0.0    # 0-100: custom vs template
    content_authenticity: float = 0.0   # 0-100: human vs AI-written
    brand_personality: float = 0.0      # 0-100: has personality vs generic
    cta_density_score: float = 0.0      # 0-100: natural vs salesy
    overall_authenticity: float = 0.0
    confidence: float = 0.0
    insights: list = field(default_factory=list)
    details: dict = field(default_factory=dict)


class AuthenticityAnalyzer:
    """Analyzes brand authenticity — real vs AI-generated/template."""

    def __init__(self, visual_analyzer: VisualAnalyzer = None):
        self.visual = visual_analyzer or VisualAnalyzer()

    def analyze(self, web: WebData = None, exa: ExaData = None,
                screenshot_url: str = None) -> AuthenticityResult:
        """Run full authenticity analysis."""
        result = AuthenticityResult()

        if not web or web.error:
            result.overall_authenticity = 30.0
            result.confidence = 0.2
            return result

        content = web.markdown_content

        # ── 1. Content pattern analysis ──
        result.content_authenticity = self._analyze_content_patterns(content)
        result.brand_personality = self._analyze_brand_personality(content, exa)
        result.cta_density_score = self._analyze_cta_density(content)

        # ── 2. Visual analysis (if screenshot available) ──
        if screenshot_url:
            visual_result = self.visual.analyze_screenshot(
                screenshot_url, exa.brand_name if exa else ""
            )
            if visual_result.details:
                result.design_authenticity = visual_result.details.get(
                    "design_authenticity", 50.0
                )
                result.details["visual"] = visual_result.details
                result.insights.extend(
                    visual_result.details.get("authenticity_insights", [])
                )
            else:
                result.design_authenticity = 50.0
        else:
            # Heuristic estimate without screenshot
            result.design_authenticity = self._estimate_design_authenticity(content)

        # ── 3. Generate insights ──
        self._generate_insights(result, content)

        # ── 4. Overall score ──
        weights = {
            "content": 0.35,
            "personality": 0.25,
            "design": 0.25,
            "cta": 0.15,
        }
        result.overall_authenticity = (
            result.content_authenticity * weights["content"]
            + result.brand_personality * weights["personality"]
            + result.design_authenticity * weights["design"]
            + result.cta_density_score * weights["cta"]
        )

        result.confidence = 0.7 if screenshot_url else 0.5
        return result

    def _analyze_content_patterns(self, content: str) -> float:
        """Detect AI-written content patterns. Returns score (100=human, 0=AI)."""
        text = content.lower()

        # Count AI phrase matches
        ai_hits = sum(1 for p in AI_PHRASES if p in text)

        # Count structural pattern matches
        structural_hits = sum(
            1 for p in AI_STRUCTURAL_PATTERNS if re.search(p, text)
        )

        # Check sentence length uniformity (AI tends to be uniform)
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        if len(sentences) > 5:
            lengths = [len(s.split()) for s in sentences[:30]]
            avg_len = sum(lengths) / len(lengths)
            variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
            # Low variance = uniform = likely AI
            uniformity_penalty = max(0, (50 - variance) / 50) * 20
        else:
            uniformity_penalty = 0

        # Calculate score
        total_penalty = (ai_hits * 5) + (structural_hits * 8) + uniformity_penalty
        score = max(0, 100 - total_penalty)

        return score

    def _analyze_brand_personality(self, content: str, exa: ExaData = None) -> float:
        """Does the brand have a unique personality/voice?"""
        text = content.lower()
        score = 50.0  # neutral baseline

        # Positive personality signals
        personality_signals = {
            "humor": ["joke", "funny", "lol", "haha", "😅", "🤔", "👀", "🔥",
                       "weird", "quirky", "honestly", "real talk", "no bs"],
            "opinionated": ["we believe", "we think", "our take", "honestly",
                           "let's be real", "the truth is", "unpopular opinion",
                           "we don't", "we won't", "we refuse"],
            "specific_voice": ["our way", "we call it", "our thing", "weird",
                              "our philosophy", "our bet", "our bet is"],
            "casual": ["hey", "yo", "sup", "gonna", "wanna", "tbh", "ngl",
                      "btw", "idk", "fwiw"],
            "references": ["like", "think of it as", "imagine", "remember when",
                          "you know that feeling"],
        }

        for category, signals in personality_signals.items():
            hits = sum(1 for s in signals if s in text)
            if hits >= 2:
                score += 8
            elif hits >= 1:
                score += 4

        # Negative: too corporate/formal
        corporate_signals = [
            "we are committed to", "our mission is to", "we strive to",
            "exceed expectations", "best-in-class", "world-class",
            "we pride ourselves", "customer-centric", "data-driven",
            "innovative solutions", "proven track record",
        ]
        corporate_hits = sum(1 for s in corporate_signals if s in text)
        score -= corporate_hits * 6

        return max(0, min(100, score))

    def _analyze_cta_density(self, content: str) -> float:
        """Check CTA density — too many = salesy/agency, too few = no conversion."""
        text = content.lower()

        cta_patterns = [
            "book a call", "get started", "sign up", "try free",
            "request demo", "contact us", "let's talk", "schedule",
            "get in touch", "start now", "learn more", "see pricing",
            "talk to", "speak to", "book now", "request a",
        ]

        cta_count = sum(1 for p in cta_patterns if p in text)

        # Count distinct sections (rough estimate by headings)
        sections = len(re.findall(r'^#{1,3}\s', content, re.MULTILINE))
        if sections == 0:
            sections = max(1, len(content) // 1000)

        cta_per_section = cta_count / sections

        # Ideal: 0.2-0.5 CTAs per section (natural conversion)
        # Too high: >1 per section (agency/aggressive)
        # Too low: 0 (no conversion)
        if cta_per_section > 1.0:
            score = max(20, 80 - (cta_per_section - 1) * 40)
        elif cta_per_section < 0.1:
            score = 50  # neutral
        else:
            score = 80 + (0.3 - abs(cta_per_section - 0.35)) * 50

        return max(0, min(100, score))

    def _estimate_design_authenticity(self, content: str) -> float:
        """Rough estimate of design quality from content signals."""
        text = content.lower()
        score = 50.0

        # Has custom elements
        if "animation" in text or "scroll" in text or "interactive" in text:
            score += 10

        # Excessive template signals
        template_signals = [
            "built with", "powered by", "template", "theme",
            "made with wix", "made with squarespace", "wordpress",
        ]
        template_hits = sum(1 for s in template_signals if s in text)
        score -= template_hits * 10

        # Has a lot of content (real brands invest in content)
        if len(content) > 20000:
            score += 15
        elif len(content) > 10000:
            score += 8

        return max(0, min(100, score))

    def _generate_insights(self, result: AuthenticityResult, content: str):
        """Generate human-readable insights about authenticity."""
        text = content.lower()

        if result.content_authenticity < 40:
            result.insights.append("Content shows strong AI writing patterns")

        if result.brand_personality < 40:
            result.insights.append("Brand voice is generic/corporate — no distinct personality")

        if result.cta_density_score < 40:
            result.insights.append("CTA density too high — feels like an agency, not a brand")

        # Check for specific red flags
        ai_phrase_count = sum(1 for p in AI_PHRASES if p in text)
        if ai_phrase_count > 8:
            result.insights.append(f"{ai_phrase_count} AI-typical phrases detected in copy")

        # Positive signals
        if result.brand_personality > 70:
            result.insights.append("Strong brand personality — feels human and authentic")

        if result.content_authenticity > 75:
            result.insights.append("Content feels original and human-written")
