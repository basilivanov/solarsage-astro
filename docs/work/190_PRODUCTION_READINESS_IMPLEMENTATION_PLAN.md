# 190 — Production Readiness Implementation Plan

Date: 2026-07-19. IMPLEMENTATION IN PROGRESS — slices land via reviewed commits; no unreviewed push. Sources:
AGENTS.md, 189 (R1-corrected audit), 80 (accepted ephemeris gate design),
Makefile, `scripts/audit_today.py`, `scripts/deploy/prod-orchestrator.sh`,
`.github/workflows/{ci,e2e,deploy-production}.yml`, e2e/mock READMEs.

**Status legend:** ✅ confirmed done (with evidence) · 🔲 not implemented ·
🚦 launch criterion (must be green before public exposure)

**Current truth:** live release `72871dbd` predates this gate; it runs
with green liveness but without production-readiness proof (Moshier math at
deploy time, Telegram webhook ingress blocked pending=2, and it was deployed
while CI was red). The branch now HAS the source-quality/tag gates, but the
full artifact-acceptance contour remains incomplete (P1-2/P1-3) — so the
live release is not yet proof of the new gate.

## Current launch scope

The current gate is limited to the minimal P0 contour below. **P1/P2 are
NOT cancelled and NOT deferred/non-binding** — they will be implemented as
their own later phases per owner decision; the earlier P0-1 (workflow
release-quality gate) and P0-3 (Telegram ingress) items from the first
version of this plan are likewise moved into those separate P1/P2 slices
by owner decision. P0-4 (migration safety) was pulled back forward by
owner decision and is now implemented locally as PARTIAL (remote host
apply and a real candidate run are still pending) — see the P0-4 section.

## Simplified P0 ephemeris design (supersedes the installer design)

Owner decision (2026-07-19): the Swiss Ephemeris bundle is BAKED INTO the
immutable sidecar OCI image at build time. The host installer
(`prod-ephemeris-install.sh`) and the `/opt/solarsage-ephemeris`
current/previous host layout are NOT the target design.

- **Pinned artifact/provenance at build:** the sidecar Dockerfile stages the
  licensed bundle with `manifest.json` + `manifest.sha256` at a fixed image
  path WITHOUT any symlink (e.g. `/opt/solarsage-ephemeris/bundle` inside
  the image); build fails closed without the bundle/provenance
  (build-arg/secret, never committed).
- **Startup proof:** sidecar startup runs fixed + boundary FLG_SWIEPH probes
  with returned-flag checks; production is fail-closed on Moshier.
- **Health identity:** `/v1/health` exposes exact `ephemeris_artifact_id` +
  `ephemeris_manifest_sha256` + `engine=swieph`; orchestrator `prove_health`
  requires them and the `EPHEMERIS_EXPECTED_*` env pins exactly.
- **Superseded commits:** `1c7a884`, `4566462`, `f4fe81f` implement the
  superseded installer design and REQUIRE REFACTOR BEFORE MERGE. Keep:
  runtime verifier + returned-flag checks, health v2, exact orchestrator
  proof, sidecar tests. Remove/replace: host installer, host
  artifact layout + `current/previous`, host-prepare artifact wiring and
  compose host mount — replaced by the image-baked bundle.

---

## Phase P0 — blocking (before any public exposure)

Scope per owner decision: P0 currently contains ONLY the ephemeris gate
(P0-2 below) plus the manual launch gates at the end of this phase.
P0-4 (migration safety) was pulled forward and is implemented locally as
PARTIAL (remote apply/candidate pending) — see its section below.
Former P0-1 (workflow release-quality gate) and P0-3 (Telegram ingress)
are moved to separate P1/P2 slices — see "Current launch scope" above;
their text below is kept as the design for those later slices.

### P0-1. Exact-SHA release-quality gate in the ONE deploy workflow

- **Goal:** red code can never reach build/deploy again.
- **Status: PARTIAL.** Sub-parts: `source-quality` ✅ (implemented),
  `tag` ✅ (implemented), artifact-acceptance BLOCKED (P1-2/P1-3).
  Details: `source-quality` job in
  `deploy-production.yml` is a LOCAL REUSABLE call to the whole existing CI
  (`uses: ./.github/workflows/ci.yml` — no duplicated commands); `build`
  `needs: source-quality`, so no login/bundle fetch/image build happens
  before full green CI on the exact SHA. `ci.yml` gained `workflow_call`;
  contract base ref: PR merge-base unchanged, push uses
  `github.event.before`, workflow_call/dispatch use `HEAD^`.
