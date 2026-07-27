# V5 TZ: integration — assessments в сферы, horizon tone, версии, contracts

Дата: 2026-07-27
Phase / Wave: **W2-VALENCE**, срез V5
Master: `docs/work/2026-07-27_today-premium-first-screen/11_TZ_W2_MASTER_VALENCE.md`
Норматив: `docs/work/2026-07-25_today-sphere-valence-correction/00_TZ.md` §8–10, §14.2
Modules: `M-API-TODAY-INTERPRETATION-SERVICE`, `M-API-HORIZON-TONE`, `M-API-VERSIONS`, `M-SCHEMAS-TODAY`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Goal

При `TODAY_VALENCE_V1_ENABLED=true` selected payload получает честные
verdict'ы: `ConcreteAdviceRow.assessment` из нового engine, horizon tone
из corrected verdicts, версии/cache identity `ss-scoring-2.1 /
today.v2.2 / frontend 4`, Today и Calendar одинаковый status.
При `ENABLED=false` всё остаётся ровно как сейчас (V4 shadow).

## 2. Exact write scope

- `apps/api/app/schemas/today.py` — `ConcreteAdviceRow.assessment:
  SphereValenceRead | None` (§9.1); `TodayV2Audit` += `valenceVersion` +
  `dayStatusBreakdown`.
- `apps/api/app/services/today_interpretation_service.py` — при ENABLED:
  rows получают verdict/assessment из engine (не из `verdict_for_score`);
  counts §7.2; assessment НЕ проходит через LLM (LLM видит текстовый
  контекст, не numeric поля).
- `apps/api/app/services/today_horizon_integration_service.py` (или
  horizon tone service) — `sphere_component` тона только из
  `ProductSphereAssessment.verdict` связанных сфер (§8.2); selection
  не меняется (§8.1, no-drift golden из V1).
- `apps/api/app/core/versions.py` — bump при ENABLED: `ss-scoring-2.1`,
  `today.v2.2`, `V2_FRONTEND_PAYLOAD_VERSION=4`, `TODAY_CONTENT_VERSION=11`;
  compatibility pair previous/current (§9.3).
- `apps/api/app/services/today_service.py`, `calendar_service.py`,
  `cache_key_service.py` — единая selected identity; Today/Calendar
  same-date parity (§10).
- `npm run contracts:generate` + `lib/contracts/today.ts` — регенерация
  после pydantic-изменений (wire source of truth §9.2).
- Тесты §14.2: 12 assessments в selected payload; counts == 12;
  Today/Calendar parity hit/miss; previous cache не читается как current;
  horizon selection IDs/timing no-drift на baseline fixture (V1 golden);
  tone использует corrected verdicts; `pnpm contracts:check`.

## 3. Frozen / out-of-scope

- Frontend UI (W3). Модель/промпты LLM. Scoring salience/selection.
- Прод-включение флага (Release B — отдельное решение после V6).

## 4. Must-preserve

- `ENABLED=false` → byte-identical текущее поведение (тест).
- LLM не владеет numeric/verdict полями (spy-тест §15).
- Banned-жаргон валидатор и M6/M7 детерминированный why не ломать.

## 5. Verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q -k "valence or horizon or calendar_parity or versions"
pnpm contracts:check
```

## 6. Expected evidence

- Файлы, вывод verification, contracts:check вывод, no-drift golden
  сравнение (selected IDs до/после).

## 7. Escalation rule

Нужен файл вне §2 / drift в horizon selection — стоп, доложить. Ничего не
коммить и не пушить.
