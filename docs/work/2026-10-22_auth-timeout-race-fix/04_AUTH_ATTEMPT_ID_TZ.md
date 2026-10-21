# TZ 04: auth_attempt_id — сквозная корреляция попытки входа

1. **Packet title**: SLICE-04 auth_attempt_id end-to-end
2. **Phase / Wave**: W-AUTH-TIMEOUT-RACE-FIX (2026-10-22), срез 04/05
3. **Modules**: M-HOOK-TELEGRAM-AUTH (frontend), M-AUTH-TG (`apps/api/app/api/auth.py`),
   `apps/api/app/schemas/auth.py`, `apps/api/app/core/logging.py`
4. **Goal**: каждая попытка `authenticate()` имеет uuid `auth_attempt_id`; фронт шлёт его
   в `POST /api/auth/telegram`; бэкенд прикладывает к `auth.tg_login_succeeded/failed` и в
   log context — цепочка «попытка фронта → запрос бэкенда» грепается одним ID.

## 5. Exact write scope

- `hooks/use-telegram-auth.ts` (только генерация/прокидывание id + поля в логах)
- `apps/api/app/schemas/auth.py` (additive optional field)
- `apps/api/app/api/auth.py` (payload + bind)
- `apps/api/app/core/logging.py` (additive kwarg в `bind_log_context`)
- Один backend-тест: ближайший существующий `apps/api/tests/**/test*auth*.py` (расширить) — выбрать по месту.

## 6. Frozen / out-of-scope

- Все прочие backend файлы; `apps/api/app/core/logging_events.py` (новых событий нет — используются существующие `auth.tg_login_*`).
- `grace/canon/observability.xml`, `lib/log/events.gen.ts` — не трогать (новых имён событий нет).
- db_connect_ms/db_query_ms разбивка (ТЗ 2026-09-27 §2.3.3) — НЕ в этом срезе.
- Фронт-файлы кроме хука auth.

## 7. Must-preserve invariants

- Контракт `TelegramAuthRequest` — только additive (`auth_attempt_id: str | None`, max 64, pattern `[A-Za-z0-9-]+`); старые клиенты без поля работают.
- Никакого PII/raw initData в логах; payload-ключи как сейчас + `auth_attempt_id`.
- `python3 scripts/grace_lint.py apps/api/app` → PASS (обновить emitted_logs/contract комментарии под новые поля payload).
- Фронт: auth_attempt_id — uuid (`crypto.randomUUID()`), новый на каждый `authenticate()`/`retry()`; в TIMEOUT/success/fail логах фронта — рядом с attempt/duration.

## Техническое задание

1. Фронт (`hooks/use-telegram-auth.ts`): генерировать `auth_attempt_id` в начале каждой
   попытки; включать в тело POST `{ initData, auth_attempt_id }` (camelCase — backend
   CamelModel маппит); добавлять в warn/info логи попытки.
2. Схема (`apps/api/app/schemas/auth.py`): `TelegramAuthRequest` += optional
   `auth_attempt_id` (alias camelCase), валидация длины/паттерна, None по умолчанию.
3. API (`apps/api/app/api/auth.py`): если поле пришло —
   `bind_log_context(auth_attempt_id=...)` (новый additive kwarg, см. п.4) и
   `payload={..., "auth_attempt_id": ...}` в `auth.tg_login_succeeded` и
   `auth.tg_login_failed` (failed — в обеих ветках: verify error и прочих, где доступно).
4. `apps/api/app/core/logging.py`: `bind_log_context(..., auth_attempt_id: str = "")` —
   additive; пустая строка = не биндить (как остальные kwargs).
5. Тест: POST с `auth_attempt_id` → событие `auth.tg_login_succeeded` содержит его в payload;
   POST без поля → 200, событие без ключа (или None-эквивалент). Использовать существующие
   фикстуры auth-тестов.

## 8. Verification (одна команда)

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q -k auth && python3 scripts/grace_lint.py apps/api/app && cd /opt/solarsage-astro && npx vitest run __tests__/hooks/useTelegramAuth.test.ts
```

## 9. Expected evidence

diff по файлам п.5; PASS pytest (auth), grace_lint PASS, vitest PASS; пример строки лога с auth_attempt_id (из теста/мока).

## 10. Escalation rule

Нужна правка observability.xml / новых имён событий / middleware → стоп, доложить, новый packet.

## 11. No-commit rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
