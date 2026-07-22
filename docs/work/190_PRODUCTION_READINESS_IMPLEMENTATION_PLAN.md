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
while CI was red). The branch now HAS the source-quality/tag gates, and the
P1-3 payload now EXISTS (committed `today.v2.1` camelCase wire artifact
produced by the live audit contour on 2026-07-22, local same-payload UI
proof green); what remains pending is the exact-SHA acceptance run on
GitHub — so the
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
  `tag` ✅ (implemented), artifact-acceptance PARTIAL (P1-3 payload
  produced and locally proven; exact-SHA GitHub acceptance run pending).
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
- **artifact-acceptance: PARTIAL** — P1-2 mechanics exist and are
  fail-closed (astronomy/scoring oracles exit non-zero on houses/scoring/
  top_signals mismatch; 2026-07-22 second-review hardening added the
  final-dayChart proof and full-object downstream compares with directed
  mutation proofs, all exiting non-zero); exact-SHA oracle proof is
  pending with the P1-1 freeze gate. P1-3 is locally proven (2026-07-22):
  the committed `11_final_today_payload.json` is a real `today.v2.1`
  camelCase wire artifact from the live audit contour on the pinned
  proven sidecar image, the acceptance spec discriminates
  `meta.payloadVersion` (never `schemaVersion`, canonically `today/v1`),
  and the local same-payload UI proof is green. The GitHub acceptance run
  on the exact SHA stays pending. The blocking acceptance
  full gate (audit-day-freeze + oracle + same-payload proof) MUST block
  deploy/tag until those pass.
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
  acceptance pending only on the exact-SHA GitHub run (P1-3 payload now
  exists and is locally proven); the P1-2 oracle gate needs no owner
  input — its proof is the exact-SHA freeze run.
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
  suite (acceptance-day now discriminates `payloadVersion` and has a real
  V2.1 artifact; CI inclusion is a separate workflow decision);
  `deploy-production.yml` job `visual-baselines` (reusable), `build` now
  `needs: [source-quality, visual-baselines]`. Single production workflow
  and manual trigger preserved.
- Product contract additions (minimal): `natal-report-screen` unified root
  across all branches (loading/not_found/error/generating/failed/ready/
  section-view) with data-state + role + aria-busy; `horary-screen` gained
  `data-access-state` (unlocked|locked). No business-logic changes.
- Remote candidate runs: PENDING (not yet executed on GitHub).
- P1-3 (V2 same-payload) is locally proven on the real `today.v2.1` wire
  artifact (2026-07-22), GitHub acceptance run pending; P1-6 (full real
  E2E) stays OPEN; P1-2 is
  redefined (2026-07-20) as independent-from-pipeline verification via the
  existing fail-closed oracles — exact-SHA proof pending with P1-1.

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
- **P1-3 PROVEN LOCALLY (2026-07-22):** the acceptance gate now
  discriminates `meta.payloadVersion` (coherent `frontendPayloadVersion`
  + non-null v2 block + `TodayPayloadWireSchema` as final validation) —
  never `schemaVersion`, which is canonically `today/v1` for every series.
  The committed `11_final_today_payload.json` was refreshed by the live
  audit contour (ephemeral DB + local image-baked sidecar + real
  TodayService/LLM, no fixture payload) into a real `today.v2.1` camelCase
  wire artifact; oracles green (astronomy + scoring), `audit-day-freeze`
  ×2 byte-stable, same-payload Playwright acceptance passed locally.
  Evidence screenshot is not a visual baseline; the GitHub acceptance run
  on the exact SHA stays pending.
- **P1-2 (redefined 2026-07-20):** independent-from-product-pipeline
  verification via the EXISTING fail-closed oracles (transit longitudes,
  retrograde flags, moon phase, houses; day_status, sphere_scores,
  top_signals) — no external source, no owner tolerances. 2026-07-22 the
  contour was completed with the payload-vs-recomputed-V2 check
  (`scripts/audit_downstream_v2.py` wired into `audit_today.py`): the
  honest artifact is green (24 intentional unmapped warnings, policy
  pinned `warn`), and directed mutations (dayStatus, score
  amount/contribution, sphere order, topFlags, lost/extra ids) all exit
  non-zero. Combined audit is green on the exact same artifact LOCALLY;
  the exact-SHA GitHub proof stays pending with P1-1.
