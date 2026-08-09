# S21 — Sanitizer facet-exclusivity rebalance (grounding false positives)

Дата: 2026-08-09. Пакет по остаточной проблеме №1 из S16-хвостов, подтверждённой
боевыми данными после миграции flash+strict (04_TZ в `docs/work/2026-08-09_narrative-model-eval/`).

## Фактура (проверено ревьюером)

- Eval run `20260809T082931Z`: `sanitizer_pass` 0.38–0.68 у ВСЕХ моделей и плеч —
  санитайзер режет треть-половину claims независимо от модели. Это главный
  множитель потери качества narrative.
- Dev-прод после миграции (2026-08-09, pregen run4): fill rate 2/9, 7/9, 3/9 →
  44%. Тексты flash хорошие, но две трети зануляются нашим же фильтром.
- Механика (`apps/api/app/services/narrative_sanitizer.py`):
  `has_narrative_grounding_violation` → `detected_facets.difference(normalized_facets)`
  → null. Любое «узкое» слово чужого фасета убивает claim целиком, даже бытовое
  («уют», «нежность», «вялость»). Полярность: антоним в окне 40 символов без
  маркера смягчения → null. S17 уже починил маску жребиев и окно отрицания;
  остаток — facet-эксклюзивность и мягкая лексика.
- Eval-scorer импортирует продовый санитайзер (`scripts/narrative_model_eval.py:1057`),
  и 280 raw-ответов сохранены в `.eval-runs/narrative-model-eval-v1/20260809T082931Z/`
  → **бесплатный offline A/B цикл без API-вызовов**.

## Задачи кодера

### A1. Аудит-дамп (offline, бесплатно)

Скрипт `scripts/narrative_sanitizer_audit.py`: по сохранённым raw-ответам run'а
выгружает per-claim вердикты → `evals/results/20260809T082931Z/sanitizer-audit.json`:
- claim text (маскированный), facet, polarity, verdict (pass/null);
- класс правила: `facet_conflict | sphere_conflict | polarity_antonym | forbidden_token`;
- id сработавшего паттерна + пара (claim facet × detected facet).
Сводка: counts по классам правил и матрица facet×facet. Это распределение —
обязательная опора для A2 (не перебалансировать вслепую).

### A2. Ребаланс правил (`narrative_sanitizer.py`)

Направление (уточнить по аудиту):
- разделить `_FACET_PATTERNS` на hard (доменные: кредит, брак, карьера, начальник…)
  и soft (бытовые: уют, нежность, тепло, вялость…); soft cross-facet слова НЕ
  зануляют claim;
- fail-closed сохранить для hard cross-sphere утечек и forbidden tokens
  (Transit_/Natal_, служебные id);
- polarity-антонимы: расширить маркеры смягчения, если аудит покажет false hits
  (пример из S16: «снизить напряжение» в supportive).
Конкретный split обосновать в docstring примерами из аудита.

### A3. Продовая инструментация

Per-claim событие `day.narrative_claim_nulled` (slice `W-TODAY-CONVERGENCE-REWRITE`,
module `M-TODAY-NARRATIVE`), payload: `{reason_class, facet, polarity, pattern_id}` —
БЕЗ текста и PII. Сначала регистрация события в `apps/api/app/core/logging_events.py`
по канону, потом использование. Это даёт постоянный замер fill rate на проде.

### A4. Тесты

- Golden set из аудита: реальные занулённые-но-хорошие тексты обязаны проходить
  после ребаланса.
- Canned bad cases обязаны по-прежнему зануляться: cross-sphere утечка,
  Transit_/Natal_, диагнозы здоровья, polarity-антоним без смягчения.
- Существующие тесты санитайзера — зелёные, либо явно обновлены с rationale.

### A5. Offline-валидация (бесплатно)

Пересчёт scorer'ом сохранённых 280 ответов с новым санитайзером
(`python3 scripts/narrative_model_eval.py score ...` — без сети):
- `sanitizer_pass` у flash-strict и gemma-strict ≥ 0.85 (было 0.58-0.64);
- forbidden-token детекция не деградирует (selftest bad-case остаётся 0).

### A6. Доки

- Строка S21 в `02_SLICE_PLAN.md`.
- AGENTS.md — только если где-то описано поведение санитайзера (проверить).

## НЕ в скоупе

- Промпт, модели, роутинг — не трогаем.
- Дубли групп в selection (проблема №2 из S16-хвостов) — отдельный пакет S22.
- Платные вызовы запрещены.

## Done-критерии

- [ ] sanitizer-audit.json с распределением по классам правил
- [ ] ребаланс с обоснованием в docstring
- [ ] `day.narrative_claim_nulled` зарегистрировано и эмитится
- [ ] golden/bad-case тесты зелёные; полный pytest (not integration) зелёный
- [ ] offline re-score: sanitizer_pass flash/gemma strict ≥ 0.85
- [ ] grace_lint чисто; slice plan обновлён
