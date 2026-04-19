"""Heuristic niche classifier for brand calibration profiles."""

from __future__ import annotations

from collections import Counter
import re
from typing import Any

from .profiles import CALIBRATION_PROFILES


PROFILE_SIGNALS: dict[str, dict[str, object]] = {
    "frontier_ai": {
        "keywords": {
            "frontier": 2.5,
            "reasoning": 2.0,
            "foundation model": 3.0,
            "pre-trained": 2.5,
            "research": 1.5,
            "benchmark": 1.5,
            "inference": 1.0,
            "open source": 1.0,
            "model": 1.0,
        },
        "patterns": [
            (r"\bresearch lab\b", 3.0, "Research-lab positioning detected"),
            (r"\bsafe super intelligence\b", 3.0, "Frontier AI ambition detected"),
            (r"\bfrontier ai lab\b", 3.0, "Frontier-lab language detected"),
        ],
    },
    "enterprise_ai": {
        "keywords": {
            "enterprise": 2.5,
            "compliance": 1.5,
            "governance": 3.0,
            "audit": 2.0,
            "audit trails": 3.0,
            "policy engine": 2.5,
            "runtime assurance": 2.5,
            "security": 1.0,
            "defense": 1.5,
        },
        "patterns": [
            (r"\bbook a demo\b", 2.0, "Demo CTA suggests enterprise motion"),
            (r"\brequest demo\b", 2.0, "Demo CTA suggests enterprise motion"),
            (r"\bfortune 500\b", 2.0, "Enterprise customer language detected"),
        ],
    },
    "physical_ai": {
        "keywords": {
            "robotics": 3.0,
            "robot": 2.5,
            "embodied": 3.0,
            "autonomy": 2.5,
            "autonomous": 2.0,
            "physical ai": 3.0,
            "real-world": 1.5,
            "teleoperation": 2.0,
            "simulation": 1.5,
            "sensor": 1.5,
            "fleet": 1.0,
            "warehouse": 1.0,
            "dataset": 1.5,
        },
        "patterns": [
            (r"\bphysical ai\b", 3.0, "Physical-AI language detected"),
            (r"\bembodied ai\b", 3.0, "Embodied-AI language detected"),
            (r"\brobotics\b", 2.5, "Robotics language detected"),
        ],
    },
}

