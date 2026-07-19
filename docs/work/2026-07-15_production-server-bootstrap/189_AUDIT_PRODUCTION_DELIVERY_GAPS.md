# 189 — Production delivery gaps: evidence-based audit + minimal architecture

Date: 2026-07-19. Status: R1-corrected (ARCH REVIEW R1 applied). Read-only
audit; no implementation. Current live release `72871dbd…`: green
liveness/release_sha ×3 + HTTPS — but NOT production-readiness (calculations
run on Moshier, Telegram webhook ingress is blocked, and the release was
deployed with failing CI; details below).

---

## 1. Product inventory (from actual code)

**Frontend routes** (`app/(grace)/`): `/` (redirect), `/day/[date]`, `/today`
(legacy redirect), `/calendar`, `/profile`, `/readings`, `/readings/horary`,
`/readings/horary/[id]`, `/readings/natal`, `/readings/natal/[id]`,
`/readings/natal/generating`, `/onboarding`, `/chat`, `/checkin`, `/reset`,
plus non-product `/debug*`, `/test-hook`.

**API routers** (`apps/api/app/api/`, 20 files): access, auth, calendar,
chat, checkin, day, debug, geo, health, health_extended, horary, _log,
metrics, microcopy, natal, payment, profile, referral, telegram_webhook.

**Capability matrix** (evidence level per capability):

| Capability | Unit/Component | API integration | Real no-intercept E2E | Live prod smoke | Evidence gap |
|---|---|---|---|---|---|
| Auth (Telegram HMAC) | conftest HMAC paths | auth tests | onboarding-real | HMAC smoke ✓ (2026-07-19) | — |
| Onboarding + city | CityPicker 3/3 | geo tests | onboarding-real | geo cyr/lat ✓ | — |
| Today/day | useDay, day-page, WeekStrip, overlap gather | day tests | today.spec (early return at onboarding — false-green) | health ✓ | real-path incomplete |
| Calendar | calendar comps | calendar API | calendar.spec | — | no live smoke |
| Profile | profile comps | profile API | — | — | — |
| Readings | readings comps | readings API | — | — | — |
| Horary | horary-time-confirm | horary API | — | — | — |
| Natal | natal comps | natal API | — | — | — |
| Chat | chat comps | chat API | — | — | — |
| Checkin | checkin comps | checkin API | — | — | — |
| Access/referral/paywall | referral 9/9, share 6/6 | referral live ✓ | — | referral URL ✓ | paywall flow untested E2E |
| Payment/webhook | payment tests | yookassa guard tests | — | — | idempotency + sandbox flow unproven (P1) |
| Geo | cities 9/9 | geonames tests | — | cyr/lat ✓ | — |
| Telegram /start | webhook 11, sync 16, setup 7 | Bot API read-backs ✓ | — | synthetic POST ✓ + read-backs ✓; REAL Telegram delivery FAILS (pending=2) | ingress P0 |

## 2. Test/workflow inventory — authoritative numbers

**Authoritative GitHub CI run (owner-confirmed):**
- backend: 1430 passed, 4 failed, 3 skipped, **64 errors** — most errors
  because backend CI does not run the sidecar on 18091 while
  pipeline_golden/invariants/llm_context tests call it.
- sidecar: 200 passed, 1 failed — health 503 (missing production-like
  ephemeris path in CI).
- frontend: 1098 passed, 1 failed — git-tracked `.antigravitycli/*.json`
  is a symlink (mode 120000) to `~/.gemini/config/...` (absent on runner)
  → secret guard ENOENT.
- contracts: green.
- Local coverage run (separate): API 1496 passed, 1 failed (local alembic
  subprocess), 4 skipped.
- PR #9 was merged and `72871dbd` deployed with this red CI (deploy
  workflow has no exact-SHA quality gate). Any earlier "1474/1095 all
  green" summary referred to local pre-merge runs and is superseded by the
  authoritative GitHub run above.

**E2E interception facts (corrected):** among `e2e/*.spec.ts`, only
`edge-cases.spec.ts` actually calls `page.route`;
`real-v2-preview.spec.ts` is explicitly "strict no interception"
(comment mention only). Real E2E auth uses genuine Telegram HMAC via
`scripts/generate-telegram-test-initdata.py`. **Cleanup is NOT automated:**
`deriveTelegramUserId` (e2e/fixtures.ts:44) is deterministic and repeats
between runs; fixtures do not delete DB users.

**Trigger inventory:** ci.yml — PR + manual; deploy-production.yml — manual
(no quality job); e2e.yml — manual only (smoke|full); visual-regression.yml
— manual only; source-readiness.yml — manual only.

**Known spec false-greens (owner-confirmed):** today.spec returns early at
onboarding; cross-feature-navigation uses conditional clicks and ends with
tautological expect(true); e2e/README claims nonexistent auto triggers and
references missing specs.

## 3. Coverage — measured (owner's local run)

