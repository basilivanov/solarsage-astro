# 190 — Production Readiness Implementation Plan

Date: 2026-07-19. PLAN ONLY — no implementation, no commit/push. Sources:
AGENTS.md, 189 (R1-corrected audit), 80 (accepted ephemeris gate design),
Makefile, `scripts/audit_today.py`, `scripts/deploy/prod-orchestrator.sh`,
`.github/workflows/{ci,e2e,deploy-production}.yml`, e2e/mock READMEs.

**Status legend:** ✅ confirmed done (with evidence) · 🔲 not implemented ·
🚦 launch criterion (must be green before public exposure)

**Current truth:** release `72871dbd` live with green liveness; NOT
production-ready — Moshier math (empty `/opt/sweph/ephe`), Telegram webhook
ingress blocked (pending=2), deployed with red CI, no exact-SHA gate.

---

## Phase P0 — blocking (before any public exposure)

### P0-1. Exact-SHA release-quality gate in the ONE deploy workflow

- **Goal:** red code can never reach build/deploy again.
- **Design (from 189 §10, no duplicate gates):** single authoritative manual
  `Deploy Production` workflow for the exact SHA:
  1. `source-quality` (BLOCKING): checkout exact SHA; pytest apps/api +
     apps/solarsage, vitest, eslint/tsc, `check_audit_golden.py`, contracts.
  2. `build` (existing): build/push immutable images ONCE.
  3. `artifact-acceptance` (BLOCKING, runs against those exact images —
     details in P1-1/P1-3; an initial compose-up + health implementation is
     only an interim step, never the release criterion). **The release gate
     MUST block deploy/tag until ALL of: full `make audit-day-freeze` on the
     exact SHA + independent oracle (P1-2) + same-payload
     API/DOM/screenshot proof (P1-3) pass.**
  4. `deploy` (existing forced command), needs 1–3.
  5. `functional-smoke` → rollback authority on failure.
  6. `tag` (immutable, after smoke only).
- **Files:** `.github/workflows/deploy-production.yml` (add jobs/needs);
  reuse `ci.yml` commands verbatim.
- **Companion CI fixes so the gate can pass:** run sidecar in backend CI
  (service container/launch step with production-like ephemeris — fixes the
  backend 64 errors and the sidecar health 503 in CI); replace
  tracked `.antigravitycli` symlink (delete it from the repo) or scope the
  secret guard to skip symlinks WITHOUT reading their targets (never copy
  the target's secret content into the repo).
- **Responsible:** Kimi implements; owner approves PR.
- **Blockers:** none (private-plan branch protection irrelevant — gate lives
  in the workflow itself).
- **Artifacts:** workflow run evidence per job; pass = all jobs green for
  the exact SHA; fail = no build, no deploy.

### P0-2. Swiss Ephemeris artifact + exact identity (reuse doc 80 design)

- **Goal:** production calculates with real Swiss files and PROVES it at
  host/deploy/runtime layers; identity drift impossible.
- **Steps (per doc 80):**
  1. Owner/secret-owner supplies licensed/redistributable artifact bundle
     (sepl_18.se1, semo_18.se1, …) with provenance; create
     `/opt/solarsage-ephemeris/releases/<artifact-id>/{ephe/,manifest.json,
     manifest.sha256}` + atomic `current` symlink (root-owned immutable).
  2. Offline installer (root-only check/apply): validates tree/manifest/
     hash, runs offline oracle requiring returned FLG_SWIEPH, atomic
     install + pointer flip, preserves previous for rollback. (Doc 80 §
     "Offline installer".)
  3. Single runtime owner module in sidecar: resolves `current`, verifies
     manifest identity, `set_ephe_path` once, wraps every calc_ut checking
     return flags, fatal on fallback under APP_ENV=production.
  4. Health schema v2: expose `ephemeris_artifact_id`,
     `ephemeris_manifest_sha256`, `engine=swieph`, `pyswisseph_version`,
     `calculation_version` (canonical ss-calc-1.2.0), probe
     flags/fallback=false; orchestrator `prove_health` compares EXACT
     expected values (not nonempty).
  5. Compose/host-prepare: mount artifact read-only into sidecar container;
     remove hardcoded `/opt/sweph/ephe` writes; CI/E2E uses pinned test
     artifact or explicit Moshier-only label (never counts as prod proof).
- **Files:** `apps/solarsage/solarsage/core/health.py`, new
  `apps/solarsage/solarsage/core/ephemeris_runtime.py`, sidecar service paths
  (calculator/returns/eclipses/progressions), `apps/solarsage/Dockerfile`,
  `infra/production/docker-compose.app.yml`, `scripts/deploy/*` (host-prepare
  verify), `scripts/deploy/prod-orchestrator.sh` (prove_health exact match).
- **Commands:** installer `--check/--apply` on apex; orchestrator preflight;
  deploy health proof.
- **Responsible:** secret-owner (artifact bytes + provenance) → operator
  (install) → Kimi (code/wiring).
- **Blockers:** artifact licensing/provenance decision (owner).
- **Artifacts:** manifest+sha256, installer log, health v2 JSON,
  acceptance matrix (doc 80 §"Acceptance matrix") all-pass.
- **Pass/fail:** retflag SWIEPH in all probes incl. range boundaries;
  Moshier → fatal everywhere; exact identity in orchestrator status.

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
- **Design:** backward-compatible expand/contract only; pre-migration
  backup (already in `migrate <sha>`); snapshot + `alembic current=head`
  evidence before app switch; migration result recorded; no blind
  auto-migrate in the workflow; rollback of app code never implies schema
  rollback.
- **Files:** runbook §5, `deploy-production.yml` (acceptance step runs
  `migrate <sha>` explicitly when the release carries new revisions).
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

- **Goal:** every user-facing capability has real-path evidence.
- **Steps:** add specs for readings CRUD, horary submit/view, natal
  generate/view, chat, checkin, paywall/referral claim, profile edit city
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

### Stop rule P1

All P1 items green on two consecutive candidate runs. Safe stop: evidence
bundle (coverage, audit hashes, E2E reports, baselines) + owner review.

---

## Phase P2 — hardening (post-launch ok)

- Docker base images pinned by digest; Python deps locked (P2).
- Branch protection/rulesets when billing allows.
- Stale docs refresh (`e2e/README.md` systemd-era content), harness dedup,
  stale astro ssh config block on apex.
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