SUBTYPE_SIGNALS: dict[str, dict[str, object]] = {
    "model_lab": {
        "profile": "frontier_ai",
        "keywords": {
            "tabular foundation": 3.0,
            "tabular": 2.0,
            "foundation model": 3.0,
            "pre-trained": 2.5,
            "probabilistic": 1.5,
        },
        "patterns": [
            (r"\btabular foundation models?\b", 3.0, "Tabular foundation-model language detected"),
        ],
    },
    "ai_research_lab": {
        "profile": "frontier_ai",
        "keywords": {
            "research lab": 3.0,
            "reasoning": 2.0,
            "safe super intelligence": 3.0,
            "frontier ai lab": 3.0,
            "research": 1.5,
        },
        "patterns": [
            (r"\bsafe super intelligence\b", 3.0, "Safe-superintelligence language detected"),
            (r"\bbetter reasoning\b", 2.0, "Reasoning-first positioning detected"),
        ],
    },
    "chip_ai": {
        "profile": "frontier_ai",
        "keywords": {
            "chip": 2.5,
            "chips": 2.5,
            "semiconductor": 3.0,
            "silicon": 2.0,
            "hardware": 1.5,
        },
        "patterns": [
            (r"\bchip design\b", 3.0, "Chip-design focus detected"),
            (r"\bsemiconductor\b", 3.0, "Semiconductor focus detected"),
        ],
    },
    "ai_governance": {
        "profile": "enterprise_ai",
        "keywords": {
            "governance": 3.0,
            "audit trails": 3.0,
            "audit trail": 3.0,
            "policy engine": 2.5,
            "runtime assurance": 2.5,
            "compliance": 2.0,
            "deterministic": 1.5,
        },
        "patterns": [
            (r"\bruntime audit trails\b", 3.0, "Runtime audit-trail positioning detected"),
            (r"\bdeterministic layer\b", 2.0, "Deterministic-control language detected"),
        ],
    },
    "startup_studio": {
        "profile": "base",
        "keywords": {
            "foundry": 1.5,
            "venture studio": 3.0,
            "startup studio": 3.0,
            "building ai products": 2.0,
            "incubate": 1.5,
        },
        "patterns": [
            (r"\bstartup foundry\b", 3.0, "Startup-foundry language detected"),
            (r"\bventure studio\b", 3.0, "Venture-studio language detected"),
        ],
    },
    "community_platform": {
        "profile": "base",
        "keywords": {
            "petition": 2.5,
            "petitions": 2.5,
            "subscriptions": 2.0,
            "supporters": 2.0,
            "membership": 1.5,
            "fundraising": 1.5,
            "donor": 1.5,
            "cause platform": 2.5,
        },
        "patterns": [
            (r"\bconvert your cause into an unstoppable movement\b", 4.0, "Cause-to-movement positioning detected"),
            (r"\bcomplete control over your audience\b", 3.0, "Audience-control language detected"),
            (r"\bno algorithms limiting your reach\b", 3.0, "Anti-algorithm distribution language detected"),
            (r"\bdrive change\b", 2.0, "Change-oriented positioning detected"),
            (r"\borganize, scale and sustain your cause\b", 3.0, "Cause-platform operating model detected"),
        ],
    },
    "llm_framework": {
        "profile": "base",
        "keywords": {
            "open source": 1.0,
            "framework": 3.0,
            "llm applications": 2.5,
            "agent framework": 2.5,
            "orchestration": 2.0,
            "developers": 0.5,
            "sdk": 1.0,
            "library": 0.5,
        },
        "patterns": [
            (r"\bleading open-source framework\b", 3.0, "Open-source framework positioning detected"),
            (r"\bbuild (llm|ai) applications\b", 2.5, "Build-applications framework language detected"),
            (r"\bframework for (llm|ai)\b", 2.5, "Framework-for-LLM language detected"),
        ],
    },
    "agent_tooling": {
        "profile": "base",
        "keywords": {
            "browser": 2.5,
            "web interaction": 2.5,
            "web automation": 2.5,
            "agent tools": 2.5,
            "validation": 0.8,
            "engineering": 0.5,
            "developers": 0.5,
        },
        "patterns": [
            (r"\bai agent(s)? for browsing\b", 3.0, "Agent-browsing language detected"),
            (r"\bweb agent(s)?\b", 2.5, "Web-agent language detected"),
            (r"\bhigh-accuracy ai agent\b", 2.5, "High-accuracy agent tooling language detected"),
            (r"\bengineering validation\b", 2.5, "Engineering-validation language detected"),
        ],
    },
    "workforce_marketplace": {
        "profile": "base",
        "keywords": {
            "marketplace": 3.0,
            "labor": 2.5,
            "workforce": 2.5,
            "staffing": 2.5,
            "supply chain": 2.0,
            "industrial": 1.5,
            "operations": 1.5,
            "shifts": 2.0,
            "hourly": 1.5,
        },
        "patterns": [
            (r"\bindustrial .* marketplace\b", 3.0, "Industrial-marketplace language detected"),
            (r"\bworkforce marketplace\b", 3.0, "Workforce-marketplace language detected"),
            (r"\bsupply chain marketplace\b", 2.5, "Supply-chain marketplace language detected"),
        ],
    },
    "productivity_addon": {
        "profile": "base",
        "keywords": {
            "excel": 3.0,
            "spreadsheet": 3.0,
            "add-on": 2.5,
            "addin": 2.0,
            "plugin": 2.0,
            "document processing": 2.5,
            "structured data": 2.0,
            "analysis": 0.5,
        },
        "patterns": [
            (r"\bexcel add-?on\b", 3.0, "Excel add-on language detected"),
            (r"\bstructured data analysis\b", 2.5, "Structured-data analysis language detected"),
            (r"\bdocument processing\b", 2.5, "Document-processing language detected"),
        ],
    },
    "engineering_validation": {
        "profile": "base",
        "keywords": {
            "devin": 3.0,
            "software engineering": 2.5,
            "engineering validation": 3.0,
            "code validation": 2.5,
            "codebase": 1.5,
            "specialized ai engineering": 2.5,
            "agent evaluation": 2.0,
        },
        "patterns": [
            (r"\bspecialized ai engineering validation\b", 3.0, "Engineering-validation specialization detected"),
            (r"\bautonomous software engineering\b", 2.5, "Autonomous software-engineering language detected"),
            (r"\bdevin\b", 3.0, "Devin product language detected"),
        ],
    },
    "physical_ai_data": {
        "profile": "physical_ai",
        "keywords": {
            "robotics data": 3.0,
            "embodied ai": 3.0,
            "physical ai": 3.0,
            "dataset": 2.0,
            "marketplace": 1.0,
            "teleoperation": 2.0,
            "simulation": 1.5,
        },
        "patterns": [
            (r"\bdata engine\b", 2.0, "Data-engine positioning detected"),
            (r"\brobotics datasets?\b", 3.0, "Robotics-dataset language detected"),
        ],
    },
}


