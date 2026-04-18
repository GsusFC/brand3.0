"""
Dimension and feature definitions for Brand3 Scoring.

Each dimension has:
- weight: importance in composite score (sums to 1.0)
- features: what we measure, each with its own weight within the dimension
- rules: heuristic overrides that can cap or boost scores
"""

DIMENSIONS = {

    "coherencia": {
        "description": "¿El messaging, visual y tono son consistentes across touchpoints?",
        "weight": 0.20,
        "features": {
            "visual_consistency": {
                "description": "¿Colores, tipografía e imágenes son consistentes entre web y socials?",
                "weight": 0.30,
                "sources": ["web_scrape", "social_media"],
            },
            "messaging_consistency": {
                "description": "¿El tagline, bio y descripciones dicen lo mismo en todos los canales?",
                "weight": 0.35,
                "sources": ["web_scrape", "social_media", "exa"],
            },
            "tone_consistency": {
                "description": "¿El tono de comunicación es el mismo en web, redes y contenido?",
                "weight": 0.20,
                "sources": ["web_scrape", "social_media"],
            },
            "cross_channel_coherence": {
                "description": "¿Los canales se enlazan y referencian entre sí correctamente?",
                "weight": 0.15,
                "sources": ["web_scrape", "social_media"],
            },
        },
        "rules": [
            "si no tiene web propia → cap a 40",
            "si solo tiene 1 canal activo → cap a 50",
        ],
    },

    "presencia": {
        "description": "¿Dónde aparece y con qué volumen? (web, social, AI visibility)",
        "weight": 0.20,
        "features": {
            "web_presence": {
                "description": "¿Tiene web propia? ¿Es profesional? ¿Carga bien?",
                "weight": 0.25,
                "sources": ["web_scrape"],
            },
            "social_footprint": {
                "description": "En qué plataformas está, seguidores, alcance",
                "weight": 0.30,
                "sources": ["social_media"],
            },
            "search_visibility": {
                "description": "¿Aparece en resultados de búsqueda por su nombre/nicho?",
                "weight": 0.20,
                "sources": ["exa"],
            },
            "ai_visibility": {
                "description": "¿Los LLMs conocen la marca? ¿Aparece en respuestas de IA?",
                "weight": 0.15,
                "sources": ["exa", "llm_probe"],
            },
            "directory_listings": {
                "description": "¿Está en directorios relevantes? (Google Business, Crunchbase, etc.)",
                "weight": 0.10,
                "sources": ["exa"],
            },
        },
        "rules": [
            "si no tiene web ni socials → score directo 5 (marca fantasma)",
        ],
    },

    "percepcion": {
        "description": "¿Qué sentiment genera? ¿Cómo hablan de ella?",
        "weight": 0.25,
        "features": {
            "sentiment_score": {
                "description": "Sentiment promedio en menciones y contenido sobre la marca",
                "weight": 0.35,
                "sources": ["exa", "social_media"],
            },
            "mention_volume": {
                "description": "Cuánto se habla de la marca (absoluto y relativo al nicho)",
                "weight": 0.20,
                "sources": ["exa"],
            },
            "sentiment_trend": {
                "description": "¿Mejora o empeora el sentiment con el tiempo?",
                "weight": 0.20,
                "sources": ["exa"],
            },
            "review_quality": {
                "description": "Calidad y cantidad de reviews donde aparezca",
                "weight": 0.15,
                "sources": ["exa", "web_scrape"],
            },
            "controversy_flag": {
                "description": "¿Hay controversia, crisis o mentions negativas significativas?",
                "weight": 0.10,
                "sources": ["exa"],
            },
        },
        "rules": [
            "si controversy_flag está activo → percepción cap a 35",
            "si no hay mentions suficientes → score = 50 (neutral, no hay datos)",
        ],
    },

    "diferenciacion": {
        "description": "¿Dice algo distinto a sus competidores o es genérica?",
        "weight": 0.20,
        "features": {
            "unique_value_prop": {
                "description": "¿Articula claramente qué la hace diferente?",
                "weight": 0.22,
                "sources": ["web_scrape", "exa"],
            },
            "generic_language_score": {
                "description": "Cuánto usa frases genéricas vs lenguaje propio (inverso)",
                "weight": 0.18,
                "sources": ["web_scrape", "llm_analysis"],
            },
            "competitor_distance": {
                "description": "¿Se posiciona distinto a la competencia principal?",
                "weight": 0.22,
                "sources": ["exa", "llm_analysis"],
            },
            "brand_vocabulary": {
                "description": "¿Tiene términos, frases o conceptos propios reconocibles?",
                "weight": 0.15,
                "sources": ["web_scrape", "exa"],
            },
            "content_authenticity": {
                "description": "¿El contenido se siente original y humano, no plantilla/AI sludge?",
                "weight": 0.13,
                "sources": ["content_analysis", "vision"],
            },
            "brand_personality": {
                "description": "¿La marca tiene voz y carácter propios?",
                "weight": 0.10,
                "sources": ["content_analysis", "exa"],
            },
        },
        "rules": [
            "si el lenguaje es >80% genérico → diferenciación cap a 25",
        ],
    },

    "vitalidad": {
        "description": "¿Está activa, publicando, evolucionando, o es una marca muerta?",
        "weight": 0.15,
        "features": {
            "content_recency": {
                "description": "¿Cuándo fue la última publicación detectable en fuentes terceras?",
                "weight": 0.40,
                "sources": ["exa"],
            },
            "publication_cadence": {
                "description": "Consistencia de la cadencia de publicación en los últimos 12 meses",
                "weight": 0.35,
                "sources": ["exa"],
            },
            "momentum": {
                "description": "¿Está construyendo o en mantenimiento? Juicio LLM con citas literales de menciones recientes",
                "weight": 0.25,
                "sources": ["exa", "llm_analysis"],
            },
        },
        "rules": [
            "si última publicación > 6 meses → vitalidad cap a 20",
            "si última publicación > 12 meses → vitalidad cap a 10",
        ],
    },
}

# Validate weights
assert abs(sum(d["weight"] for d in DIMENSIONS.values()) - 1.0) < 0.001, \
    "Dimension weights must sum to 1.0"

for name, dim in DIMENSIONS.items():
    feature_weights = sum(f["weight"] for f in dim["features"].values())
    assert abs(feature_weights - 1.0) < 0.001, \
        f"Feature weights in '{name}' must sum to 1.0, got {feature_weights}"
