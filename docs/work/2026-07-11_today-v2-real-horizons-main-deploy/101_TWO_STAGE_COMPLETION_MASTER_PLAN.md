# Two-stage completion master — safe real preview, main merge and production deploy

Дата: 2026-07-13
Репозиторий: `/opt/solarsage-astro`
Feature branch: `preview/solarsage-v2-human-first-navigator-ux`
Accepted base SHA: `ae62ad8ced1865cef2b2b1b3a0382d2e06065ce0`
Authority: user objective, repository `AGENTS.md`, documents `00`, `50`, `51`, `75`, `80`, `90`, `97`–`100`
Статус: **MASTER EXECUTION PLAN — ONE AUTHORIZED WAVE AT A TIME**

## 1. Final objective

Программа завершена только когда одновременно доказано:

1. обычный local review URL на `3003` получает real backend-owned
   `today.v2.1 / frontend 3 / content 10` через canonical API `8000`;
2. local preview не включает V2 для обычных Telegram/public пользователей до
   release approval;
3. три backend horizons `long / medium / fast` отображаются human-first UI;
4. 12-sphere navigator, technical disclosures, timing/actions and semantic
   statuses проходят strict desktop/mobile no-interception E2E;
5. fixture/mock path не участвует в acceptance;
6. feature branch full-green, clean, pushed;
7. feature branch merged в `main`, `origin/main` equal;
8. shared Python/runtime dependencies установлены из одного accepted main SHA;
9. canonical sidecar/API/frontend systemd services задеплоены в safe order;
10. production flags enable real V2 globally only during release wave;
11. production Telegram HMAC smoke и real browser UI proof проходят;
12. rollback artifacts/commands/SHA сохранены;
13. ни secrets, raw cookies, initData, birth/profile data или raw activation IDs
    не попадают в logs/artifacts/callback.

Локальный preview, commit feature branch или зелёный narrow test не являются
заменой этой конечной цели.

## 2. Why two stages

Current canonical API process on `8000`:

~~~text
started:                  2026-07-08
current repo commits:     2026-07-12+
selected identity:        today.v1 / frontend 1 / content 5
required preview identity today.v2.1 / frontend 3 / content 10
~~~

B3 real proof used in-process ASGI with process-local V2 settings. It proved
backend correctness but did not converge canonical HTTP API. Globally enabling
V2 now would expose an unapproved identity to ordinary users and possibly an
older production frontend.

Therefore:

~~~text
Stage 1 — isolated local dev V2 selection + canonical API convergence
Stage 2 — strict preview acceptance + release hardening + main deploy
~~~

## 3. Global roles and protocol

- Architect/reviewer: root Codex session.
- Coder: interactive `tmux astro:0.0` only.
- No subagents/delegation.
- Detailed tasks live only in `docs/work`; tmux receives path + short command.
- If coder is still running, next monitor only after full 3 minutes.
- Coder never commits/pushes before separate architect acceptance document.
- Main/systemd/env state changes require a dedicated runtime/release wave.
- No broad `git add`, checkout/reset/clean, `pkill`, `killall`, manual uvicorn.
- Frozen unrelated paths are never touched/staged:

~~~text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
~~~

## 4. Stage 1 — safe real-preview convergence

Stage 1 master:

~~~text
102_STAGE_1_SAFE_DEV_SCOPED_V2_PREVIEW_MASTER_TZ.md
~~~

### S1.W0 — strict harness stabilization checkpoint

Current W3 tooling is dirty and contains invalid conditional acceptance of V1
and mobile 401. Before backend work:

- harden launcher lifecycle/config hygiene;
- make E2E strict `today.v2.1 / 3 / 10`, no skips/conditional V1;
- unit/full/build gates green;
- run current canonical V1 runtime only as an expected fail-closed diagnostic;
- scoped commit/push harness and blocker documents.

This produces a clean baseline. It does not claim W3 real success.

### S1.W1 — pure request-scoped selection foundation

- create pure typed preview-selection context/resolver;
- no global settings mutation;
- no request/header/frontend integration yet;
- selected scoring/cache identity accepts an explicit request-scoped override;
- defaults remain byte/behavior-compatible for all existing callers;
- security truth table and cache concurrency tests.

### S1.W2 — guarded request/frontend/service integration

- frontend dev-only header only on local host `127.0.0.1|localhost`, port 3003;
- backend requires exact header + local origin/proxy facts + non-production app
  env + dedicated dev-auth identity;
- route passes immutable selection context to TodayService;
- TodayService/cache/scoring use same selected family;
- ordinary requests remain current flag-selected V1 before release;
- no DB schema/session/global env mutation;
- full API/frontend/contracts tests;
- scoped commit/push.

### S1.W3 — controlled canonical API convergence

- preflight accepted commit/local-origin security tests;
- one `sudo systemctl restart solarsage-api.service`;
- no env edit and no global V2 flag change;
- ordinary control request remains V1;
- dedicated local preview request becomes V2 `today.v2.1 / 3 / 10`;
- real payload/provenance proof, cache separation, service health;
- docs-only evidence commit/push.

### S1.W4 — strict real preview completion

