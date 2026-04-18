# Review report — Dimensión Presencia

## Resumen ejecutivo

- **Decisión**: APPROVE
- **Fixes aplicados**: 1
- **Bloqueantes**: 0
- **Advertencias**: 2

## Fixes aplicados por el revisor

### 1. `5eef1b9` — Zombie features en fixture `test_frontier_ai_profile_prioritises_differentiation_and_vitality`

**Archivo:** `tests/test_scoring_engine.py:126-127`.

Codex actualizó el primer fixture de presencia en el test principal, pero olvidó el segundo. El bloque seguía con `ai_visibility` y `directory_listings` (features eliminadas). El test pasaba porque `ScoringEngine` aplica neutral `50` a features ausentes, así que el runner no se quejaba — pero el fixture perdía intención: el 20.0 diseñado para `directory_presence` era ignorado y sustituido por 50 neutro.

Fix: reemplazar las 2 keys viejas por una sola `directory_presence` con valor 20.0, manteniendo la intención del diseño. El test sigue pasando y ahora evalúa lo que el autor pretendía.

Tipo: referencia zombi (regla #6 del review brief). Fix trivial.

## Bloqueantes restantes

Ninguno.

## Advertencias

### A1. Codex reportó falso positivo sobre `test_learning.py` y `test_main_experiment.py`

`REVIEW_NOTES.md` afirma que esos dos archivos fallan con `ModuleNotFoundError: No module named 'main'`. **No es regresión ni fallo real**: es un artefacto de correr `pytest` sin `PYTHONPATH=.`. Con el invocador correcto (`PYTHONPATH=. pytest` o con el paquete instalado vía `pip install -e .` en `.venv`), los 22 tests pasan tanto en `main` como en `refactor/presencia` (22 passed confirmado).

No bloquea merge. Sugerencia fuera de scope: añadir `pythonpath = ["."]` en `[tool.pytest.ini_options]` de `pyproject.toml`, o documentar el invocador en `README`.

### A2. `raw_value` como `dict` nativo vs JSON string

Codex eligió devolver `raw_value` como `dict` nativo (ver `REVIEW_NOTES.md` D1), mientras que Vitalidad (ya en main) serializa a JSON string porque `FeatureValue.raw_value` está tipado como `Optional[str]`. Es una decisión de diseño, no un bug, pero **se divergen los dos patrones** dentro del mismo engine. Los consumidores downstream (`SQLiteStore`, frontend) van a tener que manejar los dos formatos.

No bloquea merge (ambos enfoques funcionan runtime), pero conviene decidir en banda: o se cambia `FeatureValue.raw_value` a `Any` y se unifican ambas dimensiones en dict, o se fuerza JSON string también en Presencia. Queda flaggeado para el humano si quiere coherencia cross-dimensional.

## Tests

```
124 passed in 2.41s
```

Suite completa ejecutada tras el fix. Archivos focales (`test_feature_extractors.py`, `test_scoring_engine.py`) con 67 tests + resto del suite 57 tests.

### Cumplimiento del prompt verificado

- ✅ 4 features con nombres exactos: `web_presence`, `social_footprint`, `search_visibility`, `directory_presence` (`dimensions.py:152-167`, `presencia.py:158-161`).
- ✅ Pesos `0.30 / 0.35 / 0.25 / 0.10`. Suman 1.0 (assert en `dimensions.py` pasa en import).
- ✅ `ai_visibility` eliminada como feature independiente; lógica absorbida en `search_visibility` (`presencia.py:398-414`).
- ✅ `directory_listings` renombrado a `directory_presence`.
- ✅ `raw_value` estructurado (dict) en las 4 features.
- ✅ `PresenciaExtractor.__init__` sin argumento `llm` (`presencia.py:23-24`).
- ✅ Regla `marca_fantasma` en `engine.py:70, 83-85, 99-100` sigue usando `web_presence` y `social_footprint` sin cambios; `test_presence_ghost_brand_rule_caps_score` actualizado con los nuevos nombres y pasa.
- ✅ Matemáticas del assert `presencia.score == 76.25` verificadas a mano: `0.30*90 + 0.35*75 + 0.25*80 + 0.10*30 = 76.25` ✓.
- ✅ `brand_service.py` sigue instanciando `PresenciaExtractor()` sin cambios (no aparece en el diff vs main).

### Bugs potenciales revisados, descartados

- `exa.mentions[:3]`, `exa.ai_visibility_results[:5]`: safe por `field(default_factory=list)` en `ExaData`.
- División por cero: `_search_visibility` y `_social_footprint` no dividen; sumas ponderadas con constantes, sin denominadores derivados de input.
- `max([])` / slicing fuera de rango: no encontrado. Todos los slicings son `[:3]` y `[:5]`, safe aun con listas vacías.

## Notas cualitativas

- Evidencia literal preservada: `search_visibility.raw_value.evidence` lista 3 resultados con `{url, title, snippet}` (`presencia.py:422-430`). `directory_presence` emite listas explícitas de dominios encontrados por tier. Útil para conversación comercial.
- `social_footprint` sin `SocialData` degrada a score 15 + `reason=no_social_data` en lugar de ceros silenciosos. Bien para el producto.
- `_parse_last_post_days_ago` es defensivo ante strings vagos tipo "3 days ago" o fechas estructuradas. Bug edge-case leve: devuelve 0 para cualquier cantidad de "hours ago" (no amortigua 23h vs 1h), pero es lo bastante granular para el uso. Decisión de diseño, no bug.

---

**Branch:** `refactor/presencia`
**Último commit:** `5eef1b9`
**Base:** `main` (Vitalidad ya en main)

# Review report — Dimensión Coherencia

## Resumen ejecutivo

- **Decisión**: APPROVE
- **Fixes aplicados**: 1
- **Bloqueantes**: 0
- **Advertencias**: 2

## Fixes aplicados

- `1192e68` — degradé `confidence` en `tone_consistency` cuando `examples` llega con shape malformada y se filtra por completo ([src/features/coherencia.py](/Users/gsus/Antigravity/Brand3/brand3/src/features/coherencia.py:90), [src/features/coherencia.py](/Users/gsus/Antigravity/Brand3/brand3/src/features/coherencia.py:434)). Antes solo degradaba si `gap_signal != "none"`, así que una respuesta LLM con evidencia rota podía quedar con `confidence=0.85`.

## Bloqueantes restantes

Ninguno.

## Advertencias

### A1. El prompt original no está en el repo, así que el cumplimiento literal no puede verificarse al 100%

No encontré `brand3-coherencia-implement-claudecode.md` ni variantes cercanas en el workspace. Pude verificar el estado final del código contra los requisitos listados en tu brief actual, pero no cerrar una auditoría línea por línea contra el prompt original del implementador.

### A2. La cobertura de tests de Coherencia aún deja huecos en contratos LLM negativos

Los tests cubren bien `messaging_consistency` con `verdict` inválido y `gaps` malformados, pero no encontré un test explícito para:
- `messaging_consistency` con `verdict="unclear"`
- `tone_consistency` con `gap_signal` inválido
- `tone_consistency` con `examples` no-lista o items malformados

No es bloqueante porque el código ahora maneja parte de ese path, pero sigue siendo un hueco de regresión.

## Tests

- `PYTHONPATH=. ./.venv/bin/pytest -v` → **132 passed**
- `PYTHONPATH=. ./.venv/bin/pytest tests/test_feature_extractors.py tests/test_scoring_engine.py -v` → **75 passed**

Verificación focal de Coherencia:
- `dimensions.py` declara exactamente `visual_consistency`, `messaging_consistency`, `tone_consistency`, `cross_channel_coherence` con pesos `0.25 / 0.40 / 0.20 / 0.15`.
- `raw_value` de las 4 features sale como dict nativo en [src/features/coherencia.py](/Users/gsus/Antigravity/Brand3/brand3/src/features/coherencia.py).
- `coherencia_llm.py` no existe.
- `CoherenciaExtractor` acepta `llm`, `visual_analyzer`, `skip_visual_analysis`.
- `brand_service.py` instancia `CoherenciaExtractor(llm=llm, skip_visual_analysis=skip_visual_analysis)`.
- `LLMAnalyzer` conserva `analyze_coherence` y añade `analyze_messaging_consistency` y `analyze_tone_consistency`.
- `test_weighted_average_and_composite_score` está matemáticamente correcto:
  `coherencia = 0.25*80 + 0.40*60 + 0.20*70 + 0.15*50 = 65.5`
  y el composite `69.2` también cuadra con los pesos de dimensión actuales.

## Notas cualitativas

- `messaging_consistency` preserva evidencia útil para conversación comercial: `self_category`, `third_party_category`, `aligned_themes`, `gaps`, `reasoning`.
- `tone_consistency` conserva citas literales en `examples`, pero el contrato usa `gap_signal` en vez de `verdict`. Como el prompt original no está disponible, lo dejo como observación y no como fallo literal.
- Los fallbacks heurísticos de Coherencia devuelven razones y señales accionables; no son solo scores neutrales mudos.
