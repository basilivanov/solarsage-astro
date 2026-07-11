# MASTER ТЗ — Today V2: реальные горизонты, действия, main и production deploy

Дата: 2026-07-11
Репозиторий: `/opt/solarsage-astro`
Рабочая ветка: `preview/solarsage-v2-human-first-navigator-ux`
Baseline HEAD на старте программы: `04bebb331575909c70c36412449101ccba999a79`
Локальный `main`: `c9bc36bd9a947566eddb1ffcf5617967c7412676`

## 0.1 Канонический архитектурный amendment после S2.W1

После принятия решения об упрощении contract evolution программа получает две
обязательные последовательные стадии перед final main release:

```text
40_STAGE_A_SHARED_PYTHON_CONTRACT_PLATFORM_TZ.md
50_STAGE_B_REAL_HORIZONS_ACTIONS_FRONTEND_TZ.md
```

Порядок:

```text
S2.W1 real timing
  -> Stage A shared Python contracts
  -> Stage B real horizons/actions/frontend
  -> 90_MAIN_RELEASE_DEPLOY_TZ.md
```

Эти файлы имеют приоритет над прежними архитектурными формулировками Stage 1/2
в части source-of-truth и public horizon model. Уже выполненные S1 codegen,
runtime Zod, fixture consolidation и preview checkpoints остаются действующими
и не откатываются.

Новое source-of-truth rule:

```text
sidecar -> API calculation evidence:
  packages/py-contracts shared semantic field definitions
  + thin boundary-specific wrappers/casing

API -> frontend public read model:
  apps/api Pydantic
  -> OpenAPI
  -> generated TypeScript + generated Zod
```

Не создавать один универсальный DTO, смешивающий calculation, human guidance и
frontend presentation.

## 1. Итог программы

Задача считается завершённой только когда одновременно доказано:

1. Три временных горизонта приходят из реального `/api/day/<date>`, а не
   создаются frontend fixture или frontend astrology inference.
2. Sidecar/API передают реальные сроки:
   - `activeFrom`;
   - `exactAt`;
   - `activeUntil`;
   - текущую фазу/стадию.
3. Backend формирует structured personal horizons:
   - динамическую вводную личного сюжета;
   - human-first title/body;
   - вероятные сферы проявления;
   - подтверждённую личную сильную сторону, если такая есть;
   - подтверждённый риск/паттерн, если такой есть;
   - конкретные действия;
   - действия, которые лучше отложить;
   - точный срок актуальности;
   - ссылки на evidence IDs для каждого утверждения.
4. Frontend только рендерит backend-owned structured block и не вычисляет
   астрологию или персональные утверждения.
5. Навигатор 12 сфер сохраняет видимые статусы:
   `Поддержка / Ровно / Внимание / Отложить`.
6. Обычный production URL работает через Telegram HMAC и реальный API без
   `fixture=...`.
7. Mock/dev fixture остаётся только test/review harness и не является источником
   production данных.
8. Все contract/backend/frontend/unit/integration/real-E2E/build gates проходят.
9. Изменения слиты в `main`, `origin/main` обновлён.
10. Sidecar, API и frontend задеплоены через канонические systemd services.
11. Production smoke подтверждает новый payload и новый UI через nginx/Telegram
    auth.

## 2. Роли и протокол

- Архитектор и reviewer: основной Codex-сеанс.
- Кодер: tmux target `astro:0.0`.
- Сабагенты не использовать.
- Все полные задания хранятся в `docs/work`; в tmux передаётся только путь и
  короткая команда.
- Если кодер не закончил волну, следующий контроль выполняется через 3 минуты.
- Кодер не принимает архитектурные решения, не описанные в ТЗ. При настоящем
  противоречии останавливается с `BLOCKED_<WAVE>` и точными файлами/фактами.
- До architect review конкретной волны кодер не делает её commit/push.
- После `ACCEPTED_<WAVE>` архитектор отдельно разрешает scoped commit и push.
- Merge в `main` и production deploy разрешены только в финальной release wave.

## 3. Текущее подтверждённое состояние

### Уже реализовано в preview worktree

