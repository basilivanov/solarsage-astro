# SolarSage V2 Personal Day Preview — Implementation Report

Status: COMPLETE_PENDING_ARCHITECTURE_REVIEW
Date: 2026-07-10
Base SHA: `c9bc36bd9a947566eddb1ffcf5617967c7412676`
Branch: `preview/solarsage-v2-personal-day-ux`
Implementation commit SHA: `4438d18b489861d2d390e7a4a3cc557aa8461154`

## Scope delivered

- `/day/2026-07-08` now presents the existing compact day summary, then the
  personal V2 activation-evidence card, then the 12 concrete advice rows;
  V1 payloads render no empty V2 gap.
- The card localizes backend-owned evidence only, exposes it progressively,
  and retains stable DOM/ARIA selectors for the public test contract.
- `pnpm preview:v2` starts the test-only mock API on `127.0.0.1:18092` and
  Next dev on `0.0.0.0:3003`; production ignores the development rewrite.
- A Next 16 development-origin allowlist for `127.0.0.1` fixes the mock
  visual auth flow. Without it, Next rejected HMR/client initialization when
  the preview server was bound to `0.0.0.0`, so `useTelegramAuth` never sent
  its fixture-backed auth request.

## Sidecar rollout proof

Pre-restart observation from the implementation handoff: the prior sidecar
process did not expose `/v1/activation-layer` in live OpenAPI. The local
journal confirms the old PID `443050` served the final pre-restart OpenAPI
request at `2026-07-10 11:02:50 MSK`, then shut down.

After the authorized restart:

- `solarsage-sidecar.service` is `active/running` since
  `2026-07-10 11:02:50 MSK`, MainPID `1593852`.
- `GET /v1/health` is HTTP 200 with `ok=true`.
- Live OpenAPI contains `/v1/activation-layer`.
- The live endpoint returns HTTP 200 with calculation version `ss-calc-1.1.0`,
  activation-layer version `al-1.0`, and schema `activation-layer.v1`.
- IDs were unique and every `by_planet`, `by_house`, `by_lot`, and `by_angle`
  reference resolved to a returned activation.

The requested fixture's selected day produced 158 activations. Aggregate
counts only (no birth inputs):

| Technique family | Activations |
| --- | ---: |
| transit | 118 |
| progression | 17 |
| return | 17 |
| profection | 4 |
| firdar | 2 |

For that day no eclipse window is active, so the returned technique set has
no `eclipse_window` activation. The endpoint's own representative default-all
test date returned 160 activations and included `eclipse_window: 2`; its
family aggregates were transit 125, return 15, progression 12, profection 4,
firdar 2, eclipse 2. This is the date-dependent behavior asserted by the
sidecar test suite, rather than a fabricated eclipse activation.

## Files changed

- Presentation and UI: `components/today/activation-evidence-card.tsx`,
  `concrete-day-advice.tsx`, `technique-chip.tsx`, `today-screen.tsx`,
  `why-expanded.tsx`, `lib/presentation/today-v2.ts`.
- Preview runtime and fixtures: `next.config.mjs`, `package.json`,
  `e2e/mock-visual/start-v2-preview.mjs`, `e2e/mock-visual/README.md`,
  `e2e/mock-visual/day-v2.spec.ts`, its typed fixture plus JSON fixtures.
- Tests and guardrails: the Today/V2 downstream tests, V2 card and keyboard
  tests, presentation helper test, preview-isolation guard, and mobile
  visual baselines.
- Review materials: this report and the three committed screenshots below.
- Configuration/test include support: `.gitignore` and `tsconfig.json`.

## Verification

| Command | Result |
| --- | --- |
| `git diff --check` | PASS |
| `pnpm exec tsc --noEmit --pretty false` | PASS |
| Targeted `npx vitest run` (8 files) | PASS — 39 tests |
| Full `npx vitest run` | PASS — 91 files, 931 tests |
| `pnpm build` | PASS |
| `E2E_BASE_URL=http://127.0.0.1:3003 pnpm exec playwright test e2e/mock-visual/day-v2.spec.ts --project=mobile --update-snapshots` | PASS — 1 test |
| Same Playwright command without `--update-snapshots` | PASS — 1 test |
| `PYTHONPATH=apps/solarsage apps/solarsage/venv/bin/python -m pytest apps/solarsage/tests/test_activation_layer_endpoint.py -q` | PASS — 10 tests |

The final sidecar pytest uses the same `PYTHONPATH` as its systemd unit. The
unqualified root-level pytest invocation cannot import the sidecar package in
this shell; that was an environment-path issue, not a service failure.

## Preview and review assets

- Preview URL: `http://127.0.0.1:3003/day/2026-07-08`
- Listening ports: Next preview `3003`, mock API `18092`.
- Preview process: tmux window `astro:v2-preview`.
- Production frontend `3002` still returned HTTP 200 during verification.

Screenshots:

- `docs/work/2026-07-10_solarsage-v2-personal-day-preview/assets/v2-card-collapsed-mobile.png`
- `docs/work/2026-07-10_solarsage-v2-personal-day-preview/assets/v2-card-expanded-mobile.png`
- `docs/work/2026-07-10_solarsage-v2-personal-day-preview/assets/v2-day-full-mobile.png`

## Self-review

- Confirmed the V2 card is immediately after `day-summary-card` and before
  concrete advice; `v2=null` renders no card.
- Confirmed collapsed/expanded ARIA state, max-three evidence selection,
  localized labels, and keyboard-accessible advice evidence.
- Confirmed runtime code has no preview fixture import and production ignores
  `DEV_API_REWRITE_BASE_URL`.
- Visually checked all three review assets: warm light V2 card, no raw English
  evidence/IDs/debug data, no horizontal overflow, and no masked product UI.
  The full mobile asset captures the complete `today-screen` locator from its
  collapsed top state, beginning with summary → V2 card → concrete advice.

## Explicit NOT TOUCHED for main merge

- `main`, push, and merge.
- Production frontend on port `3002` and `solarsage-frontend.service`.
- API on port `8000` and `solarsage-api.service`.
- nginx, production rollout flags, database, `.env`, and `.env.production`.
- Known user-owned untracked paths: `.grace/`, `grace.db`, `skills/`, and
  `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`.