- start `pnpm preview:v2:real` on 3003;
- strict desktop + mobile E2E with zero interception;
- screenshots and redacted network proof;
- actual signal/no-orphan/config-clean proof;
- user review URL stays running after accepted commit/push;
- no fixture dependency.

Stage 1 exit:

~~~text
READY_STAGE_1_REAL_PREVIEW_FOR_USER_REVIEW
~~~

## 5. Stage 2 — release completion

Stage 2 master:

~~~text
103_STAGE_2_PREVIEW_TO_MAIN_PRODUCTION_MASTER_TZ.md
~~~

### S2.W1 — user visual review corrections

- preserve strict real API path;
- only accepted visual/content changes;
- no backend astrology inference on frontend;
- desktop/mobile/dark/390px proof;
- scoped commit/push for each material correction.

### S2.W2 — release-candidate hardening (B5)

- contracts generate/check/compat idempotent;
- full frontend Vitest/typecheck/build/guardrails;
- full API pytest zero failures;
- full sidecar pytest zero failures;
- real local dev-auth E2E;
- real Telegram HMAC E2E against release candidate;
- security guard proves preview override impossible in production/public flow;
- generated artifacts clean;
- branch audit against origin/main;
- produce `READY_STAGE_B_FOR_MAIN_RELEASE`.

### S2.W3 — main integration

Execute amended `90_MAIN_RELEASE_DEPLOY_TZ.md`:

- fetch and verify origin/main ancestor;
- merge `--no-ff` feature branch into main;
- run post-merge contract/type checks;
- push origin/main without force;
- local/origin main equality.

### S2.W4 — production deploy

Safe dependency/runtime order:

1. build one shared contract wheel from accepted main SHA if required;
2. install same wheel into sidecar/API venvs and `pip check`;
3. build isolated frontend release dist;
4. backup env and current `.next-prod` atomically;
5. set global V2 release flags true only now;
6. restart sidecar if dependency/runtime changed;
7. restart API after env/dependency convergence;
8. swap frontend release dist to `.next-prod`;
9. restart frontend;
10. verify nginx unchanged/healthy.

No manual uvicorn, no port 8001 API, no destructive removal before smoke.

### S2.W5 — production acceptance and rollback proof

- health/status/PIDs/start timestamps;
- API real V2 payload proof;
- Telegram HMAC browser real UI proof;
- horizons/actions/technical/sphere navigation DOM proof;
- no fixture/mock network;
- production screenshots;
- logs privacy audit;
- exact deployed git SHA;
- rollback build/env/service commands verified;
- final report and goal completion only after all proof is present.

## 6. Dev-preview override lifecycle

The request-scoped preview boundary is not a release feature and must remain
strictly production-dead:

~~~text
APP_ENV=production -> override always false
non-loopback/public origin -> false
ordinary Telegram session -> false
missing/wrong marker -> false
port other than 3003 -> false
global settings are never mutated
~~~

At production release global `SOLARSAGE_V2_ENABLED=true` becomes the normal
selection source. The dev boundary may remain as dead development tooling only
if security tests prove it unreachable in production; otherwise it is removed
in S2.W2 before main.

## 7. Commit checkpoints

Expected independent commits, subject names finalized in acceptance docs:

~~~text
S1.W0 strict real-preview harness
S1.W1 request-scoped selection foundation
S1.W2 guarded integration
S1.W3 runtime evidence docs
S1.W4 strict preview acceptance
S2.W1 visual corrections as needed
S2.W2 release hardening/evidence
S2.W3 merge commit on main
~~~

No mega-commit mixing runtime operations, backend selection and frontend UI.

## 8. Global verification matrix

Minimum final matrix, with exact commands refined per wave:

~~~bash
pnpm contracts:generate
pnpm contracts:check
pnpm contracts:compat
npx vitest run
pnpm typecheck
pnpm guardrails:prod
pnpm guardrails:contracts
pnpm guardrails:frontend
apps/api/.venv/bin/python -m pytest apps/api/tests/ -q
apps/solarsage/venv/bin/python -m pytest apps/solarsage/tests/ -q
NEXT_DIST_DIR=.next-release-proof pnpm build
E2E_BASE_URL=http://127.0.0.1:3003 pnpm exec playwright test e2e/real-v2-preview.spec.ts --project=chromium --project=mobile
E2E_BASE_URL=https://dev.astro.vasiliy-ivanov.ru pnpm exec playwright test <strict-production-real-spec>
~~~

Targeted tests never replace full gates.

## 9. Completion evidence

Final callback must include:

- feature SHA and origin feature equality;
- merge/main/origin main SHAs;
- exact commit list;
- full test counts, not generic PASS;
- API/sidecar/frontend deployed PIDs and active timestamps;
- exact V2 versions and horizon order from real HTTP;
- local 3003 and production no-interception proofs;
- mobile/desktop screenshot paths;
- production health statuses through nginx;
- env flags reported only as booleans;
- build/wheel SHA-256 and rollback locations;
- proof frozen unrelated paths untouched;
- no secrets/personal raw data.

Only then may the active goal be marked complete.
