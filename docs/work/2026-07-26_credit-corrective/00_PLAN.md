# Credit corrective wave — план срезов (по 00_TZ.md corrective-релиза)

Master: `docs/work/2026-07-26_post-synastry-live-corrective/00_TZ.md` (authority).
Дата: 2026-07-26. Base SHA после parity-волны: `87a3637`.

## Preflight (выполнено ревьюером)

- git: только чужой binary-churn PNG (не трогаем) и next-env.d.ts (build churn, в коммиты не включать — §14.5).
- alembic head: `0025_synastry_schema` ✓ → следующая миграция 0026, один parent.
- DB product row: `synastry | is_active=false | one_time | 39900 | quota 1` ✓ (до миграции).
- Baseline targeted tests (§14.1) — прогон запущен, результат приложить.

## Отклонение от нумерации миграций в master-TZ

Master называет `0026_synastry_live_corrective.py` для product activation. Но §15 требует Release A БЕЗ product flip, а request_hash нужен уже в Release A. Поэтому:
- `0026_synastry_spend_request_hash` — Release A (spend fingerprint).
- `0027_synastry_product_live` — Release B (is_active=true и пр.). Содержание идентично §8.1.

## Срезы

| # | Срез | Master разделы | Release |
|---|------|----------------|---------|
| C1 | weekly-free race + refund lock + observability events | 7.1, 7.4, 11 | A |
| C2 | spend correctness + idempotency + request_hash + capabilities | 7.2, 7.3 | A |
| C3 | purchase backend: catalog, slugs, fulfill attribution, webhook | 8.1, 8.2 | B |
| C4 | purchase sheet + zero-credit UX + SynastryApiError | 8.3, 9 | B |
| C5 | sidecar planet.house + API fallback + cache bump | 10 | A |
| C6 | gates §14 + AGENTS.md cleanup + matrix + deploy A→B | 12-16 | A+B |

Порядок: C1 → C2 → C5 (backend, Release A) → deploy A → C3 → C4 (Release B) → C6.

## Заметки для срезов

- `HoraryCreditService` уже имеет `select_spendable_credit(lock=)`, `get_balance`, `get_or_create_current_weekly_free` — использовать, не дублировать.
- Real-PG concurrency test: disposable БД на том же инстансе (`astro_test`), создание/дроп в fixture; unit SQLite не доказывает race (§7.1).
- Observability: события §11 сначала в `grace/canon/observability.xml`, registry — штатным generator'ом, generated файлы руками не править.