- API: 1496 passed/1 failed/4 skipped; TOTAL 11264 stmts/1730 miss,
  3834 branches/548 partial → combined 82%. Critical zeros:
  `services/llm/{client,horary,prompts,russian,service}.py`,
  `yesterday_service.py` 0%; health_extended 16%, metrics/debug 36%,
  referral API 43%, chat_quota 42%, GeoNames ~53%, chat 52–67%, auth 62%.
- Sidecar: TOTAL 2002 stmts/158 miss, 614 branches/102 partial → 90%, but
  `services/calculator.py` 0%, core/health 68%, returns 78%.
- Frontend: not measurable today (no @vitest/coverage-v8/istanbul, no
  config/threshold).
- Policy (no implementation here): per-critical-file thresholds over
  aggregate; changed-code ≥80%; 100% of critical capabilities by evidence,
  not by line %.

## 4. Mock baseline

`e2e/mock-visual/`: 7 specs with a route-interception harness feeding
**deterministic mocked payloads** (not masking of live dynamics).
`toHaveScreenshot` only in `day-v2.spec.ts`; 6 snapshot PNGs total =
3 Today states × chromium/mobile. Other mock specs (calendar/profile/
readings/horary/natal) are structural checks, not visual baselines.
Snapshot policy fail-closed (`updateSnapshots:none`). Suite manual-only.

## 5. Real/mixed E2E

Exists (most with genuine Telegram HMAC via
`scripts/generate-telegram-test-initdata.py`): onboarding-real, today,
calendar, cross-feature-navigation, locked-features, hydration-guard,
dev-* fixtures. Mixed: `edge-cases.spec.ts` uses one `page.route`
interception; `real-v2-preview.spec.ts` has no interception but uses
`/api/auth/dev` instead of Telegram HMAC injection (explicit, not real
Telegram auth).
Missing real-path: readings, horary, natal, chat, checkin, paywall/referral
claim, /start→web_app, profile edit city change, payment webhook.
Cleanup gap (P1): deterministic user ids + no DB user deletion → reruns
collide with prior state.

## 6. External dependencies (corrected)

| Dep | Deterministic contract | Controlled integration | Live state (honest) |
|---|---|---|---|
| Telegram Bot/WebApp | webhook/sync/setup suites (34) | identity-gated tooling | `getWebhookInfo` = **FAIL**: pending=2, `last_error_message="Connection timed out"`, last_error_date=1784446093 (2026-07-19T07:28:13Z). Synthetic webhook POST + Bot API read-backs prove the endpoint/config — they are NOT proof of real Telegram delivery, which currently fails. |
| GeoNames | service tests | patched username tests | live cyr/lat smoke ✓ (after P0 fix) |
| OpenRouter/LLM | llm tests, overlap gather | manual E2E secret exists | flaky live integration only — never a math gate; LLM asserted structurally |
| GHCR/docker | orchestrator harness 29 | manifest inspect ✓ | deploy health ✓ |
| Restic/SFTP | backup units | — | offsite backup ✓; restore rehearsal NEVER executed |

## 7. Golden calculations — truth status

Existing suites: `apps/solarsage/tests` (parity frozen JSON, profections,
firdar, eclipse, lunar return, progressions, ephemeris retrograde);
`apps/api/tests` (pipeline golden, basil/zhanna goldens, patterns canon);
CI `scripts/check_audit_golden.py` — narrow offline scoring-snapshot subset
(3 tests/0.04s measured by owner).

**None of these is an independent correctness oracle (owner-verified):**
- `test_parity.py` reads frozen JSON vs hardcoded values; the current
  sidecar calculation is never invoked.
- `test_natal_golden_zhanna.py` self-declares "NOT an astrology correctness
  proof" and mocks the sidecar.
- `test_pipeline_golden.py` generates expectations with the same sidecar +
  same normalization/scoring, sphere threshold = 50% of its own output —
  self-referential.
- `scripts/audit_astronomy_oracle.py` computes with the same swisseph and
  does NOT check returned engine flags — it can compare Moshier against
  Moshier.
- Production currently runs **Moshier**: apex `/opt/sweph/ephe` has 0 files;
  probe in the live sidecar returned `retflag=260, uses_moshier=True,
  uses_swiss_files=False`. `core/health.py` checks `os.path.exists(dir)`
  only; orchestrator `prove_health` checks nonempty strings only.
- **Identity drift (P0):** live sidecar health reports `version=dev` and
  `calculation_version=ss-1.0.0` while the shared canonical version is
  `ss-calc-1.2.0`; orchestrator verifies only nonempty values.

**Accepted design to reuse (no new bicycle):**
`docs/work/2026-07-15_production-server-bootstrap/80_AUDIT_AND_ARCH_EPHEMERIS_PRODUCTION_GATE.md`
— pinned Swiss Ephemeris artifact with manifest+hash+provenance,
engine-flag-verifying health, exact-identity deploy proof. An independent
reference must be neither product code nor the same runtime installation;
exact sources and tolerances are subject to owner/domain approval — none
are invented here. Golden cases must additionally record engine flag,
artifact version/hash, UTC and tzdata version.