- **P1-2 third-review hardening (2026-07-22, local):** a second
  independent mutation sweep found eight more downstream fail-opens
  (removed key/title/normalizedScore-null/dominanceCapped-false,
  activationEvidence debug mutation, removed nullable house, extra keys
  in topFlags/evidence) and four astronomy fail-opens (retrograde flip,
  removed house → traceback without summary, removed lunar_phase fact,
  extra transit planet), plus a silent moshier oracle (empty
  /opt/sweph/ephe, calc flags=260). Fixes, all inside the existing
  contour: payload blocks are validated through the public Pydantic
  contracts and compared as canonical model_dump(by_alias=True,
  mode="json") with exact ordered equality (missing/extra keys and
  null-presence are diagnostic failures payload_contract_missing_key /
  payload_contract_extra_key); private-helper oracles were replaced by
  audit-local INDEPENDENT_PROJECTIONS over the actual ScoringV2Result
  and public canon constants; the astronomy oracle now checks exact
  final transit structure/order/count + retrograde, exact house
  structure/count/order, moon-phase missing/non-True as failure, never
  tracebacks, and records an engine proof (fail-closed swieph by
  default; allow-moshier is an explicit test-only flag). audit_today
  resolves the oracle interpreter (sidecar venv locally, the swisseph-
  capable current interpreter in CI) and forwards AUDIT_EPHEMERIS_PATH;
  the artifact-acceptance job extracts the baked bundle from the exact
  sidecar container and verifies artifact_id + manifest sha256 against
  /v1/health before the freeze runs. The standalone wave script now
  passes the production current_location + WHOLE_SIGN house system, so
  17 carries exactly the canonical 143 ordered ids of
  16_activation_layer. The canonical package was regenerated with the
  oracle on the pinned bundle (swieph=true, flags=258); provenance
  coherence asserts the exact full SHAs; freeze ×2 stays byte-clean on
  the final commit. GitHub exact-SHA run stays PENDING.
- **P1-2 fourth-review hardening (2026-07-22, local):** three more
  proven gaps closed. (a) The engine summary persisted the absolute
  runner ephemeris path, which would have made the exact-SHA freeze
  dirty on any other runner; it now records only a stable source marker
  (argument/env/default) — proven byte-clean across two different
  bundle paths on the same commit. (b) contract_diff is JSON-type-strict
  (false != 0, true != 1) and the ACTUAL payload v2 block is validated
  against the public TodayV2Block (extra=forbid) — ValidationError is
  the diagnostic failure payload_v2_contract_invalid; directed
  mutations: dominanceCapped false->0, activationEvidence.active
  true->1, v2-root extra key. (c) Astronomy retrograde compares with
  exact boolean type; wrong container shapes (day_chart /
  transit_planets / houses / facts) are normalized to empty structures
  — summary written, rc=1, no traceback (directed tests); swieph
  engine_pass requires FLG_SWIEPH on every calc AND zero FLG_MOSEPH;
  the fail-closed engine test uses an explicit empty ephe dir. The
  wave-17 coherence test now asserts exact full-layer equality vs the
  canonical HTTP layer (except _audit_meta, whose current_location is
  asserted exactly). GitHub exact-SHA run stays PENDING.
- **P1-2 second-review hardening (2026-07-22, local):** an independent
  mutation sweep showed 9 further probes passing rc=0 (topFlags summary,
  normalizedScore, contribution before, activationEvidence strength,
  sphereScores order, dayChart aspect orb, debug longitude/sign, house
  cusp). The EXISTING oracles were strengthened fail-closed, no new
  harness: downstream now compares the full public `SphereScoreV2`
  (all fields + ordered full-field contributions), full ordered topFlags
  objects, top-level sphereScores value/rank/order vs the selected
  recompute, and ordered activationEvidence entries vs the validated
  layer dump (missing AND extra ids fail); the astronomy oracle gained a
  FINAL_CHART_PROOF block (final dayChart transit longitude/sign/motion
  and serialized house number/order/cusp/sign vs the independent Swiss
  result, aggregated into the exit code). The downstream audit also
  verifies dayChart.aspects as the exact ordered day-signals projection
  (production _build_day_chart rules) — the last of the 9 probes
  (aspects[0].orb) now exits non-zero with its own failure kind. Every
  listed mutation now exits non-zero with its own failure kind. The canonical package was
  regenerated as ONE generation via the pinned image
  `solarsage-sidecar-readiness:62b756a` (health: engine=swieph,
  fallback=false, release_sha=62b756a6…, calculation_version
  ss-calc-1.2.0, ephemeris se-stellium-1800-2399-20260721, manifest
  768d5fc9…) on an ephemeral DB; the accidentally committed `live/`
  duplicate was removed and replaced by compact
  `provenance_sidecar.json`; the stale older-sidecar wave artifacts
  17-21 and V2 scoring artifacts 22-23 were regenerated with the same
  proven contour. Frozen `artifact_source.json` carries no dynamic git
  HEAD (self-reference fixed): `audit-day-freeze` ×2 on the final
  commit leaves `git status/diff -- artifacts/` clean. Coherence tests
  assert all downstream checked flags true, exactly 24 pinned unmapped
  warnings, scoring-oracle all-pass, the astronomy final_* keys, and
  the pinned sidecar provenance identity. P1-2 is locally complete on
  the exact same artifact; the GitHub exact-SHA run stays PENDING.