- **Tag (implemented):** `tag` job `needs: deploy`, `contents: write`;
  re-verifies refs/heads/main + exact 40-hex SHA, checkout exact SHA
  fetch-depth 0, creates annotated immutable collision-safe
  `prod-YYYYMMDDTHHMMSSZ-<short12sha>` (fails on existing tag, never
  force/overwrite), verifies tag target == GITHUB_SHA, pushes only
  `refs/tags/<tag>`; annotation carries exact SHA + workflow run URL.
- **Smoke/rollback authority:** the canonical health + front/geo smoke +
  recorded rollback already run INSIDE the orchestrator during deploy
  (proven by OC28); no second functional-smoke job was added.
- **artifact-acceptance: PARTIAL, blocked** by P1-2 (independent oracle,
  owner input) and P1-3 (V2 same-payload UI proof needs an owner-approved
  committed today.v2.x payload). The blocking acceptance full gate
  (audit-day-freeze + oracle + same-payload proof) MUST block deploy/tag
  until those pass.
- **Files:** `.github/workflows/deploy-production.yml` (add jobs/needs);
  reuse `ci.yml` commands verbatim.
- **Companion CI fixes so the gate can pass:** run sidecar in backend CI
  (service container/launch step with production-like ephemeris — fixes the
  backend 64 errors and the sidecar health 503 in CI); replace
  tracked `.antigravitycli` symlink (delete it from the repo) or scope the
  secret guard to skip symlinks WITHOUT reading their targets (never copy
  the target's secret content into the repo).
- **Responsible:** Kimi implements; owner approves PR.
- **Blockers:** source-quality/tag — none (private-plan branch protection
  irrelevant, the gate lives in the workflow itself). Full artifact
  acceptance remains blocked by P1-2 (independent oracle, owner input) and
  P1-3 (owner-approved committed today.v2.x payload).
- **Artifacts:** workflow run evidence per job; pass = all jobs green for
  the exact SHA; fail = no build, no deploy.

### P0-2. Swiss Ephemeris artifact baked into the sidecar image + exact identity

- **Goal:** production calculates with real Swiss files and PROVES it at
  build/runtime/deploy layers; identity drift impossible; no host-side
  artifact installation.
- **Design (simplified, owner-approved):** the licensed bundle
  (`ephe/` data files + `manifest.json` + `manifest.sha256` with
  provenance: artifact_id, supported_date_range, swiss_data_version,
  pyswisseph version, full inventory with size+sha256) is staged into the
  immutable sidecar OCI image at a fixed path WITHOUT symlinks
  (`/opt/solarsage-ephemeris/bundle`).
- **Steps:**
  1. Secret-owner supplies the licensed bundle + provenance as a build
     input (build-arg/secret, never committed to Git).
  2. `apps/solarsage/Dockerfile`: stage the bundle at
     `/opt/solarsage-ephemeris/bundle`, then run the single verifier owner
     (`solarsage.core.ephemeris_runtime.verify_and_configure`) at build
     time — build FAILS CLOSED on missing/invalid bundle, bad manifest, or
     a Moshier-only probe result.
  3. Sidecar runtime (already implemented): startup gate verifies the
     manifest + fixed/boundary probes require returned FLG_SWIEPH; every
     calculation passes `calc_ut_checked`; production fallback is fatal.
  4. Health: `/v1/health` exposes exact `ephemeris_artifact_id`,
     `ephemeris_manifest_sha256`, `engine=swieph`, canonical
     `calculation_version`.
  5. Orchestrator `prove_health` (already implemented): requires
     `engine=swieph`, exact `EXPECTED_CALCULATION_VERSION`, and exact
     `EPHEMERIS_EXPECTED_ARTIFACT_ID` /
     `EPHEMERIS_EXPECTED_MANIFEST_SHA256` env pins (required keys in
     `/etc/solarsage/app.env`).
  6. Compose: NO host ephemeris mount — the bundle lives only inside the
     image; `SOLARSAGE_EPHEMERIS_ROOT=/opt/solarsage-ephemeris/bundle`,
     `SOLARSAGE_APP_ENV=production`.
- **Removed from P0-2 by the simplification:** host installer
  (`prod-ephemeris-install.sh`), `/opt/solarsage-ephemeris`
  `current/previous` host layout, host-prepare artifact wiring, and the
  compose host mount — superseded by the image-baked bundle (superseded
  commits `1c7a884`, `4566462`, `f4fe81f` require refactor before merge;
  keep: runtime verifier + flag checks, health v2, exact orchestrator
  proof, sidecar tests).
- **Files:** `apps/solarsage/Dockerfile`,
  `apps/solarsage/solarsage/core/{ephemeris_runtime.py,health.py,config.py}`,
  `infra/production/docker-compose.app.yml`,
  `scripts/deploy/prod-orchestrator.sh`.
- **Responsible:** secret-owner (bundle + provenance at build) → Kimi
  (Dockerfile/wiring) → operator (env pins).
- **Blockers:** bundle licensing/provenance decision (owner).
- **Artifacts:** image manifest identity, build log proof, health v2 JSON,
  deploy health proof.
- **Pass/fail:** build fails without a valid bundle; startup fails on
  Moshier; deploy health proof requires exact identity match.

### P0-3. Telegram webhook ingress

- **Goal:** real Telegram delivery reaches `/api/telegram/webhook`.
- **Options (owner decision):** (a) provider unblock Telegram DC ranges on
  157.22.192.242 (support ticket evidence); (b) relay via an unfiltered
  host (nginx stream/proxy on an approved host → apex), keeping the
  canonical webhook URL stable.
- **Verify:** `getWebhookInfo` shows pending=0 and no last_error after a
  real /start from a real client; webhook smoke still passes.
- **Responsible:** owner (provider decision/ticket) or operator (relay).
- **Pass/fail:** real /start answered in a real client; pending=0.

### P0-4. Migration safety contract

- **Goal:** forward migrations never strand the app on failed rollout.
- **Status: PARTIAL (implemented locally 2026-07-19; remote candidate run
  and host sudoers apply pending).** Implemented: orchestrator `migrate
  <sha>` now records an atomic migration marker (target SHA, exact resolved
  api digest, backup dump path, verified timestamp, `status=heads_applied`)
  only after a proven `alembic upgrade head` + separate `alembic current
  --check-heads` with the same pinned api digest; a failed upgrade/head
  check leaves the previous marker byte-identical. Every new deploy target
  is gated on a valid marker + verified non-symlink backup pair before
  activation (same-SHA no-op and rollback unchanged). `status` prints
  read-only marker evidence. The Deploy Production job runs `migrate
  <sha>` then `deploy <sha>` on every manual run (upgrade is a no-op
  without new revisions); the forced wrapper and sudoers allow exactly
  `migrate <40hex>` additionally to deploy/source-check. Evidence:
  test-prod-orchestrator 32/32 (OC25/OC29/OC30), test-prod-github-wrapper
  63+10 (MIG_*), host-offsite sudoers assertions, github-access 162.
  Pending: real workflow candidate run and `prod-host-prepare --apply`
  installing the two-capability sudoers on the host.
- **Design:** backward-compatible expand/contract only; pre-migration
  backup (already in `migrate <sha>`); head-check evidence before app
  switch; migration result recorded; no blind auto-migrate in the ordinary
  app/api path; rollback of app code never implies schema rollback.
- **Files:** runbook §5, `deploy-production.yml` (migrate step always runs
  before deploy), `scripts/deploy/prod-orchestrator.sh`,
  `infra/production/solarsage-github-deploy`,
  `infra/production/solarsage-deploy.sudoers`.
- **Pass/fail:** head check green before activation; failed migration →
  stop before app switch, DB restorable from pre-migration dump.

### Launch gates (manual, required before launch announcement) 🚦

- BotFather: menu label «Мой день ✨» + avatar upload (operator; Bot API
  proven unable to set these).
- Real restore rehearsal once on a real dump:
  `prod-orchestrator restore /var/backups/solarsage/db-<latest>.dump --manual-confirm`
  → expect "Restore rehearsal OK".
- Stop rule: Phase P0 complete = gate workflow green on exact SHA, SWIEPH
  proven, ingress working, migrations contract documented. Safe stop:
  report + owner review before P1.

---

## Phase P1 — before public launch

### P1-1. Deterministic `audit-day-freeze`/`audit-day-live` on exact SHA

- **Goal:** full-pipeline audit becomes a deterministic release gate.
- **Truth today:** frozen mode reads live DB/profile/access, calls sidecar
  and current engine → NOT deterministic until seeded.
- **Steps:** seeded fixed DB fixture (test profile/user), pinned ephemeris
  artifact + tzdata version, exact deployed image; run
  `make audit-day-freeze USER_ID=<seed> DATE=<fixed>` inside artifact
  acceptance (P0-1 step 3); `audit-day-live` stays an operator diagnostic,
  never a gate.
- **Files:** `scripts/audit_today.py` — REUSE, no rewrite; if seeding
  inputs are missing, add only an EXTERNAL seeded fixture/adapter (separate
  file feeding the script), never modify the audit pipeline itself.
- **Pass/fail:** byte-stable audit artifacts across two runs (hash match).

### Status note 3 (2026-07-19, P1-7 visual baselines slice)

- **P1-7 IMPLEMENTED (verified locally; remote candidate runs pending):**
  ready-screen baselines for calendar/profile/readings/horary/natal +
  state baselines: horary no-credit (locked, `data-access-state=locked`),
  natal profile_incomplete, natal report GENERATING and ERROR on the unified
  `natal-report-screen` root (`data-state` + role/aria-busy per AGENTS
  contract; empty horary history is inside the ready baseline).
- Baselines generated for chromium AND mobile (`*-{chromium,mobile}-linux.png`)
  and proven deterministic: TWO consecutive FULL-GATE runs without
  UPDATE_SNAPSHOTS — 52/52 passed each (26 chromium + 26 mobile, the exact
  visual-regression.yml command including day-v2). Missing-baseline fails
  closed (profile-ready deleted → test fails; restored → passes). No
  screenshot masking of real UI; only the Next.js dev chrome is hidden via
  the shared hideNextOverlay selectors (verified pixel-level: no dev
  indicator in regenerated baselines). Error baseline is localized
  ("Не удалось загрузить отчёт").
- Workflow: `visual-regression.yml` reusable (`workflow_call`), baseline
  suite only (acceptance-day excluded — P1-3 blocked on v1);
  `deploy-production.yml` job `visual-baselines` (reusable), `build` now
  `needs: [source-quality, visual-baselines]`. Single production workflow
  and manual trigger preserved.
- Product contract additions (minimal): `natal-report-screen` unified root
  across all branches (loading/not_found/error/generating/failed/ready/
  section-view) with data-state + role + aria-busy; `horary-screen` gained
  `data-access-state` (unlocked|locked). No business-logic changes.
- Remote candidate runs: PENDING (not yet executed on GitHub).
- P1-2 (oracle), P1-3 (V2 same-payload), P1-6 (full real E2E) stay OPEN.

### Status note 2 (2026-07-19, P1-4/P1-5 slice)

- **P1-4 done ✅:** `today.spec.ts` rewritten without early returns
  (`ensureOnboarded` completes the REAL onboarding via `completeOnboarding`
  copied step-for-step from onboarding-real); `cross-feature-navigation.spec.ts`
  rewritten with required link+destination assertions (no conditional clicks,
  no expect(true)); `deriveTelegramUserId` now run-salted
  (E2E_RUN_SALT/GITHUB_RUN_ID) with created-id persistence to
  E2E_CREATED_USERS_FILE; cleanup adapter
  `scripts/acceptance/cleanup_e2e_users.py` (guarded APP_ENV=test|acceptance +
  localhost DB, per-id verified deletion) wired into `e2e.yml` as a separate
  `if: always()` step; `e2e/README.md` corrected (manual-only trigger, real
  spec inventory, stale refs removed).
- **P1-5 PARTIAL / in progress (measured facts, no invented thresholds; acceptance runs pending):**
  - sidecar: TOTAL **90.97%** after deleting dead `services/calculator.py`
    (zero runtime callers, rg-verified; not replaced by tests for dead code);
  - frontend: lines/statements **46.67%**, functions **64.89%**, branches
    **76.38%** (v8, 1099 tests green) — thresholds wired as Vitest built-in
    `coverage.thresholds` (46/46/64/76);
  - API: TOTAL **81.77%** (1490 passed, integration-marked tests excluded;
    critical rows auth 62, geo 53, referral 43, telegram_webhook 91,
    access 69, geonames 53, llm 60, today_service 89, today_interpretation 88).
  - CI gates (ci.yml): pytest coverage + TOTAL via `coverage report
    --fail-under` (API 81, sidecar 90 (precision=2)) + per-file built-in
    `--include/--fail-under` gates + diff-cover (changed lines >= 80 on PR)
    + artifact uploads. Measured finding: `--cov-fail-under` in pytest-cov
    prints FAIL but exits 0 in this env — TOTAL gates therefore use the
    coverage CLI directly.
  - Exclusions (documented): `test_audit_live_isolates_output` marked
    `@pytest.mark.integration` (env-dependent audit integration; canonical
    gate is artifact-acceptance + make audit-day).
  - diff-cover threshold part: wired off-the-shelf (PR-only step) but NOT
    yet accepted against a real PR; two consecutive candidate runs are still
    pending. Frontend changed-lines coverage is NOT claimed.
    Coverage tooling: `pytest-cov` in api+solarsage dev deps,
    `@vitest/coverage-v8` in frontend dev deps (lockfile updated).
  - Measured findings honored: dead `services/calculator.py` (zero runtime
    callers) deleted, not covered by new tests; TOTAL floors set at the
    measured baselines (API 81, sidecar 90); API result 1490 passed /
    4 skipped / 7 deselected, sidecar 220 passed.

### Status note (2026-07-19, acceptance slice)

- **P1-1 partial ✅:** `artifact-acceptance` job in `deploy-production.yml`
  (blocking for deploy): ephemeral Postgres + migrations, seed from the
  EXACT committed `00_input_profile.json` (external adapter, ephemeral DB
  only), exact-image sidecar proof (`engine=swieph` + release_sha),
  `make audit-day-freeze` ×2 with byte-stability + untracked-artifact
  cleanliness, `check_audit_golden.py`, `prove_today_v2_real_api.py`
  (explicit dev env). No OpenRouter dependency for frozen mode (it uses the
  committed baseline).
- **P1-3 BLOCKED (honest):** the V2 same-payload UI proof
  (`e2e/mock-visual/acceptance-day.spec.ts` + preview
  `ACCEPTANCE_PAYLOAD_PATH` override) fails closed while the committed
  artifact is `today/v1` — it requires an owner-approved committed
  `today.v2.x` `11_final_today_payload.json` (live audit refresh). Evidence
  screenshot is not a visual baseline; P1-3 stays open.
- **P1-2 NOT started:** independent oracle source + tolerances need owner
  input; nothing invented.

### P1-2. Independent calculation oracle

- **Goal:** owner-approved independent reference for positions/houses/
  aspects/timezone with recorded engine flag, artifact hash, UTC, tzdata
  version, and owner-approved tolerances (not invented by us).
- **Constraint (from 189 R1):** reference must be neither product code nor
  the same runtime installation; existing `audit_astronomy_oracle.py` is
  same-engine and flag-blind — insufficient alone.
- **Steps:** owner/domain approves source + tolerances; implement as an
  EXTERNAL oracle/adapter or a separate authority artifact that the
  existing audit flow invokes (no modification or rewrite of
  `audit_today.py`); record provenance in the audit artifact.
- **Pass/fail:** all fixed-UTC/coordinate cases within approved tolerances;
  engine flag SWIEPH recorded per case.

### P1-3. Same-payload UI proof

- **Goal:** the SAME `11_final_today_payload` audit artifact renders
  correctly — calculation truth and display truth proven together.
- **Steps:** feed the payload artifact into the existing Playwright route
  fixture (mock-visual harness); validate schema + key DOM states + one
  screenshot per key state; reuse, no new harness.
- **Files:** `e2e/mock-visual/` (fixture + spec additions), acceptance job.
- **Pass/fail:** schema valid, DOM contract (data-testid/data-state) exact,
  screenshot matches baseline.

### P1-4. E2E false-greens + automated cleanup

- **Goal:** specs prove paths; reruns don't collide.
- **Steps:** rewrite `today.spec.ts` (no early return),
  `cross-feature-navigation.spec.ts` (no conditional clicks, real final
  assertions); fix `e2e/README.md` (remove false auto-trigger claims,
  missing specs); randomize/persist-unique test users
  (`deriveTelegramUserId` + run salt) and add a DB user cleanup fixture
  (delete created users after each run, verified count) — cleanup runs ONLY
  in the ephemeral acceptance DB / test environment; deleting any data from
  production is forbidden by design.
- **Files:** `e2e/*.spec.ts`, `e2e/fixtures.ts`, README.
- **Pass/fail:** specs fail when the path breaks; two consecutive full runs
  green without manual DB intervention.

### P1-5. Coverage tooling + thresholds

- **Goal:** measured, gated coverage; no invented percentages.
- **Steps:** add `pytest-cov` (backend, branch) + `@vitest/coverage-v8`
  (frontend) to CI; per-critical-file thresholds (auth, referral, access,
  webhook, geo, day pipeline, calculator.py) over aggregate; changed-code
  ≥80% on PR.
- **Files:** `ci.yml`, `vitest.config.ts`, `apps/api/pyproject.toml`.
- **Baseline (measured):** API 82% combined (llm/*, yesterday 0%;
  referral 43%; auth 62%), sidecar 90% (calculator.py 0%), frontend
  unmeasured.
- **Pass/fail:** thresholds enforced; report artifacts on every PR.

### P1-6. Real E2E missing flows (real HMAC, no interception)

- **Status: PARTIAL (2026-07-19).** Implemented locally: public CityPicker DOM
  contract (`city-picker-input` / `city-picker-suggestions` /
  `city-picker-suggestion`; NOT globally unique — onboarding can render two
  pickers when "same as birth" is unchecked, so tests scope the locator to
  the active screen/sheet) adopted by `completeOnboarding` and
  `onboarding-real.spec.ts` (fragile placeholder / `ul li` selectors
  removed); new `e2e/profile-city-checkin.spec.ts` covers
  the profile "Где живу сейчас" edit with real GET `/api/profile` proof
  (city/coordinates/timezone) and the check-in mood → energy → accuracy flow
  with fresh-load read-back («Оценка уже сохранена»), no interception, no
  conditional passes. Release-gate wiring implemented locally: `e2e.yml` is
  reusable (`workflow_call`, required string `suite` + required
  `E2E_TELEGRAM_BOT_TOKEN` / `E2E_OPENROUTER_API_KEY` secrets — missing
  secrets are a fail-closed blocker) with a `release` suite of exactly the
  real-HMAC no-interception specs (onboarding-real, today, calendar,
  cross-feature-navigation, profile-city-checkin, readings-horary,
  natal-report, chat); `deploy-production.yml`
  adds the `real-e2e` reusable job (`needs: [source-quality,
  visual-baselines]`) and `deploy` now needs it, so a failing real flow
  blocks migrate/deploy/tag. Second slice (2026-07-19, local): real-HMAC
  no-interception specs for the remaining user paths —
  `e2e/readings-horary.spec.ts` (readings list contract + horary submit →
  auto-navigated answer view → API read-back `status=answered` → history;
  the product has no delete/archive operation, none invented),
  `e2e/natal-report.spec.ts` (preview ready + the product's own
  `/readings/natal/generating` route → redirect → ready report on the
  unified `natal-report-screen` root, API read-back only as additional
  proof; the ephemeral E2E stack sets
  `NATAL_REPORT_ENABLED=true`, the production flag stays off),
  `e2e/chat.spec.ts` (real send → structural assistant reply). Minimal chat
  testids added per AGENTS contract (`chat-screen`/`chat-messages`/
  `chat-message`/`chat-input`/`chat-send`), no business-logic changes.
  Real candidate run on the ephemeral stack is
  PENDING (needs the full real stack + Telegram secrets); the remaining
  P1-6 flows (paywall/referral claim, /start→web_app launch, payment
  webhook idempotency) stay OPEN.
- **Goal:** every user-facing capability has real-path evidence.
- **Steps:** add specs for readings list + horary lifecycle (no
  delete/archive — the endpoint does not exist), natal generate/view, chat,
  checkin, paywall/referral claim, profile edit city
  change, /start→web_app launch; use P1-4 cleanup. Payment webhook
  idempotency + sandbox proof (repeated callback → single effect).
- **Files:** `e2e/*.spec.ts`, payment tests.
- **Pass/fail:** all flows green on the ephemeral real stack in artifact
  acceptance; failures block.

### P1-7. Visual baselines beyond Today

- **Goal:** key screens/states have visual baselines per AGENTS contract.
- **Steps:** add `toHaveScreenshot` baselines for calendar, profile,
  readings, horary, natal (+ locked/error/generating states); mask/struct
  dynamic LLM zones; restore deleted snapshot PNGs policy-compliant.
- **Files:** `e2e/mock-visual/*.spec.ts` + snapshots.
- **Pass/fail:** visual suite green in release-candidate; missing baseline
  fails closed.

### P1-8. Canonical post-deploy smoke command

- **Goal:** one documented non-destructive smoke after every deploy.
- **Steps:** runbook command set: orchestrator status, health ×3,
  `GET /api/geo/autocomplete?q=Москва` (200+timezone_id), webhook synthetic
  POST (200 exact/403), front 200, referral auth smoke optional.
- **Files:** `docs/PRODUCTION_RUNBOOK.md`.
- **Pass/fail:** each check exact; failure → rollback authority (P0-1 step 5).
- **Status ✅ (implemented):** `run_smoke` (front 3002 + geo autocomplete
  with timezone_id) is wired into the orchestrator's `deploy` at all four
  prove_health call sites (activation, rollback, both no-op paths) — the
  release record is written only after health+smoke, and a smoke failure
  triggers the existing recorded-rollback path. Harness regression case
  OC28 (addressable `fail-smoke-for`): smoke failure → proven rollback with
  byte-identical record, exactly 2 ups; orchestrator harness 30/30.
  Runbook §6.1 documents the canonical non-destructive smoke command
  (health ×3, front, geo, webhook synthetic 200/403 explicitly marked as
  endpoint proof, not real Telegram delivery). Remaining P1 items stay open.

### Stop rule P1

All P1 items green on two consecutive candidate runs. Safe stop: evidence
bundle (coverage, audit hashes, E2E reports, baselines) + owner review.

---

## Phase P2 — hardening (post-launch ok)

- Docker base images pinned by digest; Python deps locked (P2).
  **Status: PARTIAL (2026-07-19).** Base image digest pins implemented
  locally and verified via `docker buildx imagetools inspect`:
  `python:3.12-slim` (3.12.13-slim-trixie) in `apps/api/Dockerfile` and both
  stages of `apps/solarsage/Dockerfile`; `node:20-slim` (20-bookworm-slim) in
  both stages of `apps/web/Dockerfile`; `postgres:15` (15.18) in
  `infra/production/docker-compose.yml` and in the canonical orchestrator
  restore rehearsal (`RESTORE_REHEARSAL_IMAGE` constant — no env override,
  no mutable tag). Root `docker-compose*.yml` stay
  unpinned intentionally (dev/compatibility only per AGENTS, not production
  source of truth); E2E service images unchanged. **Open blocker:**
  Python dependency lock export — both Python images install editable
  packages via pip from pyproject constraints (`>=` ranges included), and
  `apps/api/poetry.lock` is not consumed by the pip-based Docker builds, so
  image dependency content is not bit-reproducible; a lock→constraints
  export pipeline remains an open P2 item (not invented here).
- Branch protection/rulesets when billing allows.
- Stale docs refresh (`e2e/README.md` systemd-era content), harness dedup,
  stale astro ssh config block on apex.
  **Status (2026-07-19, partial):** `e2e/README.md` systemd-era claims
  replaced — the E2E workflow stack is documented as ephemeral
  (Postgres/Redis services + uvicorn sidecar/API + production Next build)
  and production systemd units are never touched.
- ANTHROPIC_API_KEY empty-default documented (harmless while
  LLM_PROVIDER=openrouter).

---

## Confirmed already done (do not redo)

- ✅ Canonical deploy pipeline: immutable images, digest-pinned activation,
  exact health ×3, release record + rollback path, offsite backup (live).
- ✅ Geo P0: fail-closed env + live smoke cyr/lat (188).
- ✅ Telegram tooling: webhook endpoint + secret gate, sync/setup identity
  gates + read-backs, bio/description/commands applied (186/187).
- ✅ Referral canonical bot URLs live (PR #6 + smoke).
- ✅ Laconic UX copy live in webhook + Bot API (addenda 187).

## Introduction order (strict)

P0-1 → P0-2 (artifact decision first — owner) → P0-3 (owner ticket) →
P0-4 → launch gates → P1-1..P1-3 (deterministic audit core) →
P1-4/P1-5 (test integrity + coverage) → P1-6/P1-7 (flows + visuals) →
P1-8 → P2.

Every phase ends with: evidence bundle + report + explicit owner
go/no-go. Any P0/P1 failure = stop, no public exposure, rollback to the
recorded previous release where applicable.