- human-first навигатор 12 сфер;
- видимые verdict labels;
- frontend presentation трёх горизонтов;
- timing UI;
- dev-only fixture URL на `3003`;
- browser screenshots и focused tests;
- Suspense-safe dev fixture shell;
- production build ранее проходил после Suspense fix.

### Чего пока нет в production pipeline

- API/sidecar `activeFrom` и `activeUntil`;
- реально рассчитанный `exactAt` для transit activations;
- backend-owned `v2.horizons`;
- backend-owned dynamic horizon intro;
- structured personal actions/avoid actions;
- typed personal fact pack и claim provenance;
- real API frontend rendering этих новых blocks;
- production rollout.

### Contract audit

Уже есть правильный фундамент:

```text
Pydantic schemas
  -> scripts/contracts/export_openapi.py
  -> packages/contracts/openapi.json
  -> openapi-typescript
  -> packages/contracts/_generated.ts
```

Недостающие части:

- runtime Zod schemas всё ещё описываются вручную;
- `lib/contracts/today.ts` повторяет wire V2 shapes;
- TS и JSON visual fixtures содержат дублированные payload copies;
- contract drift gate не проверяет runtime validator artifact.

## 4. Целевая архитектура

```text
SolarSage / Swiss Ephemeris
  -> ActivationEvidence with real timing
  -> API ActivationLayer validation
  -> ScoringV2 + ranked spheres
  -> PersonalFactPackService
  -> HorizonGuidanceService
       deterministic safe fallback
       optional constrained LLM wording
       strict claim validator
  -> TodayV2Block.horizonIntro + horizons
  -> generated OpenAPI types + generated runtime Zod
  -> frontend adapter (shape only)
  -> TodayScreen / WhyExpanded / horizon cards
```

### Source-of-truth rule

Pydantic models in `apps/api/app/schemas/*` are the only wire-contract source.

Generated artifacts:

```text
packages/contracts/openapi.json
packages/contracts/_generated.ts
packages/contracts/_generated.zod.ts
```

Frontend manual schemas may describe only UI-adapted structures. They must not
redeclare raw API wire shapes.

### Personalization rule

Backend may use only confirmed facts:

- active activation evidence;
- score contributions and ranked spheres;
- deterministic natal context facts;
- versioned canon mappings;
- profile facts explicitly stored by the user.

Forbidden assumptions:

- profession or employer;
- relationship status;
- debts, income, purchases;
- medical diagnosis;
- an event that has allegedly happened;
- another person's intentions.

Unknown real-life context uses conditional wording:

```text
Если сейчас вы обсуждаете новую роль или объём ответственности…
```

### Evidence rule

Every human claim/action must be traceable:

- `evidenceIds` references `v2.activationEvidence[].id`;
- `sphereKeys` references known sphere keys;
- natal claims reference internal typed natal fact IDs;
- profile claims reference allowlisted profile fact kinds;
- no empty provenance for a personal strength/risk/action.

## 5. Две стадии и волны

## Стадия 1 — Contract foundation

Полное ТЗ:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/10_STAGE_1_CONTRACT_FOUNDATION_TZ.md
```

### S1.W0 — Preserve accepted preview baseline

- привести текущий dirty diff к reviewable allowlist;
- добавить недостающие GRACE contracts новым code files;
- доказать текущие frontend/dev-fixture gates;
- scoped commit/push accepted preview baseline.

### S1.W1 — Generated runtime schemas

- pinned OpenAPI → Zod generation;
- schemas-only artifact, без Zodios runtime client;
- runtime barrel;
- idempotent generation and drift gate.

### S1.W2 — Wire/runtime consumer migration

- raw TodayPayload validation generated schema;
- убрать ручное дублирование raw V2 wire contract;
- UI contracts оставить адаптированными;
- typed adapter boundary.

### S1.W3 — One-source fixtures and contract proof

- Pydantic-generated canonical fixture;
- один JSON payload вместо ручной TS+JSON копии;
- backend/frontend round-trip tests;
- contract documentation and CI gate.

## Стадия 2 — Real timing, horizons, actions and rollout

Полное ТЗ:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/20_STAGE_2_REAL_HORIZONS_TZ.md
```

### S2.W1 — Sidecar timing truth