def _normalise_text(*parts: str | None) -> str:
    combined = " ".join(part for part in parts if part)
    return re.sub(r"\s+", " ", combined).lower()


def _early_signal_text(text: str | None, limit: int = 500) -> str:
    """Keep classification anchored to title/hero copy instead of long-body noise."""
    if not text:
        return ""
    return text[:limit]


def _score_keywords(text: str, keyword_weights: dict[str, float]) -> tuple[float, list[str]]:
    score = 0.0
    evidence: list[str] = []
    for keyword, weight in keyword_weights.items():
        if keyword in text:
            score += weight
            evidence.append(f"Matched keyword '{keyword}'")
    return score, evidence


def _score_signal_set(text: str, config: dict[str, object]) -> tuple[float, list[str]]:
    score, evidence = _score_keywords(text, config["keywords"])
    for pattern, weight, reason in config["patterns"]:
        if re.search(pattern, text):
            score += weight
            evidence.append(reason)
    return score, evidence


def _score_signal_sources(
    sources: list[tuple[str, str, float]],
    config: dict[str, object],
) -> tuple[float, list[str]]:
    score = 0.0
    evidence: list[str] = []
    for source_name, text, weight in sources:
        if not text:
            continue
        source_score, source_evidence = _score_signal_set(text, config)
        if source_score <= 0:
            continue
        score += source_score * weight
        evidence.extend(f"{message} [{source_name}]" for message in source_evidence)
    return score, evidence


def _has_primary_source_evidence(evidence: list[str]) -> bool:
    return any("[web]" in item or "[identity]" in item for item in evidence)


def _has_required_subtype_evidence(subtype_id: str, evidence: list[str]) -> bool:
    if subtype_id != "workforce_marketplace":
        return True

    required_terms = {"marketplace", "workforce", "staffing", "shifts", "hourly"}
    matched_terms = {
        term
        for term in required_terms
        if any(f"'{term}'" in item and ("[web]" in item or "[identity]" in item) for item in evidence)
    }
    return len(matched_terms) >= 2