### P1-2. Independent-from-pipeline calculation verification

- **Goal:** the calculation path is verified independently of the product
  pipeline — NOT by an alternative source to Swiss Ephemeris, but by the
  existing audit tooling recomputing and comparing on the same engine.
- **Design (owner decision 2026-07-20):** P1-2 is NOT an external
  ephemeris source and needs NO owner-approved source or tolerances.
  Verification runs through the existing `make audit-day-live` /
  `make audit-day-freeze` flow (`scripts/audit_today.py`, unmodified),
  which invokes both oracle scripts as fail-closed subprocesses:
  - `scripts/audit_astronomy_oracle.py` — recomputes and compares transit
    longitudes, retrograde flags, moon phase and house placements against
    the pipeline output; exits non-zero on any mismatch
    (`longitude_pass` / `retrograde_flag_pass` / `house_pass` /
    `moon_phase`).
  - `scripts/audit_scoring_oracle.py` — recomputes and compares
    `day_status`, `sphere_scores` and `top_signals` against the
    production scoring; exits non-zero on any mismatch.
  - `scripts/audit_downstream_v2.py` (wired into `audit_today.py` after
    the oracles, `check=True`) — fail-closed verifies the FINAL selected
    payload against the independently recomputed V2: `dayStatus`, every
    `scoreBreakdown` sphere (numeric fields + contributions), sphere
    sorting, and `topFlags` in exact order; activation evidence set equals
    the sidecar set (lost/extra ids are errors).
- **Provenance (2026-07-22):** the baseline was rebuilt through the pinned
  local image `solarsage-sidecar-readiness:62b756a` (OCI revision
  `62b756a6559ba4a0f501fffe56dca51eb52872b2`), run as a temporary
  container on 127.0.0.1:18099 with
  `SOLARSAGE_EPHEMERIS_ROOT=/opt/solarsage-ephemeris/bundle`; health proof
  `engine=swieph`, `fallback=false`,
  `calculation_version=ss-calc-1.2.0`,
  `ephemeris_artifact_id=se-stellium-1800-2399-20260721`,
  `ephemeris_manifest_sha256=768d5fc920c762028437ad0bff43013c800ff027911a2dc02cb7d45d7ea9db59`.
  An earlier baseline used the already-running dev sidecar (no identity) —
  that provenance was false and was discarded. The frozen tracked
  `artifact_source.json` is deterministic (`git_head: null`; only the live
  run keeps the runtime SHA), so `audit-day-freeze` no longer breaks
  `git diff --exit-code` on a new commit.
- **Package coherence:** the committed `artifacts/audit/2026-07-08` set is
  ONE generation (one synthetic audit user, one date) across
  `00_input_profile`, `11_final_today_payload`, `14_claims_audit.md`,
  `15_audit_summary.md`, `16_activation_layer.json` and `downstream/`;
  `test_audit_artifact_coherence.py` fails on any mix.
- **Artifacts:** `13_astronomy_oracle_summary.json`,
  `12_scoring_oracle_comparison.json` (root; debug copy
  `scoring_oracle_comparison.json`), `trace_map.json` (debug),
  `final_today_payload.json` (debug), root `11_final_today_payload.json`,
  `downstream/12_downstream_audit_summary.json`.
- **Truth today:** the current oracle artifacts are ALREADY fail-closed
  on mismatch — both scripts `sys.exit(1)` on any failed comparison and
  `audit_today.py` invokes them with `check=True`, so a houses / scoring /
  top_signals mismatch returns non-zero and fails the audit gate. The
  downstream audit exits 1 on any payload-vs-recompute mismatch. No new
  harness and no `make audit-day` rewrite.