- `active_from/exact_at/active_until` in sidecar and API schemas;
- real transit exact/window solver;
- real period boundaries;
- timing parity and accuracy tests;
- calculation/version bumps.

### S2.W2 — Horizon wire contract and deterministic selection

- `horizonIntro` and structured `horizons` Pydantic schemas;
- exactly ordered `long/medium/fast` when evidence allows;
- coherent-story selection from real evidence;
- no frontend selection for new payloads.

### S2.W3 — Personal fact pack and safe guidance

- typed fact pack;
- natal/support/risk facts only from allowlisted canon;
- ranked sphere linkage;
- deterministic actions and avoid actions;
- constrained LLM refinement as optional layer;
- strict claim validator and fallback.

### S2.W4 — Real frontend rendering

- dynamic intro from API;
- real timing from API;
- horizon-specific action UI;
- visible likely-sphere links;
- legacy payload fallback during one migration version;
- no production dependency on fixture.

### S2.W5 — Integration, cache and real E2E

- version/cache invalidation;
- real sidecar → API → frontend proof;
- Telegram HMAC real E2E without route interception;
- contract/audit artifacts;
- production build.

### S2.W6 — Main integration and production deployment

Release ТЗ:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/90_MAIN_RELEASE_DEPLOY_TZ.md
```

- final branch audit;
- merge to `main`;
- push `origin/main`;
- build/restart in safe dependency order;
- production smoke and rollback proof.

## 6. Version policy

Expected final version family, unless implementation evidence requires a higher
compatible value:

```text
CALCULATION_VERSION          ss-calc-1.2.0
ACTIVATION_LAYER_VERSION     al-1.1
TODAY_V2_PAYLOAD_VERSION     today.v2.1
V2_FRONTEND_PAYLOAD_VERSION  3
TODAY_CONTENT_VERSION        10
LLM prompt version           3 (only if horizon LLM method ships)
```

Scoring formula is not changed, therefore:

```text
SCORING_V2_VERSION remains ss-scoring-2.0
```

All cache read/write identity tests must be updated together. Version bumps must
not be scattered as string literals.

## 7. Rollout compatibility

Deployment order:

1. additive sidecar fields;
2. API schema/service and new optional horizon block;
3. frontend consuming the new block;
4. enable final V2 flags only after smoke proof.

During feature-branch development:

- new `horizons` is optional on the wire;
- frontend can fall back to the accepted presentation selector for cached old
  payloads;
- final cache/version bump guarantees fresh production payloads;
- fallback must be structurally marked and must not become the final steady
  production source.

## 8. Global non-functional requirements

- No raw Telegram initData, tokens, cookies or personal birth data in logs.
- New structured logs use registered event names and exact slice/module/block.
- Backend failures follow current V2 enabled/fail-loud policy.
- Optional LLM failure never removes deterministic safe guidance.
- Sidecar timing must be deterministic for identical inputs.
- No network/API calls from frontend fixtures in production.
- UI remains usable at 390px and in dark theme.
- Public DOM/test contracts follow repository AGENTS.md.
- New code files and substantial edits preserve GRACE headers/maps/contracts.

## 9. Global verification matrix

Minimum final gates:

```bash
pnpm contracts:generate
pnpm contracts:check
npx vitest run
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
cd apps/solarsage && python -m pytest tests/ -q
NEXT_DIST_DIR=.next-release-proof pnpm build
E2E_BASE_URL=http://127.0.0.1:3003 npx playwright test
E2E_BASE_URL=https://<production-host> npx playwright test <real-e2e-spec>
git diff HEAD --check
```

Targeted commands do not replace full gates in release wave.

## 10. Definition of done evidence

Final acceptance report must contain:

- main commit SHA and origin/main SHA equality;
- deployed sidecar/API/frontend commit identity;
- exact systemd active states;
- production build result;
- full test counts;
- real API JSON excerpt proving `horizonIntro`, three `horizons`, timing and
  action provenance;
- browser screenshot from real API without fixture query;
- network trace proving no route interception/mock endpoint;
- cache version identity;
- production health URLs/statuses;
- rollback commit/unit commands.

Until all of this exists, the program is not complete.