def classify_brand_niche(
    brand_name: str | None,
    url: str | None,
    *,
    web_title: str | None = None,
    web_content: str | None = None,
    exa_texts: list[str] | None = None,
    competitor_names: list[str] | None = None,
) -> dict[str, Any]:
    identity_text = _normalise_text(brand_name, url)
    web_text = _normalise_text(web_title, _early_signal_text(web_content))
    exa_text = _normalise_text(" ".join(exa_texts or []))
    competitor_text = _normalise_text(" ".join(competitor_names or []))
    corpus = _normalise_text(identity_text, web_text, exa_text, competitor_text)
    weighted_sources = [
        ("identity", identity_text, 0.3),
        ("web", web_text, 1.0),
        ("exa", exa_text, 0.35),
        ("competitors", competitor_text, 0.2),
    ]

    if not corpus.strip():
        return {
            "predicted_niche": "base",
            "confidence": 0.2,
            "alternatives": [],
            "evidence": ["No classification content available"],
        }

    profile_scores: dict[str, float] = {profile_id: 0.0 for profile_id in CALIBRATION_PROFILES}
    evidence_map: dict[str, list[str]] = {profile_id: [] for profile_id in CALIBRATION_PROFILES}
    subtype_scores: dict[str, float] = {}
    subtype_evidence: dict[str, list[str]] = {}

    for subtype_id, config in SUBTYPE_SIGNALS.items():
        score, evidence = _score_signal_sources(weighted_sources, config)
        subtype_scores[subtype_id] = score
        subtype_evidence[subtype_id] = evidence
        profile_id = str(config["profile"])
        profile_scores[profile_id] = profile_scores.get(profile_id, 0.0) + score
        evidence_map.setdefault(profile_id, []).extend(evidence)

    for profile_id, config in PROFILE_SIGNALS.items():
        score, evidence = _score_signal_sources(weighted_sources, config)
        profile_scores[profile_id] = profile_scores.get(profile_id, 0.0) + score
        evidence_map.setdefault(profile_id, []).extend(evidence)

    sorted_scores = sorted(profile_scores.items(), key=lambda item: item[1], reverse=True)
    top_niche, top_score = sorted_scores[0]
    second_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0.0

    if top_score <= 0:
        return {
            "predicted_niche": "base",
            "confidence": 0.2,
            "alternatives": [],
            "evidence": ["No strong niche signals detected"],
        }

    score_total = sum(max(value, 0.0) for _, value in sorted_scores) or top_score
    dominance = top_score / score_total
    margin = max(top_score - second_score, 0.0)
    confidence = min(0.95, round(0.35 + (dominance * 0.35) + min(margin * 0.06, 0.25), 2))
    if top_niche != "base" and confidence < 0.6:
        top_niche = "base"

    alternatives = [
        {
            "niche": niche_id,
            "score": round(score, 2),
            "label": CALIBRATION_PROFILES[niche_id]["label"],
        }
        for niche_id, score in sorted_scores[1:4]
        if score > 0
    ]

    raw_evidence = evidence_map[top_niche]
    evidence_counts = Counter(raw_evidence)
    evidence = [message for message, _ in evidence_counts.most_common(5)]
    subtype_candidates = sorted(
        (
            (subtype_id, score)
            for subtype_id, score in subtype_scores.items()
            if score > 0 and SUBTYPE_SIGNALS[subtype_id]["profile"] == top_niche
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    predicted_subtype = subtype_candidates[0][0] if subtype_candidates else None
    if predicted_subtype:
        subtype_config = SUBTYPE_SIGNALS[predicted_subtype]
        subtype_signal_evidence = subtype_evidence[predicted_subtype]
        if (
            subtype_config["profile"] == "base"
            and not _has_primary_source_evidence(subtype_signal_evidence)
        ):
            predicted_subtype = None
        elif (
            subtype_config["profile"] == "base"
            and subtype_scores[predicted_subtype] < 2.5
        ):
            predicted_subtype = None
        elif (
            subtype_config["profile"] == "base"
            and not _has_required_subtype_evidence(predicted_subtype, subtype_signal_evidence)
        ):
            predicted_subtype = None
    if predicted_subtype and not evidence:
        subtype_counts = Counter(subtype_evidence[predicted_subtype])
        evidence = [message for message, _ in subtype_counts.most_common(5)]

    return {
        "predicted_niche": top_niche,
        "predicted_subtype": predicted_subtype,
        "confidence": confidence,
        "alternatives": alternatives,
        "evidence": evidence,
    }


def select_calibration_profile(
    niche_prediction: dict[str, Any],
    *,
    min_confidence: float = 0.65,
) -> tuple[str, str]:
    predicted_niche = niche_prediction.get("predicted_niche") or "base"
    predicted_subtype = niche_prediction.get("predicted_subtype")
    confidence = float(niche_prediction.get("confidence") or 0.0)
    if predicted_niche == "base" and predicted_subtype:
        return "base", "auto"
    if (
        predicted_niche in CALIBRATION_PROFILES
        and predicted_niche != "base"
        and confidence >= min_confidence
    ):
        return predicted_niche, "auto"
    return "base", "fallback"
