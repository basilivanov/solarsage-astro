# Stage 2.W7-R1 — correction of production full-access V2 proof

Date: 2026-07-13
Owner: coder in tmux astro:0.0
Reviewer: architect
Mode: production acceptance correction only

## 1. Why the previous W7 callback is rejected

The previous READY_STAGE_2_W7_PRODUCTION_ACCEPTANCE_REVIEW callback is not
accepted.

Authoritative evidence contradicts the callback:

- production-payload-proof.redacted.json contains accessState = preview;
- all four PNG files show the paywall/locked presentation;
- the PNG files do not visibly prove activation-evidence-card,
  concrete-day-advice, the 12-sphere navigator, or the three horizon cards;
- therefore the previous browser run did not prove the requested full V2 UI.

Do not reinterpret preview as full. Do not accept a passing reporter result when
the persisted payload and screenshots contradict it.

## 2. Goal

Produce a truthful public-production acceptance proof in which the established
synthetic Telegram identity receives temporary, reversible full entitlement
only for the duration of the proof.

The final proof must establish all of the following:

1. Public Telegram HMAC authentication is natural and returns 200.
2. GET /api/day/2026-07-08 returns access.state = full.
3. Payload versions are today.v2.1 / frontend 3 / content 10.
4. Backend horizons are exactly long, medium, fast.
5. Desktop and mobile render data-state = ready, not locked.
6. Desktop and mobile visibly render:
   - activation-evidence-card;
   - concrete-day-advice with exactly 12 sphere rows;
   - why-horizons from backend-horizons;
   - exactly three why-horizon cards;
   - long/medium/fast timing and actions;
   - sphere navigation focus/selected behavior.
7. No fixture, local preview, dev auth, route interception, HAR, mock, cookie
   seeding, or storage-state seeding participates.
8. The temporary access-ledger mutation is removed after the proof and the
   synthetic user's access-ledger snapshot is restored exactly.
9. Product code, contracts, environment, build, services, Git refs, and
   rollback assets remain unchanged.

## 3. Absolute restrictions

- Do not edit product code.
- Do not edit generated contracts.
- Do not edit .env or .env.production.
- Do not restart or reload sidecar, API, frontend, nginx, PostgreSQL, or Docker.
- Do not rebuild or swap .next-prod.
- Do not commit, push, merge, rebase, reset, checkout, or stash.
- Do not touch the five frozen untracked paths.
- Do not use fixture query parameters or dev fixture modules.
- Do not call /api/auth/dev.
- Do not use page.route, context.route, routeFromHAR, HAR, mock servers, 18092,
  addCookies, storageState, or manually seeded session cookies.
- Do not weaken, remove, skip, conditionalize, or replace any assertion in the
  canonical W7 Playwright specification.
- Do not fabricate or hand-write evidence JSON.
- Do not copy, inspect, or reference /tmp/dasha_natal in release evidence.
- Do not delete W6 rollback env, wheel, or old frontend dist.
- Do not claim success while a persisted screenshot shows the paywall.

Only one production mutation is permitted: one temporary AccessLedger row for
the established synthetic test identity, with exact before/after restoration.

## 4. Exact entry identity

Require:

- branch main;
- HEAD, origin/main and remote main:
  4d8f03b5c89da050790eaf7391e0b3e8baaa31c5;
- release root:
  /opt/solarsage-release/20260713T143406Z;
- retained wheel SHA-256:
  5aa85c71ec5497598b02ff003f55f4281625785ddeaead8c294c29cca427b147;
- sidecar PID 202964;
- API PID 203504;
- frontend PID 204066;
- nginx PID 1048;
- current BUILD_ID: HBrg3x9QiX5xEyK9-HCET;
- rollback BUILD_ID: 2NkqWdVYJ1tMwVYnkOtc7.

Before any access-ledger mutation, repeat Git, service, port, health, feature
flag, wheel, BUILD_ID, rollback and worktree checks from sections 3, 4 and 9 of
179_STAGE_2_W7_PRODUCTION_ACCEPTANCE_TZ.md.

Stop if any identity differs.

## 5. Preserve the rejected evidence

The current seven files are rejected evidence and must not be silently
overwritten.

Create:

  /opt/solarsage-release/20260713T143406Z/rejected-evidence/w7-preview

Move the current seven files from:

  /opt/solarsage-release/20260713T143406Z/evidence

into that rejected directory. Preserve owner, mode and timestamps.

Write a small mode-640 manifest beside them containing only:

