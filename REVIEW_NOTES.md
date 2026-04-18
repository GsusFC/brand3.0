# REVIEW NOTES — Rediseño Vitalidad

**Branch:** `refactor/vitalidad`
**Scope:** primera dimensión del rediseño del engine. Vitalidad pasa de 5 features ruidosas a 3 features con juicio explícito + evidencia literal.

---

## Archivos modificados

1. `src/features/vitalidad.py` — reescritura completa (248 → 241 líneas). Unificado heurístico + LLM en un solo archivo.
2. `src/features/llm_analyzer.py` — añadido método público `analyze_momentum()`.
3. `src/dimensions.py` — bloque `vitalidad` reemplazado: 5 features con pesos 0.30/0.25/0.20/0.15/0.10 → 3 features con 0.40/0.35/0.25.
4. `src/services/brand_service.py:653` — `VitalidadExtractor()` → `VitalidadExtractor(llm=llm)`.
5. `tests/test_feature_extractors.py` — 2 tests de `_tech_modernity` eliminados, 12 tests nuevos añadidos para las 3 features (+1 para el contrato del `extract`).
6. `tests/test_scoring_engine.py` — 2 fixtures de vitalidad actualizados con las nuevas features, más un nuevo `assertAlmostEqual(vitalidad.score, 79.0)` explícito.

## Decisiones de diseño (no estaban 100% especificadas en la spec)

### D1. `analyze_momentum()` añadido al `LLMAnalyzer`

La spec decía "no refactorizar el LLMAnalyzer". El método `_call_json` es privado. Dos opciones:
- Llamar `_call_json` directamente desde `vitalidad.py` (rompe encapsulación).
- Añadir un método público `analyze_momentum()` siguiendo el patrón de `analyze_sentiment`, `analyze_coherence`, `analyze_positioning`, `analyze_differentiation`.

**Elegí la segunda.** Es *extensión*, no refactor. Mantiene encapsulación y es coherente con el resto del archivo. Comentario `# REVIEW:` en el método.

### D2. Patrón single-file para Vitalidad (divergente)

Otras dimensiones (`percepcion`, `coherencia`, `diferenciacion`) tienen `X.py` + `X_llm.py` (subclase). La spec pide unificar Vitalidad en un solo archivo. **Divergencia consciente del usuario** — primera dimensión del refactor, otras se migrarán en iteraciones futuras.

El `VitalidadExtractor` acepta `llm: LLMAnalyzer | None = None` en el constructor. Si `llm` es None o no tiene `api_key`, `momentum` devuelve fallback neutral.

### D3. Fallback de `momentum` con razón explícita

Sin LLM o con LLM pero sin `api_key` → `value=50`, `confidence=0.3`, `source="heuristic_fallback"`, `raw_value` JSON con `{"reason": "llm_unavailable", ...}`.

Otros casos de fallback con razones distintas:
- `"no_recent_mentions_6m"` → no había menciones datadas en los últimos 180 días.
- `"llm_error"` → excepción lanzada por el LLM (contiene `error` truncado).
- `"llm_invalid_response"` → el LLM devolvió algo que no es dict o no tiene `momentum_score`.

### D4. `raw_value` estructurado

Las 3 features devuelven `raw_value` como **JSON string** (no dict nativo). Motivo: `FeatureValue.raw_value` está tipado `Optional[str]` en `src/models/brand.py:12`, y tocar el modelo queda fuera de scope.

El revisor/frontend debe `json.loads()` para acceder a la estructura. Campos:
- `content_recency`: `{most_recent_date, days_ago, evidence_url}` o `{..., reason: "no_dates_found"}` cuando no hay fechas.
- `publication_cadence`: `{dates_found, mean_gap_days, gap_stddev_days, evidence: [{date, url}, ...]}`.
- `momentum`: con LLM `{verdict, reasoning, evidence: [{quote, source_url, signal}, ...]}`; con fallback `{reason, ...}`.

### D5. Algoritmo de `publication_cadence` con 5+ datapoints

La spec decía "base 80, ajustar según consistencia (desviación estándar de gaps)". Concreté:
- Base 80.
- Normalizo `stddev/mean_gap` a [0, 1].
- `score = 80 + (1 - ratio)*10 - ratio*20` → rango [60, 90].
- Clamp final a [40, 95].

Marcado con `# REVIEW` implícito en el comentario del código. Ajustable si el revisor quiere otro mapping.

### D6. Ventana de 6 meses para `momentum`

