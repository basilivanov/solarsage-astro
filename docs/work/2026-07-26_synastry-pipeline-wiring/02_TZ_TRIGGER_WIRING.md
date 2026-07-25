# 02_TZ: Синастрия — триггер генерации + credit spend в API (срез B)

## 1. Packet title
Синастрия — POST /api/synastry/partners: spend через service + 202 + background trigger. Срез B из 4. Зависит от принятого среза A (реальный pipeline в SynastryService).

## 2. Phase / Wave
W-SYNASTRY-MVP, fix-wave: pipeline wiring.

## 3. Modules
- M-API-SYNASTRY (`apps/api/app/api/synastry.py`)

## 4. Goal
`POST /api/synastry/partners` перестаёт создавать записи inline и становится тонким endpoint'ом над service:
1. Вызывает `SynastryService.create_partner_and_report(user.id, body)` — profile completeness 409, dedup 409, credit spend 402 + partner/report/spend в ОДНОЙ транзакции (уже реализовано в service, срез A его не ломал).
2. Возвращает **202 Accepted** с `SynastryGenerationRead` (поле-в-поле как сейчас: report_id, partner_id, state, stage, attempt_count).
3. После успешного commit запускает best-effort фоновую задачу: `asyncio.create_task(...)`, которая открывает СВОЮ сессию `async with SessionLocal() as db` и вызывает `SynastryService(db).run_report_pipeline(report.id)`; весь task обёрнут в try/except — исключение логируется (`synastry.calculation_failed`), task не должен падать необработанным. Успех task НЕ считается durable enqueue (по master TZ 10.2).

Успех = создание партнёра через API реально списывает кредит и запускает pipeline; pytest API зелёный.

## 5. Exact write scope
- `apps/api/app/api/synastry.py`
- `apps/api/tests/test_synastry_api.py`

## 6. Frozen / Out of scope
- НЕ трогать `synastry_service.py` (принят в срезе A; если там дефект — стоп, доложить).
- НЕ трогать models, schemas, frontend, jobs (reconcile — срез C).
- НЕ добавлять lease/claim в GET /status (это срез C).
- Остальные endpoints (list/status/detail/aspect/feedback/delete) не менять.

## 7. Must-preserve invariants
- Credit spend строго в одной DB-транзакции внутри service (инвариант master TZ 8.1/10.2).
- Background task запускается ТОЛЬКО после успешного commit (паттерн `apps/api/app/api/horary.py:223-225`: `asyncio.create_task(service._generate_answer_task(...))`; session-в-задаче — паттерн `apps/api/app/services/horary_service.py:383+`: `async with SessionLocal() as db`).
- Request-scoped session НЕ использовать внутри background task (она закрывается после ответа).
- Owner-scoped 404/409/402 семантика ответов сохраняется; detail-сообщения без PII в логах.
- Frontend-совместимость: клиент `lib/api/synastry.ts` проверяет `res.ok` — 202 совместим, тело ответа не меняется.
- GRACE-разметка обновляется по факту (emitted_logs, side_effects в FUNCTION_CONTRACT).

## 8. Verification commands
```bash
cd apps/api && source .venv/bin/activate
python -m pytest tests/test_synastry_api.py -q
python3 scripts/grace_lint.py apps/api/app   # из корня репо; обязателен PASS
```
Тесты обновить/расширить: 202 + списание кредита (used_amount+1, spend-запись создана) + запуск task замокан; 402 при отсутствии кредитов; 409 при дубликате; 409 при неполном профиле.

## 9. Expected evidence
- `git diff --name-only` — ровно 2 файла из scope.
- Вывод pytest (зелёный) и grace_lint PASS.
- В отчёте: как именно task получает сессию, куда добавлен create_task.

## 10. Escalation rule
Нужен соседний scope (service, models, frontend) → стоп, доложить, новый packet.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
