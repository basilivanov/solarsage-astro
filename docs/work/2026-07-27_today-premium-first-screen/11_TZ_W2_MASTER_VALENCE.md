# W2 MASTER: честная valence-агрегация Today, 12 сфер и трёх горизонтов

Дата: 2026-07-27
Нормативный контракт: `docs/work/2026-07-25_today-sphere-valence-correction/00_TZ.md`
(803 строки — source of truth для всех срезов W2) + `01_TECHNICAL_PREMORTEM.md`
(verdict: GO WITH CONDITIONS; NO-GO для prod selection до shadow/rollback gates).
Исполнитель: кодер (opencode/Gemini, tmux astro2). Архитектор/ревьюер: Kimi.
Коммит/пуш: только ревьюер.

## 0. Pre-flight решения (архитектор, §15 нормативного ТЗ)

1. **Family decay [1.0, 0.5, 0.25]** — ПОДТВЕРЖДЕНО (владелец уведомлён;
   veto принимается до V4).
2. **Verdict thresholds §6.6** (avoid: tension≥1.50 и tension≥support×2;
   caution: tension≥0.75 и tension>support×1.30; good: support≥0.75 и
   support>tension×1.30) — ПОДТВЕРЖДЕНО.
3. Semantic-key parity sidecar/API — доказывается property fixtures в V2.
4. Sanitized prod fixtures (P-BASIL-2026-07-25/23) — строятся в V6.
5. Horizon no-drift baseline — захватывается в V1 до любых изменений.

## 1. Цель волны

Честные verdict'ы 12 сфер и day status из canonical factor ledger:
salience остаётся для ranking/selection, signed valence — для verdicts.
Корень устраняет прод-симптом «day_status=tense при good=11/12» и
пользовательскую жалобу «все дни одинаковые».

## 2. План срезов

| Срез | Содержание | Файлы |
|---|---|---|
| **V1** | canon + schemas + no-drift baseline | `grace/canon/day_valence.v1.yml`, `apps/api/app/schemas/day_valence.py`, loader+tests, golden horizon selection |
| **V2** | factor ledger | `apps/api/app/services/day_factor_ledger.py`, property fixtures signal↔activation |
| **V3** | valence engine | `apps/api/app/services/day_valence_service.py`, 14 trap-case fixtures |
| **V4** | shadow wiring + observability | flags, scoring_v2/day_scoring_runtime, `scoring.valence_*` events (registry first), metrics |
| **V5** | integration + versions + contracts | interpretation assessments, horizon tone, ss-scoring-2.1/today.v2.2/frontend 4, cache identity, contracts regen |
| **V6** | sanitized fixtures + shadow report | P-BASIL-* fixtures, DUAL_RUN на деве, canary audit, review |

После V6 — shadow review, затем W3 (frontend чипы) и Release B/prod.

## 3. Сквозные запреты (все срезы)

- LLM/frontend не рассчитывают numeric truth, verdict, counts.
- salience нигде не превращается в good/bad напрямую.
- Нет DB-миграций и удаления старых cache rows.
- Banned: логирование ПДн, birth data, raw aspects, имён пользователей.
- `pnpm contracts:check` зелёный после каждого contract-изменения.
- GRACE-разметка в новых/изменённых файлах + owned_tests.

## 4. Приёмка волны

Гейты §14.4 нормативного ТЗ + все merge-blocking gates §15 зелёные.