Spec dice "últimos 6 meses". Implementado como `now() - timedelta(days=180)`. Las menciones sin fecha parseable se descartan silenciosamente.

## Tests — diff

**Eliminados** (2):
- `test_tech_modernity_rewards_real_developer_surface_signals`
- `test_tech_modernity_does_not_inflate_from_framework_name_drops`

**Añadidos** (12):

`content_recency`:
- `test_content_recency_recent_publication_scores_high` (días=3 → 100)
- `test_content_recency_30_days_is_mid_high` (días=25 → 85)
- `test_content_recency_6_months_drops_to_mid` (días=150 → 40)
- `test_content_recency_past_year_is_low` (días=250 → 20)
- `test_content_recency_over_365_days_is_very_low` (días=400 → 10)
- `test_content_recency_no_dates_returns_neutral_with_reason` (exa=None → valor 30, raw dict con `reason: no_dates_found`)

`publication_cadence`:
- `test_publication_cadence_fewer_than_2_dates_is_low` (1 fecha → 20)
- `test_publication_cadence_regular_rhythm_scores_high` (mean_gap<30 → 90)
- `test_publication_cadence_moderate_rhythm_scores_mid` (mean_gap~100 → 50)

`momentum`:
- `test_momentum_without_llm_returns_heuristic_fallback` (llm=None → 50, fallback, `reason: llm_unavailable`)
- `test_momentum_with_llm_uses_structured_verdict` (mock devuelve JSON → score, source="llm", confidence 0.85, raw con verdict+evidence)
- `test_momentum_with_unclear_verdict_has_lower_confidence` (verdict=unclear → confidence 0.5)
- `test_momentum_with_no_recent_mentions_returns_fallback` (solo menciones >180d → fallback `reason: no_recent_mentions_6m`, mock con AssertionError para verificar que NO se llama)

`contrato`:
- `test_extract_always_returns_three_features` (web=None, exa=None → dict con 3 keys esperadas)

**Actualizados en `test_scoring_engine.py`**:
- Fixture 1 (`test_weighted_average_and_composite_score`): vitalidad con 3 features nuevas; añadido assert `dimensions["vitalidad"].score == 79.0`; composite esperado pasa de 66.3 a 66.95 (places=1).
- Fixture 2 (`test_frontier_ai_profile_prioritises_differentiation_and_vitality`): vitalidad con 3 features nuevas, valores (92, 82, 75).

## Resultado de tests

```
109 passed in 1.11s
```

(52 en los dos archivos focales + 57 en el resto del suite, 0 fallos, 0 regresiones detectadas.)

## Warnings no bloqueantes

Ninguno en este suite. El entorno usa pytest 9.0.3 sobre Python 3.11.8.

## Verificaciones manuales pendientes para el revisor

1. **Prompt del LLM en `analyze_momentum()`**: el prompt pide citas literales, ignorar falsos positivos, y fallback a `unclear` cuando hay ambigüedad. Comprobar que el wording es lo bastante fuerte; en producción puede necesitar pruebas contra muestras reales antes de ajustarlo.

2. **Escala de `publication_cadence` para 5+ datapoints**: la heurística de stddev/mean puede ser generosa o severa dependiendo de los datasets reales. Sin datos históricos para calibrar, dejé un rango amplio [40, 95]. El learning/calibration system (fuera de scope) puede tunearlo después.

3. **Caching**: los cachés viejos en SQLite tienen features con nombres obsoletos (`content_frequency`, etc). El `SQLiteStore` no crashea porque es agnóstico al schema, pero los runs viejos mostrarán features que el engine ya no conoce. No corrompe datos, solo quedan estancadas. Si se quiere limpieza explícita, crear un job aparte.

4. **Documentación en `docs/scoring_review.md`**: menciona las features viejas. No es código, no bloquea, pero conviene actualizar cuando se concluya el refactor de las 5 dimensiones.

5. **Extractor de `exa`**: en `vitalidad.py` llamo `getattr(exa, "brand_name", "")` para el momentum. Si `ExaData.brand_name` se renombra/remueve, el prompt queda con `brand_name=""`. Pequeño riesgo de silent degradation; si molesta, convertir a fallar ruidosamente.

## Fuera de scope — confirmado

- Otras dimensiones no tocadas.
- `ScoringEngine`, `niche/profiles.py`, `learning/`, `versioning`, `SQLiteStore`: intactos.
- `LLMAnalyzer` solo extendido con un método público nuevo; nada renombrado ni eliminado.
- No hay cambios en el modelo `FeatureValue`.