- **Status: LOCALLY COMPLETE (2026-07-22).** Combined audit (astronomy +
  scoring oracles + downstream payload check) is green on the exact same
  artifact, byte-stable across `audit-day-freeze` ×2 on the final commit;
  the exact-SHA proof in the GitHub acceptance job is pending with P1-1.
- **Pass/fail:** both oracle summaries and the downstream summary green on
  the exact release SHA in artifact acceptance; any mismatch blocks.
  artifact acceptance; any mismatch blocks.

### P1-3. Same-payload UI proof

- **Goal:** the SAME `11_final_today_payload` audit artifact renders
  correctly — calculation truth and display truth proven together.
- **Steps:** feed the payload artifact into the existing Playwright route
  fixture (mock-visual harness); validate schema + key DOM states + one
  screenshot per key state; reuse, no new harness.
- **Gate contract (fixed 2026-07-22):** the discriminator is
  `meta.payloadVersion` (`today.v2`/`today.v2.1`) with the coherent
  `frontendPayloadVersion` pair and a non-null v2 block; final validation
  is `TodayPayloadWireSchema`. `meta.schemaVersion` is canonically
  `today/v1` for every series and is never used. The root artifact is the
  real API wire payload (camelCase `by_alias=True`, normalized
  `generatedAt`/`cached`); astronomy/scoring oracles consume the derived
  internal snake_case debug dump.
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

