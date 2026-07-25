# 03_TZ: Синастрия — reconcile job для зависших репортов (срез C)

## 1. Packet title
Синастрия — one-shot job `synastry_reconcile`: восстановление репортов, зависших в нефинальных состояниях. Срез C из 4. Зависит от принятых A (pipeline) и B (триггер).

## 2. Phase / Wave
W-SYNASTRY-MVP, fix-wave: pipeline wiring.

## 3. Modules
- M-JOBS-SYNASTRY-RECONCILE (`apps/api/app/jobs/synastry_reconcile.py`, новый)

## 4. Goal
Репорты, зависшие из-за смерти процесса/рестарта (best-effort task не durable — master TZ 10.2), подбираются и доводятся до финального состояния. One-shot job по образцу `apps/api/app/jobs/billing_rebill.py`:

1. Найти активные (`invalidated_at IS NULL`) репорты:
   - `state = 'pending'` И `created_at < now() - interval '5 minutes'` (task так и не стартовал), ИЛИ
   - `state IN ('calculating', 'narrative_generating')` И `updated_at < now() - interval '5 minutes'` (процесс умер mid-flight).
2. Для каждого (лимит 20 за прогон, ORDER BY updated_at): запустить `SynastryService(db).run_report_pipeline(report.id)`. Pipeline идемпотентен по sidecar (пересчёт детерминирован) и ограничен по LLM (attempt_count ≤ 2): при исчерпании сам уйдёт в failed + refund — это и есть терминализация.
3. Итог по каждому репорту залогировать (`synastry.calculation_succeeded` при ready, `synastry.calculation_failed` при failed); ошибки одного репорта не роняют прогон.
4. `main() -> int` (0 = успех прогона, 1 = были необработанные ошибки), `asyncio.run` — как billing_rebill. Запуск: `python -m app.jobs.synastry_reconcile` из apps/api с env .env.

## 5. Exact write scope
- `apps/api/app/jobs/synastry_reconcile.py` (новый)
- `apps/api/tests/test_synastry_reconcile.py` (новый)

## 6. Frozen / Out of scope
- НЕ трогать service, api, models (никаких новых колонок/миграций — lease-колонка уже есть, но lease-claim НЕ вводить в этом срезе; staleness определяется по updated_at/created_at).
- НЕ трогать billing_rebill.py и другие jobs.
- Планировщик (systemd timer / compose profile) — НЕ в этом срезе, делает ревьюер при деплое.

## 7. Must-preserve invariants
- Только чтение + делегирование в `run_report_pipeline`; никакой своей state machine.
- Никаких внешних вызовов под открытой транзакцией (service сам управляет commit'ами).
- Логи через `log_event` из `app.core.logging` (события только из registry `app/core/logging_events.py`), без PII (имена/даты рождения не логировать).
- GRACE-разметка нового файла по канону (AI_HEADER, MODULE_CONTRACT, MODULE_MAP с owned_tests, FUNCTION_CONTRACT).

## 8. Verification commands
```bash
cd apps/api && source .venv/bin/activate
python -m pytest tests/test_synastry_reconcile.py -q
python3 scripts/grace_lint.py apps/api/app   # из корня репо; обязателен PASS
```
Тесты (AsyncMock-паттерн как в test_synastry_service.py): выборка pending-stale и calculating-stale вызывает pipeline; ready/failed/свежие не трогаются; исключение в одном репорте не роняет прогон.

## 9. Expected evidence
- `git diff --name-only` — ровно 2 новых файла.
- Вывод pytest (зелёный) и grace_lint PASS.

## 10. Escalation rule
Нужен lease-claim / новая колонка / изменение service → стоп, доложить, новый packet.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