## 8. Production delivery — status

Proven: immutable per-SHA images with OCI labels; digest-pinned activation;
required-env fail-closed; pre-deploy backup + offsite restic; release
record active/previous; activation-health rollback path. Live smokes exist
but must be read precisely: synthetic webhook POST/secret-gate and Bot API
read-backs prove endpoint/config — they are NOT proof of real Telegram
delivery (still FAIL, pending=2); geo/referral/HMAC-auth smokes are real.
Gaps: **orchestrator auto-rollback covers ONLY activation health failure —
a failed post-deploy functional smoke does NOT roll back today**; restore
is isolated-rehearsal-only (never executed on a real dump) and a real
production restore has no accepted procedure; alembic head not verified at
deploy; workflow deploy never runs migrations (P0 for any release that
needs one); Docker base images unpinned + loose pyproject ranges (P2);
no canonical post-deploy smoke command.

## 9. Gaps by priority (corrected)

**P0 (before any public exposure / next release):**
1. Exact-SHA release-quality gate inside the deploy workflow (red CI was
   deployed) — §10 single-workflow design.
2. Swiss Ephemeris artifact + exact identity (Moshier in prod; version
   drift `dev`/`ss-1.0.0` vs canonical `ss-calc-1.2.0`) — reuse doc 80.
3. Telegram webhook ingress blocked at provider level — real /start not
   delivered (owner decision: unblock or relay).
4. Migration safety: forward DB migrations are NOT a code rollback — any
   release requiring migrations must use backward-compatible
   expand/contract changes, take a snapshot + verify `current=head` before
   switching the app, and record the migration result. The workflow never
   runs `migrate` today; no blind auto-migrate, no app switch before proof.

**Launch gates (manual, required before launch announcement):**
5. BotFather: menu label «Мой день ✨», avatar.
6. Real restore rehearsal executed once on a real dump.

**P1 (before public launch):** coverage tooling + critical-file thresholds;
full real E2E for missing capabilities + automated cleanup; independent
golden reference per §7; visual baselines beyond Today; e2e false-green
spec rewrites + README; post-deploy smoke command; payment webhook
idempotency/sandbox proof; alembic head evidence in deploy;
`make audit-golden` honest labeling (3-test subset, not an audit).

**P2 (hardening):** branch protection (plan-blocked 403), env reviewer,
Docker base pinning + dependency locking, harness dedup, stale ssh config
block on apex.

## 10. Gate architecture — ONE authoritative manual workflow

Do NOT duplicate an automatic release-candidate and a release-quality job.
Proposed shape of the single authoritative **Deploy Production** workflow
(exact SHA, manual trigger):

1. **Source quality** (BLOCKING dependency of everything below): pytest
   api+solarsage, vitest, eslint/tsc, golden subset, contracts.
2. **Build/push images ONCE** for the exact SHA (existing job).
3. **Artifact acceptance** (new, blocking; runs against THOSE exact
   images, not the source tree): Postgres + migrations applied, pinned
   ephemeris artifact (doc 80), api/sidecar/frontend up; real no-intercept
   E2E selected by explicit tags; mock/error/visual suites reported
   separately; seeded `audit-day-freeze` (deterministic only after seeded
   fixed DB/profile + pinned ephemeris/tzdata/exact image — frozen mode
   today still reads live DB/profile/engine) + independent oracle (§7) +
   same-payload UI proof (feed the `11_final_today_payload` artifact into
   the existing Playwright route fixture; validate schema + DOM +
   screenshot; no parallel harness).
4. **Production environment approval** (manual gate preserved).
5. **Deploy** via forced command (depends on step 3 success).
6. **Functional post-deploy smoke** (health ×3 + geo + webhook + front +
   referral): on failure the design must run inside rollback authority or
   explicitly invoke the recorded rollback — today no auto-rollback exists
   for this stage; no claim otherwise.
7. **Tag** only after smoke passes: annotated, immutable, never
   overwritten, collision-safe `prod-YYYYMMDDTHHMMSSZ-<short12sha>`.
   Tag is historical evidence; the current release source of truth remains
   the orchestrator's recorded active SHA; a rollback event either gets its
   own historical tag or is documented in the same evidence bundle.

PR CI stays fast/advisory while branch protection is plan-blocked.

## 11. Honest Definition of Done

No 100% mathematical guarantee exists, and today production math is not
even engine-proven (Moshier) nor delivery-proven (Telegram ingress) nor
gate-proven (red CI shipped). DoD is achieved only when: (a) critical
capabilities have real-path evidence; (b) calculations reproduce goldens
AND an owner-approved independent reference within owner-approved
tolerances, with engine flag + artifact + tzdata recorded; (c) deploys are
digest-pinned, health-proven, backed up, rollback-proven — including the
functional-smoke stage; (d) every gate runs and passes for the exact SHA
deployed; (e) every failure is fail-closed and reported, never bypassed.