- rejectionReason = access_preview_and_paywall;
- rejectedAt;
- filenames;
- SHA-256 values;
- no payload text, profile data, auth data or personal data.

After the move, the active evidence directory must be empty before the corrected
proof starts.

## 6. Reversible temporary full entitlement

Use only the established synthetic Telegram identity:

  tg_user_id = 999999999
  username = dev_user

Use only the API venv and ORM models. Do not run raw psql and do not print the
database URL, UUIDs, profile fields, cookies, bot token or initData.

Create root-private operational state under:

  /tmp/stage2-w7-r1

Requirements:

- directory root:root mode 700;
- files root:root mode 600;
- never copy these private files into release evidence;
- clean them after verified restoration.

Before mutation:

1. Locate the synthetic User by tg_user_id.
2. Require exactly one user and an onboarded profile.
3. Read all AccessLedger rows for that user ordered by stable fields.
4. Store their complete canonical JSON snapshot privately.
5. Print only:
   - before row count;
   - SHA-256 of the canonical private snapshot;
   - AccessService.can_access_day state for 2026-07-08.
6. The expected before state is preview. If it is already full, do not insert a
   row; continue using the existing entitlement and mark inserted = false.

If insertion is required, insert exactly one row:

- id: a newly generated UUID stored only in the private state file;
- user_id: the synthetic user's existing UUID;
- entry_type: referral_bonus;
- days_granted: 14;
- start_date: 2026-07-05;
- end_date: 2026-07-18.

After insertion require:

- exactly one new row relative to the private snapshot;
- AccessService.can_access_day for 2026-07-08 returns full;
- AccessService.get_summary for the current date returns trial/full access;
- no other user's rows changed.

The insertion, direct proof, browser proof and cleanup must be coordinated by
one fail-closed shell lifecycle with EXIT, INT and TERM cleanup traps.

Cleanup must:

1. Delete only the exact newly generated row ID when inserted = true.
2. Commit the deletion.
3. Re-read all synthetic-user AccessLedger rows.
4. Require the after canonical snapshot SHA-256 and row count to equal before.
5. Require AccessService.can_access_day for 2026-07-08 to equal the before
   state.
6. Remove the root-private operational files only after restoration proof.

If cleanup or snapshot restoration fails, stop immediately and report
RESTORATION_FAILED. Do not issue a READY callback.

## 7. Correct direct public HMAC payload proof

While full entitlement is active, rerun section 5 of
179_STAGE_2_W7_PRODUCTION_ACCEPTANCE_TZ.md without weakening it.

Additional hard requirements:

- payload.access.state must equal full;
- the script must fail if it equals preview or locked;
- do not persist reason, referralDaysLeft, subscriptionActive or accessUntil;
- evidence accessState must equal full;
- all long/medium/fast timing, actions, likely spheres and provenance checks
  must pass;
- auth/profile/day/logout/revoked statuses must be
  200/200/200/204/401.

Write a fresh mode-640:

  production-payload-proof.redacted.json

The file must use exactly the allowlisted structural keys from W7 section 5.

## 8. Canonical browser proof — no modified test

Create exactly:

  e2e/.stage2-w7-production-v2.spec.ts

Use apply_patch.

Its complete content must be byte-for-byte the canonical TypeScript block under
"Required complete content" in section 6 of
179_STAGE_2_W7_PRODUCTION_ACCEPTANCE_TZ.md.

Canonical identity:

- bytes: 10925;
- lines: 268;
- SHA-256:
  533b8b33700292122c02d0c8b7da90d30f4b8ccb0a2c90f75588fab6ddd966ba.

Before running, require the temporary spec to match all three values. A mismatch
is a hard failure. Do not edit the canonical block to make the test pass.

Repeat the structural forbidden-pattern scan from W7 section 6. The permitted
string assertion for /api/auth/dev must remain an assertion only.

Run exactly:

  E2E_BASE_URL=https://dev.astro.vasiliy-ivanov.ru
  RELEASE_EVIDENCE_DIR=/opt/solarsage-release/20260713T143406Z/evidence
  E2E_WORKERS=1
  pnpm exec playwright test e2e/.stage2-w7-production-v2.spec.ts
    --project=chromium
    --project=mobile

Require exactly two passed tests, zero retries, zero skipped, zero unexpected
and zero flaky.

The canonical spec already requires:

