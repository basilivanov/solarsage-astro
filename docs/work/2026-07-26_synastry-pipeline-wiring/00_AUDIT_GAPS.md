# Синастрия — аудит реализации против master TZ (2026-07-26)

Master TZ: `/tmp/solarsage-astro-synastry-spec/docs/work/2026-07-25_synastry-prototype/01_TZ_REACT_ADAPTATION.md`
(разделы 3.1 sidecar, 3.3 API, 8.x billing, 10.2 state machine, 11 rollout).
Срезы: `docs/work/2026-07-25_synastry-prototype/0N_TZ_*.md`.

## Реализовано

- DB schema: migration `0025_synastry_schema.py`, 5 таблиц, lease/attempt колонки — OK.
- Pydantic schemas `app/schemas/synastry.py` — OK.
- Scoring engine `synastry_scoring.py` — OK.
- LLM module `synastry_llm.py`: prompt builders + validators (pure) — OK.
- API endpoints `app/api/synastry.py` — все 9, owner-scoped; router смонтирован фиксом 35e8beb.
- Sidecar `POST /v1/synastry` — OK, проверен вживую на деве.
- Frontend screens + client `lib/api/synastry.ts` — OK, задеплоено (`res.ok` — совместим с 201/202).
- Тесты: 5 backend + 3 vitest + e2e spec — существуют, зелёные (но писаны под stub).
- Billing: product row `synastry` is_active=False (fail-closed) — по замыслу Release A.

## Разрывы (что дописываем)

| # | Разрыв | Где | Срез |
|---|--------|-----|------|
| 1 | `run_report_pipeline` — stub: hardcoded aspects вместо sidecar, hardcoded narrative вместо LLM, нет refund | `synastry_service.py:203-323` | 01 |
| 2 | Нет триггера генерации: POST /partners не запускает task; API дублирует создание inline без credit spend (обходит `create_partner_and_report`); POST должен вернуть 202 | `api/synastry.py:201-279` | 02 |
| 3 | Нет reconcile job `apps/api/app/jobs/synastry_reconcile.py` (stale leases, retry ≤3, refund) | отсутствует | 03 |
| 4 | Drilldown — stub (Sun/Moon/trine всегда, без LLM) | `synastry_service.py:325-408` | 04 |
| 5 | Feature flags `SYNASTRY_ENABLED` / `NEXT_PUBLIC_SYNASTRY_ENABLED` (rollout Release A/B) | отсутствуют | отложено (prod rollout) |
| 6 | Lease-claim при исполнении (conditional update, 5 мин) | не используется | 03 |

## Порядок срезов

1. `01_TZ_REAL_PIPELINE.md` — реальный pipeline в service (sidecar→scoring→LLM→persist, refund при failed).
2. `02_TZ_TRIGGER_WIRING.md` — API wiring: spend через service + 202 + asyncio.create_task trigger.
3. `03_TZ_RECONCILE_JOB.md` — jobs/synastry_reconcile.py + lease claim.
4. `04_TZ_REAL_DRILLDOWN.md` — drilldown через LLM.
