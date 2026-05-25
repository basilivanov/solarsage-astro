---
id: doc-15-ci-without-github-actions
status: active
wave: none
last_review: 2026-05-25
---
# Guardrails и CI при синхронизации через v0

## Решение

Пока v0 синхронизирует изменения в репозиторий, в проекте намеренно нет
`.github/workflows/`: v0 блокирует push в репозиторий, где присутствуют
GitHub Actions workflow-файлы.

Это ограничение транспортного канала, а не отказ от проверок качества.
Источник правды для запуска проверок находится в
`scripts/guardrails.sh`. Любой runtime — локальная машина, Vercel,
Prefect/GRACE verifier или будущий CI — обязан вызывать этот же entrypoint,
а не дублировать набор команд.

## Команды

| Команда | Что реально проверяет | Где запускать |
| --- | --- | --- |
| `pnpm guardrails:docs` | front-matter документов и синхронность `docs/MANIFEST.md` | v0, локально, Prefect |
| `pnpm guardrails:secrets` | базовый scan случайно закоммиченных токенов/секретов | Vercel, Prefect, локально |
| `pnpm guardrails:contracts` | Pydantic → OpenAPI → TypeScript и отсутствие contract drift | Prefect/verifier, локально |
| `pnpm guardrails:backend` | `grace_lint` self-tests, `ruff`, `mypy`, Alembic round-trip, `pytest` | Prefect/verifier, локально |
| `pnpm guardrails:backend-grace` | strict backend marker lint по `apps/api/app` | canon-sync/refactor waves |
| `pnpm guardrails:frontend` | `eslint`, `tsc`, GRACE markers и negative tests | Vercel, Prefect, локально |
| `pnpm guardrails:vercel` | docs + secrets + frontend | Vercel Build Command перед `pnpm build` |
| `pnpm guardrails:full` | docs + secrets + contracts + backend + frontend | Prefect verifier и pre-merge verification |
| `pnpm guardrails:strict` | `full` + strict backend marker lint | после завершения backend canon-sync |

У команд нет успешных заглушек: если необходимый dependency не установлен
или реальная проверка падает, команда завершается с ненулевым кодом.

## Разделение ответственности

### Vercel

Vercel отвечает за frontend preview/deploy и не обязан устанавливать Python
зависимости backend. Для проекта устанавливается Build Command:

```bash
pnpm guardrails:vercel && pnpm build
```

Так Vercel блокирует визуальный/frontend build при ошибках документации,
случайных секретах, TypeScript/ESLint или GRACE frontend-маркерах, но не
пытается исполнять backend-контур.

### Prefect / GRACE verifier

Verifier для пакета или финального wave-gate запускает:

```bash
pnpm guardrails:full
```

Именно здесь исполняются backend-тесты, миграции и contract drift gate.
Stdout/stderr команды и `git diff --exit-code` должны сохраняться как
verification evidence пакета/волны.

Для волн, которые прямо меняют backend GRACE-разметку или объявляют
backend active slice формально синхронизированным с каноном, verifier
дополнительно запускает:

```bash
pnpm guardrails:backend-grace
```

`backend-grace` намеренно не входит в Vercel и в базовый `full`: текущий
импортированный baseline ещё содержит legacy/недооформленные backend-модули.
Иначе guardrails превращаются из управляемого гейта в постоянный глобальный
блокер unrelated изменений. После завершения canon-sync волны можно поднять
обязательный профиль до `pnpm guardrails:strict`.

### Локальная проверка

Перед проверкой всего проекта:

```bash
pnpm install
cd apps/api && make install
cd ../..
pnpm guardrails:full
```

Для узкой правки запускается только релевантный профиль, например
`pnpm guardrails:frontend`, `pnpm guardrails:backend` либо
`pnpm guardrails:backend-grace`.

## Почему workflow сейчас не возвращаем

Нельзя после первого push v0 просто вручную добавить
`.github/workflows/grace-gate.yml` и считать вопрос закрытым: следующий
sync из v0 может снова заблокироваться на том же ограничении. GitHub Actions
возвращается только после одного из событий:

1. v0 больше не является write-source репозитория;
2. подтверждено, что текущий режим v0 допускает существующий workflow;
3. CI запускается из отдельного служебного репозитория.

Будущий workflow не должен содержать собственную логику гейтов. Его задача —
установить зависимости и выполнить `pnpm guardrails:full`.

## Ограничение secret scan

`guardrails:secrets` — быстрый baseline-gate против случайного попадания
наиболее типичных токенов в tracked files. Он не заменяет специализированный
scanner с историей git. Перед production-релизом должен быть добавлен
полноценный `gitleaks`/эквивалентный gate в runtime, который не конфликтует
с v0.