- payload.access.state = full;
- today-screen data-state = ready;
- backend why-horizons;
- three horizon cards;
- twelve sphere rows;
- semantic statuses;
- selected/focused sphere navigation;
- natural HMAC;
- no fixture/dev auth/interception/cookie seeding;
- zero console, page and API failures.

Delete the temporary spec with apply_patch after the run, pass or fail.

## 9. Evidence truth checks

Require exactly seven active files:

- production-payload-proof.redacted.json;
- production-chromium-network.redacted.json;
- production-mobile-network.redacted.json;
- production-chromium-day.png;
- production-mobile-day.png;
- production-chromium-why.png;
- production-mobile-why.png.

All must be astro:astro mode 640.

JSON requirements:

- payload accessState = full;
- versions today.v2.1 / 3 / 10;
- fixtureDependency = false;
- naturalTelegramAuth = true;
- cookieSeeded/authDev/fixture/interception = false;
- horizons long/medium/fast;
- sphereRows = 12;
- consoleErrors/pageErrors/apiFailures = 0;
- no auth/dev, fixture, dev-fixtures or 18092 request.

PNG truth requirements:

- day screenshots must not show the paywall text or lock-only presentation;
- day screenshots must visibly show full personalized V2 content;
- why screenshots must be locator screenshots of why-expanded, not a generic
  page screenshot;
- why screenshots must visibly show the backend three-horizon explanation;
- chromium and mobile screenshots must be nonempty and independently
  inspectable.

Do not infer PNG success from Playwright status alone. Inspect all four files
before the callback.

## 10. Final post-cleanup audit

After the browser logout and access-ledger restoration:

- prove the synthetic AccessLedger before/after count and hash are identical;
- prove the temporary access row is absent;
- prove the temporary Playwright spec is absent;
- prove no temporary Playwright process/window/listener remains;
- prove Git tracked worktree and index are clean;
- prove only the original five frozen untracked paths remain;
- prove exact main/ref equality;
- prove original PIDs/start timestamps remain active;
- prove 18091/8000/3002/5433 present;
- prove 3003/3010/8001/18092 absent;
- prove local/public health passes;
- prove feature flags remain true/true with dual default;
- prove .env and .env.production hashes are unchanged;
- prove wheel/build/rollback identities are unchanged;
- repeat safe journal/privacy counts from W7 section 8;
- keep rejected evidence and rollback assets retained.

Product tests do not need another full rerun because no product file may change.
The corrected canonical browser proof and exact runtime integrity audit are
mandatory.

## 11. Final callback and stop

Only after all requirements pass:

  READY_STAGE_2_W7_R1_FULL_ACCESS_PROOF_REVIEW
  deploy_sha: 4d8f03b5c89da050790eaf7391e0b3e8baaa31c5
  previous_w7_callback: REJECTED_PREVIEW_PAYWALL
  rejected_evidence: RETAINED_SEPARATELY
  access_before: PREVIEW_OR_EXISTING_FULL
  temporary_access_inserted: TRUE_OR_FALSE
  temporary_access_removed: TRUE_OR_NOT_REQUIRED
  access_ledger_before_after: EXACT_COUNT_HASH_MATCH
  direct_hmac: AUTH_200_PROFILE_200_DAY_200_LOGOUT_204_REVOKED_401
  payload_access: FULL
  payload_versions: TODAY_V2_1_FRONTEND_3_CONTENT_10
  horizons: LONG_MEDIUM_FAST
  canonical_spec_sha256: 533b8b33700292122c02d0c8b7da90d30f4b8ccb0a2c90f75588fab6ddd966ba
  canonical_spec_identity: 10925_BYTES_268_LINES
  browser_e2e: 2_PASS_ZERO_RETRY_SKIP_UNEXPECTED_FLAKY
  browser_state: READY_NOT_LOCKED
  v2_dom: ACTIVATION_12_SPHERES_3_HORIZONS_PASS
  browser_forbidden_dependencies: ZERO
  evidence_artifacts: 7_FULL_ACCESS_SAFE_EXTERNAL
  screenshots: FULL_V2_VISIBLE_PAYWALL_ABSENT
  services_pids: UNCHANGED_ACTIVE
  git_refs: EXACT_DEPLOY_SHA_CLEAN
  env_build_wheel_rollback: UNCHANGED_RETAINED
  journals_privacy: PASS
  temporary_spec_process_private_state: ABSENT
  goal_completion: AWAITING_ARCHITECT_INDEPENDENT_REVIEW

Then stop. Do not start another task and do not declare the overall goal
complete. Only the architect may accept this correction.
