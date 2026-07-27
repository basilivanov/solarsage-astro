# V4 TZ: shadow wiring — flags, dual-run, observability events + metrics

Дата: 2026-07-27
Phase / Wave: **W2-VALENCE**, срез V4
Master: `docs/work/2026-07-27_today-premium-first-screen/11_TZ_W2_MASTER_VALENCE.md`
Норматив: `docs/work/2026-07-25_today-sphere-valence-correction/00_TZ.md` §11, §13
Modules: `M-DAY-SCORING-RUNTIME`, `M-API-LOGGING`, `M-API-CONFIG`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Goal

Новый valence engine считает ТЕНЬЮ рядом с legacy на каждом day payload:
public result и cache identity остаются legacy (`ss-scoring-2.0`), shadow
считает и логирует только агрегированные diffs. Fail-closed: ошибка нового
движка не влияет на legacy payload.

## 2. Exact write scope

- `apps/api/app/core/config.py` — server-only flags:
  `TODAY_VALENCE_V1_ENABLED=false`, `TODAY_VALENCE_V1_DUAL_RUN=false`.
- `apps/api/app/core/logging_events.py` — СНАЧАЛА registry: добавить
  `scoring.valence_diff`, `scoring.factor_deduplicated`,
  `scoring.valence_selected`, `scoring.valence_failed` (канон §13).
- `apps/api/app/services/day_scoring_runtime_service.py` (и/или
  `scoring_v2_service.py` — выбрать одну точку, зафиксировать в отчёте):
  - DUAL_RUN=true: построить ledger (V2) + engine (V3) на том же immutable
    input, НЕ менять selected result; log `scoring.valence_diff`
    (old/new day status, verdict-count diff, duplicate count) и
    `scoring.factor_deduplicated` (агрегаты, без factor text).
  - ENABLED=true: код-путь selected=new engine (для V5; флаг по умолчанию
    false) + `scoring.valence_selected`.
  - Исключение в shadow/selected пути → `scoring.valence_failed` +
    legacy продолжает работу (fail-closed).
  - Flag snapshot один раз на request до cache read (§10).
- Метрики (§13) в стиле существующего `app/api/metrics.py`:
  `today_day_status_total{version,status}`,
  `today_sphere_verdict_total{version,verdict}`,
  `today_valence_duplicate_factors{source_pair}`,
  `today_valence_effective_factors{family}`.
- `apps/api/tests/` — dual-run тесты: один immutable input; shadow не меняет
  public result; events emitted; fail-closed при исключении engine;
  метрики инкрементируются.

## 3. Frozen / out-of-scope

- Payload contract/versions (V5), interpretation/horizon (V5), frontend.
- Никакого selected=new по умолчанию: флаги выключены.
- ПДн/raw aspects в логах — запрещено (§13).

## 4. Must-preserve

- Public day status/verdicts/cache identity НЕ меняются при DUAL_RUN=true.
- Registry-first: события только из logging_events.py.
- GRACE + owned_tests; `python3 scripts/check_logging_guardrails.py` зелёный.

## 5. Verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q -k "dual_run or valence_shadow or scoring_runtime"
```

## 6. Expected evidence

- Файлы, вывод verification, пример одного sanitized shadow-лога
  (текстом, без ПДн).

## 7. Escalation rule

Нужен файл вне §2 — стоп, доложить. Ничего не коммить и не пушить.