- **Status: PARTIAL (2026-07-20).** Strict real-HMAC release suite truth:
  8 specs / 12 chromium tests, no route interception, workflow runs them
  with `--fail-on-flaky-tests`; first CLEAN strict green is proven (run
  29758437120 below). Implemented locally: public CityPicker DOM
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
  `E2E_TELEGRAM_BOT_TOKEN` / `E2E_OPENROUTER_API_KEY` /
  `E2E_GEONAMES_USERNAME` secrets — missing
  secrets are a fail-closed blocker) with a `release` suite of exactly the
  real-HMAC no-interception specs (onboarding-real, today, calendar,
  cross-feature-navigation, profile-city-checkin, readings-horary,
  natal-report, referral-deeplink); `deploy-production.yml`
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
  `NATAL_REPORT_ENABLED=true`, the production flag stays off).
  /chat is an INTENTIONAL locked placeholder (historical commit 4449768;
  the route does not render ChatScreen): the earlier real-chat spec was
  invalid and has been REMOVED from the repo and the release suite — chat
  is a product follow-up, NOT implemented; the honest locked state is
  covered by `locked-features.spec.ts`.
  **Candidate run 29701833426 (2026-07-19, completed FAILURE: 6 passed /
  5 failed).** GeoNames wiring proven (`/api/geo/autocomplete` 200).
  Causes identified and fixed in the candidate follow-up: GeoNames latency
  2.8–5.1s (suggestion waits raised to 15s, no retries/mocks);
  `searchJSON` now uses `style=FULL`
  with inline `timezone.timeZoneId` (per-item `timezoneJSON` N+1 removed,
  `_fetch_timezone` kept as fallback; narrow backend test added); fresh
  users intentionally have NO access ledger — Today is locked
  (`today.spec.ts` now proves the honest locked preview
  `data-state=locked` + access-card + payload preview, full-day cards
  absent) and horary weekly credit is absent; the referral deep-link flow
  grants real 14-day access — `referral-deeplink.spec.ts` now also proves
  the unlocked full day (`data-state=ready` + `day-summary-card` +
  `concrete-day-advice`) and `readings-horary.spec.ts` grants access via
  the new fixtures helper `grantReferralAccess` (real deep-link claim, no
  direct POST/DB seed) before quota/unlocked + submit→answer→read-back→
  history. Stale navigation fixed: calendar day cell → public CTA
  «Открыть день/Открыть превью» → canonical `/day/YYYY-MM-DD`;
  cross-feature uses `a[href^="/day/"]` + dated URL regex.

  **Candidate timeline (strict real-HMAC release suite):**
  - 29701833426 — FAILURE: 6 passed / 5 failed (GeoNames wiring proven 200;
    causes fixed in the follow-up above).
  - 29702970139 — 11 passed / 1 failed: horary create `MissingGreenlet`
    (lazy `spent_credit` serialization in a fresh request session) — fixed
    by the eager-loaded create path (`881f108`, directed fresh-session
    regression).
  - 29749139004 — GitHub success but results 9 expected + 3 flaky:
    false-green by design closed — release suite now runs with
    `--fail-on-flaky-tests` (`b4c00b5`).
  - 29750842382 — strict failure: onboarding wait, real `/api/day` took
    32.8s — day-state timeouts widened to observed latency (`86bec7c`).
  - 29751885436 — strict failure: malformed LLM neutral testimony without
    `weight` persisted as unreadable answered + frontend polling storm —
    fixed (`812f8c6`): exact `HoraryBlock` contract boundary with retry and
    no raw cause in errors, single owned polling chain.
  - **29758437120 (SHA `812f8c6`) — FIRST CLEAN strict green:** 12
    expected, 0 unexpected, 0 flaky, all retry=0, duration 309637ms,
    horary first pass 30.544s.
    https://github.com/basilivanov/solarsage-astro/actions/runs/29758437120
  Third slice (2026-07-19, local): referral deep-link auto-claim —
  `e2e/referral-deeplink.spec.ts` (referrer invite code via real GET
  /api/referral; isolated second user via new fixtures export
  `createAuthedUserPage` — same run-salted ids and cleanup ledger, no
  duplicated crypto; invitee opened with `?tgWebAppStartParam=<code>` so the
  real auth flow claims; GET /api/access `referralDaysLeft >= 13`;
  `totalInvited=1`; repeated deep-link open idempotent, no manual API
  mutation). Release suite now includes all of these specs.
  Remaining P1-6 items: chat product follow-up (intentional locked
  placeholder), the external /start Telegram-client ingress path (owner
  ingress, P0-3), and the payment implementation + provider sandbox
  (product work, not a test gap).
  **Stop rule (unchanged, not release-ready):** because this docs commit
  creates a new exact SHA, TWO consecutive strict candidate runs on the
  final docs SHA are still PENDING and will be recorded in the handoff —
  without a next docs commit. All other blockers stay open: P0-2 licensed
  bundle/identity production proof, P0-3 external Telegram ingress, P0-4
  host apply/deploy-workflow proof, P1-2 exact-SHA oracle proof,
  P1-3 GitHub acceptance run on the exact SHA, P1-5 PR diff-cover acceptance,
  chat/payments/provider sandbox follow-ups, manual launch gates.
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
  source of truth); E2E service images unchanged. **Deferred blocker
  (2026-07-19, investigated):** Python dependency lock→constraints export is
  NOT a small reproducible change: `apps/api/poetry.lock` is STALE
  (`poetry check --lock` reports pyproject changed significantly since the
  lock was generated), `apps/solarsage` has NO lock file at all, and no
  build path consumes any lock (CI and both Dockerfiles install editable
  packages via pip from pyproject `>=` ranges). Implementing means
  regenerating both locks, adding a supported export step (poetry export or
  uv — owner tool decision), changing both Dockerfiles to install with
  constraints, and adding a CI freshness gate. Owner action: pick the tool
  and regenerate the locks first; until then the `apps/api/poetry.lock` is
  evidence-only, not a build input.
- Branch protection/rulesets when billing allows.
- Stale docs refresh (`e2e/README.md` systemd-era content), harness dedup,
  stale astro ssh config block on apex.
  **Status (2026-07-19, partial):** `e2e/README.md` systemd-era claims
  replaced — the E2E workflow stack is documented as ephemeral
  (Postgres/Redis services + uvicorn sidecar/API + production Next build)
  and production systemd units are never touched. **Blocked external:** the
  stale ssh config block lives on the apex HOST (`~/.ssh/config`), not in
  this repo — host-side manual cleanup only. Harness dedup: no dead
  in-repo references found — both preview launchers are live and
  referenced (`scripts/preview-v2-real.mjs` = real-backend local preview,
  `e2e/mock-visual/start-v2-preview.mjs` = mock preview used by CI
  workflows); no second harness was created.
- ANTHROPIC_API_KEY empty-default documented (harmless while
  LLM_PROVIDER=openrouter). **Status: DONE (2026-07-19)** —
  `docs/PRODUCTION_RUNBOOK.md` §2 states the key is required only with
  `LLM_PROVIDER=anthropic` and the empty default is valid on the canonical
  openrouter path; runtime config untouched (`config.py` keeps the empty
  default).

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
