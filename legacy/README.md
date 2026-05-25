# legacy/

Замороженный снимок старого SolarSage-фронта (до GRACE bootstrap baseline).

## Статус

- **Вне GRACE-периметра.** `grace/frontend.paths` whitelist'ит только
  `app/(grace)/**`, `components/grace/**`, `lib/grace/**`, `lib/api/**`,
  `packages/contracts/index.ts`. Файлы в `legacy/` сюда не входят, поэтому
  marker gate (`scripts/grace/check-markers.sh`) их игнорирует.
- **Вне Next.js routing.** Каталог не находится под `app/`, поэтому Next.js
  не подбирает роуты и компоненты отсюда. Старый `legacy/frontend/app/`
  существует только как исходник для миграции.
- **Вне ESLint и tsc.** `eslint.config.mjs` ignores содержит `legacy/**`,
  `tsconfig.json` exclude содержит `legacy`. Никаких ошибок типов или линта
  отсюда не приходит.
- **Вне drift-gate W-1.1B.** Drift gate сравнивает только
  `packages/contracts/openapi.json` и `packages/contracts/_generated.ts`.

## Назначение

Источник для пакетов W-2.1..W-2.8: каждый пакет переносит часть `legacy/frontend/`
в GRACE-периметр (`app/(grace)/**`, `components/grace/**`, `lib/grace/**`,
`lib/api/**`), расставляет маркеры (AI_HEADER, MODULE_CONTRACT, MODULE_MAP,
BLOCK pairs, FUNCTION_CONTRACT) и обновляет `grace/frontend.paths`.

## Что внутри

`legacy/frontend/` содержит снапшот UI-папок старого проекта:

- `app/` — Next.js маршруты (`(app)/calendar`, `chat`, `day/[date]`, `profile`,
  `readings/natal/[section]`, `layout.tsx`, и т.д.)
- `components/` — feature-компоненты (calendar, chat, onboarding, profile,
  readings/natal/widgets, paywall, telegram-init, app-shell, shared)
- `lib/` — клиентская логика, API-клиенты, fixtures, mocks, reducers,
  pure-functions, контракты (`lib/contracts/*` — конфликтуют с
  `packages/contracts`, должны быть смержены в W-2.1)
- `hooks/` — React-хуки
- `styles/` — глобальные стили
- `e2e/`, `playwright.config.ts`, `vitest.config.ts` — тесты, сейчас не
  запускаются (тестовый gate появится в W-2.8)
- `package.json` — референс зависимостей старого фронта (актуальный
  package.json в корне проекта; `recharts`, `vitest`, `playwright`,
  `@hookform/resolvers` нужно будет добавлять при миграции)

## Правила

- В `legacy/` ничего не редактируется. Если нужна правка — переноси файл в
  GRACE-периметр в рамках соответствующего пакета.
- Удаление подкаталогов `legacy/frontend/<feature>/` происходит в финале
  каждого пакета W-2.x (после успешного переноса и зелёного bootstrap.sh).
