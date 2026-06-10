# ТЗ: исправить pre-existing gates вне natal-фичи

Date: 2026-06-11
Status: TODO
Scope: технический долг после merge `feat/natal-full-report`

## 1. Цель

Вернуть pre-merge gates в зелёное состояние после merge natal full report, не меняя бизнес-логику Wave 1–6.

Исправляем только заранее существующие проблемы:

1. `test_solarsage_client ×2` — Pydantic/schema drift: sidecar вернул `latitude`.
2. `test_llm_fallback` — day endpoint зависит от sidecar.
3. `test_alembic_roundtrip` — тест жёстко ожидает `.venv/bin/alembic`.
4. TypeScript errors в не-natal модулях:
   - `hooks/use-chat.ts`
   - `lib/reducers/chat-reducer.ts`
   - `hooks/use-telegram-auth.ts`
   - `hooks/use-telegram-user.ts`
   - `lib/log/index.ts`
   - `block-renderer.tsx`
   - другие pre-existing файлы из текущего `pnpm typecheck`.

## 2. Ветка

Создать отдельную ветку от актуального `main`:

```bash
git checkout main
git pull
git checkout -b fix/pre-existing-gates
```

Не смешивать с natal feature work. Natal full report уже считается принятым и смёрженным.

## 3. Non-goals

Не делать:

- не менять архитектуру natal pipeline;
- не менять golden fixture Жанны;
- не переписывать report generation;
- не чинить visual/Playwright baseline в этом пакете;
- не скрывать ошибки через массовый `any`;
- не отключать `typecheck`;
- не отключать backend tests;
- не добавлять `skip` без явной причины и follow-up.

## 4. Work package A — `test_solarsage_client ×2`

### Проблема

Pydantic-схема клиента SolarSage не совпадает с фактическим ответом sidecar: sidecar возвращает поле `latitude`, а текущая модель/валидатор падает.

### Требование

Синхронизировать контракт `SolarSageClient` с реальным sidecar response.

Допустимые решения:

1. Если `latitude`/`longitude` являются легитимными полями sidecar response — добавить их как optional поля в соответствующую Pydantic-схему.
2. Если sidecar может отдавать дополнительные metadata-поля — разрешить extra fields только на нужном уровне схемы, не превращая всю схему в бесконтрольный `dict`.
3. Если `latitude` должен мапиться в существующее поле — добавить явный alias.

### Acceptance criteria

- `test_solarsage_client` больше не падает на поле `latitude`.
- Схема всё ещё валидирует обязательные поля: planets, houses, signs, longitudes.
- Некорректный ответ без ключевых chart fields по-прежнему падает.
- Добавлен или обновлён тест на sidecar response с `latitude`.

## 5. Work package B — `test_llm_fallback`

### Проблема

Тест fallback для LLM/day endpoint не изолирован от sidecar. Day endpoint зависит от natal/transit data, поэтому тест падает не на fallback-логике, а на внешней зависимости.

### Требование

Сделать тест детерминированным.

Нужно явно разделить:

- fallback LLM behavior;
- sidecar availability;
- day endpoint orchestration.

### Ожидаемое решение

В тесте `test_llm_fallback`:

- замокать sidecar/natal/transits;
- замокать или подготовить `NatalContextService`;
- проверять только fallback-поведение LLM, а не доступность sidecar.

Если production behavior реально зависит от sidecar, это нормально. Unit/integration test не должен ходить во внешний sidecar.

### Acceptance criteria

- `test_llm_fallback` не требует живого sidecar.
- Тест явно проверяет fallback text / fallback response / fallback status.
- При падении LLM endpoint возвращает ожидаемую fallback-структуру.
- При падении sidecar отдельный тест должен проверять sidecar error path, но не смешиваться с LLM fallback.

## 6. Work package C — `test_alembic_roundtrip`

### Проблема

Тест жёстко ожидает бинарник:

```text
.venv/bin/alembic
```

В CI/локальном окружении такого пути может не быть.

### Требование

Убрать hardcoded `.venv/bin/alembic`.

Допустимые варианты:

1. Использовать `sys.executable -m alembic`.
2. Использовать `shutil.which("alembic")` с понятной ошибкой, если alembic не установлен.
3. Добавить env var `ALEMBIC_BIN`, но fallback должен быть нормальным.

Рекомендуемый вариант:

```python
cmd = [sys.executable, "-m", "alembic", "..."]
```

### Acceptance criteria

- `test_alembic_roundtrip` проходит без `.venv/bin/alembic`.
- Тест работает в CI и локально.
- Если alembic не установлен, ошибка явно говорит, что отсутствует dependency, а не файл `.venv/bin/alembic`.

## 7. Work package D — TypeScript errors вне natal

### Проблема

`pnpm typecheck` падает на pre-existing TS errors в чат/лог/telegram/block-renderer модулях.

### Требование

Исправить типы, не отключая typecheck.

Порядок работы:

```bash
pnpm typecheck
```

Затем:

1. Сгруппировать ошибки по файлам.
2. Исправить минимально, без переписывания логики.
3. При необходимости добавить локальные типы/interface guards.

### Правила исправления

Разрешено:

- добавить недостающие discriminated union cases;
- поправить nullable/undefined handling;
- добавить type guards;
- уточнить типы action/reducer payload;
- поправить logger type signatures;
- заменить невалидный доступ к полям на безопасный.

Запрещено:

- массово ставить `as any`;
- отключать strict mode;
- добавлять `// @ts-ignore` без отдельного объяснения;
- ломать runtime behavior;
- менять API контракт без тестов.

### Acceptance criteria

- `pnpm typecheck` проходит.
- Все исправления локализованы в pre-existing модулях.
- Natal full report files не переписываются без необходимости.
- Если какая-то TS ошибка требует отдельного большого рефакторинга, вынести её в follow-up issue, но основной `typecheck` должен стать зелёным.

## 8. Required commands

После исправлений выполнить:

```bash
pnpm typecheck
pnpm test
cd apps/api && pytest
```

Дополнительно точечные проверки:

```bash
pnpm test -- __tests__/api/natal-report.test.ts
pnpm test -- __tests__/natal/natal-component-states.test.tsx
cd apps/api && pytest apps/api/tests/test_natal_golden_zhanna.py
```

## 9. Evidence report

Создать файл:

```text
docs/work/YYYY-MM-DD_pre_existing_gates_fix_evidence.md
```

В отчёте указать:

- исходные failing tests/typecheck errors;
- что исправлено;
- какие файлы изменены;
- какие команды запускались;
- итоговый статус;
- если что-то осталось skipped/flaky — почему и где follow-up.

## 10. Definition of Done

Готово, когда:

- `test_solarsage_client ×2` зелёные;
- `test_llm_fallback` зелёный и не зависит от живого sidecar;
- `test_alembic_roundtrip` не зависит от `.venv/bin/alembic`;
- `pnpm typecheck` зелёный;
- `pnpm test` зелёный или known flaky явно заскипан с причиной;
- `pytest` зелёный;
- evidence report добавлен в `docs/work`;
- PR/ветка не содержит unrelated refactor.

## 11. Reviewer checklist

Reviewer должен проверить:

- не скрыты ли ошибки через `any`, `ts-ignore`, массовый skip;
- не изменена ли natal business logic;
- sidecar schema drift исправлен в контракте, а не просто замолчан;
- fallback test проверяет именно LLM fallback;
- Alembic test portable;
- typecheck реально зелёный;
- evidence приложен.
