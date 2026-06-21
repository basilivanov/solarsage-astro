# packages/contracts

Единые контракты frontend ↔ backend. Канон в
`docs/05_API_contracts_и_TodayPayload.md`.

## Source of truth — Option B (W-1.1B)

В этом репозитории **Pydantic-схемы из `apps/api/app/schemas/*` являются
единственным источником правды для API-контрактов**. Pipeline:

```
apps/api/app/schemas/*.py   (Pydantic, BaseModel(extra="forbid", camelCase))
        |
        v  scripts/contracts/export_openapi.py
packages/contracts/openapi.json     (committed snapshot, deterministic)
        |
        v  npx openapi-typescript
packages/contracts/_generated.ts    (committed, banner-stamped, do not edit)
        |
        v  per-feature re-export shims
packages/contracts/{today,calendar,natal,access}.ts
```

`lib/contracts/forms/*.ts` (если/когда появится) хранит **только** zod-схемы
для пользовательских форм (валидация ввода до отправки на сервер). Никакие
ответы сервера на фронте zod'ом больше не валидируются — для них есть типы
из `packages/contracts/_generated.ts`.

## Файлы

- `openapi.json` — артефакт, генерируется (commit обязателен).
- `_generated.ts` — артефакт, генерируется (commit обязателен).
- `today.ts`, `calendar.ts`, `natal.ts`, `access.ts` — тонкие shims:
  re-export нужных типов из `_generated.ts` под стабильными именами.

## Регенерация

```bash
pnpm contracts:generate
```

Это эквивалентно `bash scripts/contracts/generate.sh`. Скрипт идемпотентен:
повторный запуск без изменений Pydantic-моделей даёт байт-в-байт тот же
результат. Переносимый guardrail запускает

```bash
pnpm contracts:check
```

— это та же генерация плюс `git diff --exit-code` по
`packages/contracts/openapi.json` и `packages/contracts/_generated.ts`.
Любой drift между Pydantic и закоммиченными артефактами роняет verifier/CI.
Пока v0 блокирует `.github/workflows/*`, этот gate вызывается через
`scripts/guardrails.sh`, а не через GitHub Actions workflow.

## Правила

1. В JSON только примитивы и ISO-строки. Никаких `Date`, `LucideIcon`,
   React-компонентов.
2. У всех payload'ов есть `meta.schemaVersion` и `meta.contractVersion`.
3. Любая ломающая правка контракта — повышение `contractVersion`,
   обновление `docs/05` **и** регенерация артефактов в том же PR.
4. На фронте использовать только импорт типов из `packages/contracts/*`.
   `apps/api/app/schemas/*` — единственное место, где можно менять
   shape контракта.
