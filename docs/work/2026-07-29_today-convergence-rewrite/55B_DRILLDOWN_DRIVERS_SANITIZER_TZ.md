# 55B — Drilldown: реальные драйверы событий + санитайзер narrative + Transit_/Natal_ стриппинг

Ты — coder. Skill coder-loop использовать НЕЛЬЗЯ. Ничего не коммить — коммит делает ревьюер.

Контекст: приёмка владельца. Drilldown «Почему сошлось» сейчас показывает механические заглушки («Событие · Работа», «Это событие несёт смысл «напряжение» для сферы «Работа»»), потому что wire-контракт события не несёт человеческого описания драйвера. Норматив: `docs/work/2026-07-29_today-convergence-rewrite/03_W7_FRONTEND_DESIGN_TZ.md` §7 («доказательная цепочка — нумерованные драйверы с временами»), §10 (заглушки запрещены). Живой payload `GET /api/day/snapshots/{id}/spheres/work`: у событий только `kind/sphere/polarity/time/sourceIds:["MOON"]` — описания нет.

## 1. Backend: `title` у drilldown-событий (контракт + сервис)

- В OpenAPI/contract `TodayConvergenceEvent` добавить поле `title: string` (человеческое локализованное описание драйвера, напр. «Луна в напряжении к твоему Сатурну», «Марс напротив твоего Нептуна»). Обновить сгенерированные контракты через существующий codegen (`pnpm contracts:check` должен проходить после регенерации).
- Источник title — нормализованные сигналы/юниты, из которых собрано событие (`sourceIds` → сигналы в snapshot). Названия планет по-русски, аспекты человеческим языком. Сырые технические имена (`Transit_`, `Natal_`, `Planet`, `M, Mars`) в title ЗАПРЕЩЕНЫ — стриппинг префиксов и локализация на этапе сборки payload.
- Drilldown-builder (`apps/api/app/services/…` — найти по `today_sphere_drilldown`) заполняет `title` для каждого события цепочки; если для события нельзя построить честный title — не выдумывать, отдавать `title: null` (сделать поле nullable) и фронт честно покажет меньше, а не заглушку.
- Заодно исправить известный баг #1 из AGENTS.md: `today_service.py` (~строка 209, построение `TopFlag`) использует сырое `signal.planet` с префиксом `Transit_` — стриппить префикс и локализовать там же. Проверить, что в JSON дня больше нет `Transit_`/`Natal_` в любом человекочитаемом поле.

## 2. Санитайзер narrative-текстов

Владелец видел в тексте страницы сферы: «благодаря не влевой аспекту M, Mars, M, Moon», «Natal, Planet, Moon» — LLM протащил сырые имена сигналов в narrative.

- Найти генераторы narrative (today narrative + sphere natal narrative, `apps/api/app/services/`).
- Добавить deterministic post-processing/валидацию: паттерны `Transit_`, `Natal_`, `\bPlanet\b`, перечисления вида `M, <Planet>` → текст не публикуется как есть; либо чистится, либо claim помечается неготовым (honest pending), но сырьё пользователю не показывается. Усилить промпт (уже есть просьба не использовать Transit_ — недостаточно).
- Покрыть тестом: narrative с `Transit_Mars`/`Natal_Moon` не уходит в API-ответ.

## 3. Frontend: цепочка drilldown без заглушек (только `components/today-convergence/sphere-drilldown.tsx` + его тесты)

- В карточке события: заголовок — `event.title` (когда есть), под ним время + polarity-пилюля (tone-классы из `today-formatters.tsx`, как на экране дня). Удалить тексты «Событие · <Сфера>» как заголовок и «Это событие несёт смысл «…» для сферы «…»» полностью.
- Блок «Контекст сферы»: удалить фразу «Цепочка относится к опубликованному snapshot и не заменяет исходные события расчёта». Если реального контекста нет — блок не рендерить вовсе (НЕ заменять другой заглушкой). «Основание связи» (convergence) оставить как есть.
- Сохранить существующие data-testid; `drilldown-event-time-*`/`drilldown-event-polarity-*` сохранить, добавить `drilldown-event-title-{id}`.
- Обновить `__tests__/components/today-convergence/today-screen.test.tsx` / drilldown-тесты и mock-фикстуры (`__tests__/fixtures/today_convergence_v2*`, e2e mock fixtures если события там) — добавить `title` в фикстуры.

## Verification (обязательно, показать вывод)

- `cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q -m "not integration and not benchmark" 2>&1 | tail -4`
- `npx vitest run 2>&1 | tail -4`
- `npx tsc --noEmit`
- `PYTHON=/opt/solarsage-astro/apps/api/.venv/bin/python pnpm contracts:check`
- `python3 scripts/check_logging_guardrails.py | tail -2`
- `git diff --check`

Backend GRACE-маркеры обновить. Ревизии alembic (если вдруг миграция) ≤32 символа.
