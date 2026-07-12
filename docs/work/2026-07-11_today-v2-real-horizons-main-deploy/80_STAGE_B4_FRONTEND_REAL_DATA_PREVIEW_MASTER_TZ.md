# Stage B4 master ТЗ — backend-owned frontend and real preview on 3003

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Prerequisite: accepted, pushed and full-green Stage B3 real API payload
Authority: `00`, `50`, `51`, accepted B1 frontend boundary and current product discussion
Статус: **FRONTEND EXECUTION PLAN — RUN ONLY ONE AUTHORIZED WAVE AT A TIME**

## 1. Outcome of Stage B4

The normal local URL:

~~~text
http://127.0.0.1:3003/day/<accepted-date>?why=1
~~~

must authenticate through the real dev-auth flow, request the real API on
port `8000`, validate the generated wire contract, and render backend-owned
three-horizon content. It must not use `fixture=...`, Playwright interception,
mock server `18092`, `lib/mocks`, or frontend astrology inference.

The fixture URL remains available only as a development/test visual reference:

~~~text
/day/2026-07-08?fixture=three-horizon-timing&why=1
~~~

It is never the acceptance URL and is impossible in production mode.

## 2. Closed product presentation

The 12 spheres stay visible as the fast navigator. The Why block explains one
personal story in three speeds.

Information order:

~~~text
human meaning
-> exact validity window and current state
-> likely life manifestations
-> confirmed strength / confirmed risk when available
-> what to do / what to postpone
-> clickable sphere links
-> explicitly opened calculation explanation
~~~

Technical words such as `профекция`, `фирдар`, `транзит`, `орб`, `return`,
`аппликация` do not appear in the main card copy. They are allowed only inside
the accessible `Как это рассчитано` disclosure, where every term is explained
in plain Russian.

### Tone mapping

Frontend maps the closed backend enum only; it never infers tone from text:

~~~text
supportive -> Поддерживает
neutral    -> Ровный фон
tense      -> Требует внимания
mixed      -> Смешанный сигнал
~~~

Color is secondary. The visible text and `data-status` communicate semantics.

### Horizon framing

Use backend eyebrow/title/body. The surrounding structural labels are:

~~~text
long   -> Долгий цикл
medium -> Текущий период
fast   -> Быстрый триггер
~~~

Do not reintroduce the constant legacy sentence about “three random facts” for
backend horizons.

## 3. Wave decomposition

### B4.W1 — generated-wire steady-state consumer

Goal: make the real version-3 payload behavior explicit and testable.

- `today.v2.1` / frontend `3` uses only `v2.horizons` for the three cards.
- If a version-3 payload has `horizons=null`, render a stable honest unavailable
  state; do not run `selectWhyTimeHorizons`.
- Legacy selector fallback is allowed only for old accepted `today.v2` /
  frontend `2` cached payloads during migration.
- The adapter preserves backend order/copy/provenance shape and performs no
  selection, date-phase calculation or advice generation.
- Generated OpenAPI TypeScript/Zod remain the raw wire source.
- Production code does not import mock/demo data.

Required DOM contract:

~~~text
data-testid="why-expanded"
data-testid="why-horizons" data-source="backend-horizons"
data-testid="why-horizons-unavailable" data-state="empty"
data-testid="why-horizon" data-horizon="long|medium|fast"
data-status="supportive|neutral|tense|mixed"
data-timing-state="..."
~~~

### B4.W2 — final human-first UX and 12-sphere navigation

Goal: complete the design already approved in fixture review using real
backend-owned fields.

Each card shows:

- human title and expanded summary;
- dates/window, peak when present and current state;
- “Где это вероятнее проявится” manifestations;
- “На что можно опереться” only when strength exists;
- “Что может мешать” only when risk exists;
- “Что сделать” in backend order;
- “Чего лучше не делать” in backend order;
- validity label;
- likely-sphere chips;
- accessible technical disclosure.

Sphere chip behavior:

1. calls the existing TodayScreen sphere-selection boundary;
2. scrolls the matching row in the 12-sphere navigator into view;
3. expands/focuses it without changing its verdict;
4. preserves a stable `data-testid` and visible focus state;
5. does nothing fabricated if the backend sphere has no navigator row.

Accessibility:

- disclosure `aria-expanded`/`aria-controls` exact;
- technical content has `role=region` and accessible label;
- icon-only controls have `aria-label`;
- status is never color-only;
- keyboard interaction works for sphere chips and disclosures;
- 390px mobile, desktop and dark theme have no clipping/overflow.

### B4.W3 — one-command real preview and no-interception E2E

Goal: make preview usable by user `astro` without manual environment rituals.

Add a dedicated command:

~~~text
pnpm preview:v2:real
~~~

It must:

- run as the current non-root user;
- fail clearly if `3003` is occupied by an unrelated process;
- use a dedicated Next dev dist directory, not `.next-prod`;
- bind `127.0.0.1:3003` or `0.0.0.0:3003` as documented;
- use the existing Next `/api/* -> 127.0.0.1:8000` rewrite;
- never start uvicorn, sidecar or a mock API;
- print the real acceptance URL;
- handle SIGINT/SIGTERM and leave no orphan process.

Add a dedicated Playwright spec with **zero `page.route` calls**. It must:

- start with an empty browser context;
- authenticate through `/api/auth/dev` naturally;
- observe the real `/api/day/<date>` response;
- assert versions `today.v2.1` / `3` / `10`;
- assert three backend horizon IDs in order;
- assert `data-source=backend-horizons`;
- open all three technical disclosures;
- click at least one sphere chip and prove the navigator target behavior;
- assert no request to `/api/dev-fixtures/*` or port `18092`;
- capture mobile and desktop screenshots from the real API.

## 4. B4 acceptance matrix

~~~text
generated contract tests
frontend unit/component tests
Vitest full suite
typecheck
production guardrail
frontend/contract guardrails
Next production candidate build in isolated dist
real preview no-interception Playwright mobile + desktop
manual browser review URL on 3003
~~~

Visual approval is necessary but not sufficient: network evidence must prove the
page came from real backend data.

## 5. After B4

B5 closes any remaining test/runtime debt, runs the full repository and real
Telegram-HMAC release-candidate matrix, and produces
`READY_STAGE_B_FOR_MAIN_RELEASE`.

Only then may `90_MAIN_RELEASE_DEPLOY_TZ.md` execute merge, push main, shared
wheel install, atomic frontend build swap, canonical systemd restart and
production proof.

## 6. Global forbidden paths and operations

Always preserve:

~~~text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
~~~

Before final release do not switch to `main`, restart systemd, edit nginx/env or
touch `.next-prod`.
