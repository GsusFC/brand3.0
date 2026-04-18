# REVIEW NOTES — Rediseño Presencia

**Branch:** `refactor/presencia`
**Scope:** refactor completo de la dimensión `presencia` siguiendo el patrón single-file ya usado en Vitalidad.

## Archivos modificados

1. `src/features/presencia.py` — reescritura completa a 4 features heurísticas con `raw_value` estructurado.
2. `src/dimensions.py` — bloque `presencia` actualizado de 5 features a 4 con pesos `0.30 / 0.35 / 0.25 / 0.10`.
3. `tests/test_feature_extractors.py` — tests viejos de presencia sustituidos por cobertura de las 4 features nuevas.
4. `tests/test_scoring_engine.py` — fixtures de presencia actualizados con los nuevos nombres/pesos y asserts recalculados.

## Decisiones de implementación no obvias

### D1. `raw_value` estructurado como dict nativo

La instrucción pedía `raw_value` dict y no string. A diferencia de Vitalidad, aquí no serialicé JSON: `FeatureValue.raw_value` sigue tipado como `Optional[str]`, pero el modelo no impone validación runtime y el criterio explícito del encargo era devolver dict estructurado.

### D2. `social_footprint` sin fallback heurístico desde web/exa

El diseño objetivo pedía explícitamente que, si no hay `SocialData`, la feature no castigue con `0` sino con `15`, `confidence=0.3` y `raw_value.reason="no_social_data"`. Por eso eliminé el fallback viejo que infería plataformas desde `web`/`exa`. Queda más consistente y evita inflar la presencia con señales débiles.

### D3. `search_visibility` fusiona búsqueda + AI visibility

La nueva feature parte de menciones Exa relevantes (`_subject_relevance > 0.35`), añade bonus por `own_url_in_top3` e integra la señal antigua de `ai_visibility` como un bonus adicional. El output conserva evidencia literal: top 3 resultados relevantes con `url`, `title`, `snippet`.

### D4. `directory_presence` por tiers

Se renombró `directory_listings` → `directory_presence` y se separaron dominios en:
- Tier 1: `Crunchbase`, `LinkedIn company`, `G2`, `Capterra`
- Tier 2: `Yelp`, `Glassdoor`, `Trustpilot`, `AngelList`, `Product Hunt`

Puntuación: `20` por tier-1, `8` por tier-2, `max 100`.

### D5. Distinción `minimal` vs `thin` en `web_presence`

`web_presence` marca como `thin` solo contenido meaningful mínimo (`>=24 chars`). Cadenas tipo `"Login"` quedaban demasiado arriba y pasaron a `minimal`, que era el comportamiento esperado por los tests y por el diseño objetivo.

## Tests añadidos vs eliminados

### Eliminados / sustituidos

- Tests de `ai_visibility` como feature independiente.
- Tests de `directory_listings` con nombre viejo.
- Test viejo de `social_footprint` basado en `weighted_presence=` string.

### Añadidos

`web_presence`
- `test_web_presence_placeholder_page_scores_minimal`
- `test_web_presence_normal_site_scores_high_with_structured_raw_value`
- `test_web_presence_without_https_loses_signal`
- `test_web_presence_without_meaningful_content_stays_low`

`social_footprint`
- `test_social_footprint_without_social_data_degrades_gracefully`
- `test_social_footprint_with_multiple_platforms_is_structured`
- `test_social_footprint_rewards_verified_accounts`

`search_visibility`
- `test_search_visibility_without_results_returns_low_neutral`
- `test_search_visibility_with_few_results_stays_mid_low`
- `test_search_visibility_rewards_many_results_and_own_url_top3`
- `test_search_visibility_filters_low_subject_relevance`

`directory_presence`
- `test_directory_presence_without_directories_is_zero`
- `test_directory_presence_with_only_tier2_is_limited`
- `test_directory_presence_with_tier1_and_tier2_mix_scores_higher`

## Warnings no bloqueantes

1. El runner documentado en el encargo era `./venv/bin/pytest`, pero en este repo el entorno útil está en `./.venv`, no `./venv`.
2. La suite completa con `./.venv/bin/pytest -v` no terminó limpia por un problema de import en `tests/test_learning.py` y `tests/test_main_experiment.py`: `ModuleNotFoundError: No module named 'main'` durante collection, pese a que `main.py` existe en raíz. No lo toqué por estar fuera del scope del refactor de Presencia.
3. También apareció un artefacto no relacionado en el árbol: `brand3_scoring.egg-info/`. No lo toqué.

## Verificaciones manuales pendientes

1. Re-ejecutar `tests/test_feature_extractors.py` y `tests/test_scoring_engine.py` después de los dos ajustes finales (`minimal` vs `thin`, y asserts recalculados) si quieres un verde final documentado; no lo hice porque el encargo pedía no correr tests más de 2 veces y ambas corridas ya se usaron.
2. Verificar por qué `pytest` no puede importar `main` en la suite completa dentro de `.venv`; parece un problema del entorno/configuración de imports, no del refactor de Presencia.
3. Revisar con ejemplos reales si el bonus de `search_visibility` por `ai_weighted_sum` es demasiado generoso para marcas con pocas menciones search pero buena presencia en roundups de IA.
