# Stage B1 — architect acceptance and commit/push

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Pre-commit HEAD: `f0d8bef19ec4f0806039cf44a173a22bb4f60a1c`

## 1. Architect verdict

Stage B1 принят.

Подтверждено независимо архитектором:

```text
backend focused: 155 passed
contract sync focused: 110 passed
contract Vitest: 134 passed
compatibility: additive, breaking=0, override=false
generated hashes: identical across regeneration
fixture normalization: PASS
TypeScript typecheck: PASS
frontend full: 96 files, 998 passed
Playwright mobile fixture: 1 passed
preview URL: HTTP 200 on 3003
sidecar full: 201 passed
API full: identical known baseline only — 6 failed, 888 passed, 5 skipped
compileall: PASS
git diff --check: PASS
index before acceptance: EMPTY
production horizon population: NONE
```
Архитектурные corrections закрыты:

- provenance sphere subset проверяется для manifestations, strength, risk,
  do/avoid actions;
- untimed technique evidence не получает чужую точную timing card;
- raw human input скрыт из строк validation errors;
- прежние 11 component scenarios восстановлены, 11 B1 scenarios добавлены;
- tone различается текстом, enum-owned цветом и `data-status`;
- fast human dates соответствуют Europe/Moscow;
- GRACE contracts исправлены;
- canonical JSON нормализован.

## 2. Commit scope — exact paths

Добавить в index только следующие paths:

```text
apps/api/app/schemas/today_horizons.py
apps/api/app/schemas/today.py
apps/api/app/schemas/__init__.py
apps/api/tests/test_today_horizons_contract.py
apps/api/tests/test_contract_registry.py

packages/contracts/openapi.json
packages/contracts/_generated.ts
packages/contracts/_generated.zod.ts
packages/contracts/index.ts
packages/contracts/runtime.ts
lib/contracts/today.ts

components/today/today-screen.tsx
components/today/why-expanded.tsx
components/today/why-time-horizon-card.tsx
components/today/horizon-actions.tsx
components/today/horizon-technique-disclosure.tsx

e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json
__tests__/contracts/generated-runtime.test.ts
__tests__/contracts/today-fixture-roundtrip.test.ts
__tests__/components/TodayScreen.v2-downstream.test.tsx
__tests__/lib/presentation/today-v2.test.ts
e2e/dev-timing-fixture.spec.ts
e2e/mock-visual/day-v2.spec.ts

docs/work/2026-07-11_today-v2-real-horizons-main-deploy/51_STAGE_B_AND_MAIN_RELEASE_WAVE_PLAN.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/52_STAGE_B1_HORIZON_CONTRACT_CONSUMER_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/53_STAGE_B1_ARCH_REVIEW_CORRECTIONS_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/54_STAGE_B1_FIXTURE_NORMALIZATION_CORRECTION_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/55_STAGE_B1_ACCEPTANCE_COMMIT_PUSH_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/b1/01-backend-contract-horizons-mobile.png
```

Не добавлять:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Не использовать `git add -A`, `git add .` или wildcard, который может захватить
unrelated paths.

## 3. Pre-commit verification

После exact `git add -- <paths...>`:

```bash
git diff --cached --name-only
git diff --cached --check
git status --short
```

Сверить staged list буквально с section 2. Unrelated paths должны остаться
только untracked и unstaged.

## 4. Commit

Сделать один commit:

```text
feat(today): add grounded three-horizon contract
```

После commit:

```bash
git log -1 --format='%H%n%s'
git status --short --branch
```

## 5. Post-commit contract gate

Теперь generated files находятся в HEAD, поэтому обязательный gate должен
стать полностью green:

```bash
pnpm contracts:check
pnpm contracts:fixture:check
git diff --check
```

`pnpm contracts:check` должен завершиться `all checks passed successfully`, а
не только partial/substantive pass. Если он красный — не push, исправления не
делать самостоятельно вне scope, вернуть blocker.

## 6. Push

Только после green post-commit gates:

```bash
git push origin preview/solarsage-v2-human-first-navigator-ux
```

Без force.

Проверить:

```bash
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git status --short --branch
```

Local и origin SHA должны совпасть. Worktree после commit/push может содержать
только перечисленные unrelated untracked paths.

Не начинать B2. Не менять preview processes. Не запускать субагентов.

## 7. Callback

```text
PUSHED_STAGE_B1_HORIZON_CONTRACT
branch: preview/solarsage-v2-human-first-navigator-ux
commit: <sha>
subject: feat(today): add grounded three-horizon contract
staged_scope: EXACT
contracts_check_after_commit: PASS
fixture_check_after_commit: PASS
push: PASS
origin_feature: <same sha>
unrelated_untracked_only: PASS
preview_3003: LEFT_RUNNING
```
