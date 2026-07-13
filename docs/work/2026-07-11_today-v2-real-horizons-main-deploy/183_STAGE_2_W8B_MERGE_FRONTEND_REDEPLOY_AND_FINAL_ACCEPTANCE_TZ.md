# Stage 2.W8B — merge, frontend redeploy and final strict production acceptance

Date: 2026-07-13
Owner: coder in tmux astro:0.0
Reviewer: architect
Mode: authorized only after W8A architect acceptance

## 1. Goal

After architect acceptance of W8A:

1. merge the exact reviewed frontend fix into main;
2. run the canonical full gate matrix;
3. push main;
4. build and atomically deploy a new self-hosted frontend candidate;
5. keep backend, sidecar, database schema, contracts and environment unchanged;
6. prove public production emits no Vercel Analytics request or console error;
7. prove full-entitlement V2 through natural Telegram HMAC on desktop/mobile;
8. restore temporary synthetic access exactly;
9. retain all rollback assets;
10. stop for final architect completion audit.

## 2. Entry authorization

Do not start from this document alone.

Require an explicit architect message containing:

  ARCHITECT_REVIEW_W8A=PASS
  FEATURE_SHA=<exact reviewed SHA>
  CANONICAL_W7_SHA=<updated code-block SHA>

Require:

- feature branch and remote equal FEATURE_SHA;
- its parent/base is the deployed main
  4d8f03b5c89da050790eaf7391e0b3e8baaa31c5;
- reviewed tree contains only the accepted W8A files;
- production runs the W6B service PIDs (sidecar 202964, API 203504, nginx 1048)
  and the current frontend (PID 298359, start 2026-07-13 18:55:45 MSK, NRestarts 1
  due to W8A candidate cleanup) before frontend redeploy;
- current BUILD_ID is HBrg3x9QiX5xEyK9-HCET (W6B build unchanged);
- existing W6 rollback assets and rejected evidence are present.

## 3. Absolute restrictions

- No backend, sidecar, DB schema or contract changes.
- No .env or .env.production changes.
- No systemd unit or nginx changes.
- No API or sidecar restart.
- No manual uvicorn.
- No Vercel console-error filter.
- No route/HAR/mock/fixture/dev-auth/cookie seeding.
- No broad process kill: never use pkill -f, pkill, killall or process-name
  matching. Only exact systemd frontend stop/start for deployment; only exact
  tmux candidate window lifecycle for port 3010.
- No deletion of any rollback or rejected evidence.
- No force-push.
- No unrelated staging.
- No bypass of failed gates.

## 4. Audited merge to main

Fetch refs and prove exact identities.

Merge the reviewed branch into main with an explicit merge commit unless it is
an exact permitted fast-forward authorized by the architect.

Expected merge subject:

  merge: fix self-hosted analytics for final V2 acceptance

After merge require:

- main tree equals the reviewed feature tree;
- parent lineage is explicit;
- diff from prior main is exactly reviewed scope;
- tracked/index clean apart from the known docs state before commit;
- no frozen path staged.

## 5. Full merged-main gate matrix

Run from exact merged main:

  pnpm contracts:generate
  git diff --exit-code -- packages/contracts/openapi.json
    packages/contracts/_generated.ts
    packages/contracts/_generated.zod.ts
  pnpm contracts:check
  pnpm contracts:compat
  pnpm contracts:fixture:check
  PYTHONPATH=packages/py-contracts
    apps/api/.venv/bin/python -m pytest packages/py-contracts/tests/ -q

  npx vitest run
  pnpm typecheck
  pnpm guardrails:prod
  pnpm guardrails:contracts
  pnpm guardrails:frontend
  pnpm guardrails:secrets

  PYTHONPATH=apps/api
    apps/api/.venv/bin/python -m pytest apps/api/tests/ -q
  PYTHONPATH=apps/solarsage
    apps/solarsage/venv/bin/python -m pytest apps/solarsage/tests/ -q
  PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest
    apps/api/tests/test_today_preview_transport.py
    apps/api/tests/test_today_preview_access.py
    apps/api/tests/test_today_selection_context.py
    apps/api/tests/test_today_cache_v2_key.py
    -q
  apps/api/.venv/bin/python -m pip check
  apps/solarsage/venv/bin/python -m pip check

Require all green and record exact counts. The new Vitest count must include the
new W8A tests.

Contract generation must leave zero tracked diff.

## 6. Push main

Only after the full merged-main matrix passes:

- push main normally;
- prove local main, origin/main and remote main equal the exact merge SHA;
- do not create a post-deploy docs-only commit.

Define this exact SHA as DEPLOY_SHA.

## 7. New release and rollback root

Create outside Git:

  /opt/solarsage-release/<UTC-STAMP>-w8b

Retain:

- a mode-640 release manifest with safe identities only;
- the current deployed .next-prod as the immediate W8 rollback candidate;
- references to the older W6 rollback env/wheel/dist without moving or deleting
  them;
- build IDs and hashes;
- pre-deploy frontend PID/start time;
- exact DEPLOY_SHA.

No environment backup is needed because env must not change, but record hashes
of .env and .env.production before and after.

## 8. Isolated production frontend candidate

Build from exact DEPLOY_SHA with self-host semantics:

  env -u VERCEL
  NODE_ENV=production
  NEXT_TELEMETRY_DISABLED=1
  NEXT_DIST_DIR=.next-w8b-release-<STAMP>
  pnpm exec next build

Require:

- build success;
- BUILD_ID present;
- no tracked diff;
- candidate does not contain a rendered Vercel Analytics injection path for
  the root layout;
- candidate is not .next-prod yet.

Start candidate on 127.0.0.1:3010.

Smoke:

- root 200;
- /day/2026-07-08?why=1 returns 200;
- normal API health through canonical public API remains 200;
- browser root has zero /_vercel/insights scripts, requests and console errors.

Stop candidate and prove 3010 absent before swap.

## 9. Atomic frontend-only deployment

Do not restart sidecar, API or nginx.

Sequence:

1. Stop solarsage-frontend.service.
2. Require port 3002 absent.
3. Move current .next-prod atomically to:

     /opt/solarsage-release/<STAMP>-w8b/frontend/next-prod.rollback

4. Rename the completed candidate directory to .next-prod.
5. Start solarsage-frontend.service.
6. Require a new frontend PID and start timestamp.
7. Require port 3002 present.
8. Require local root 200 and public root/API health 200.
9. Require sidecar/API/nginx PIDs unchanged (202964/203504/1048). New frontend
   PID must differ from pre-W8B PID 298359.

On any failure after step 1:

- stop frontend;
- move failed new .next-prod aside into the W8 release root;
- restore the W8 immediate rollback dist atomically;
- start frontend;
- prove health;
- report rollback and stop.

## 10. Archive weakened R1 evidence

The W7-R1 evidence was useful for visual diagnosis but used a modified spec with
status adjustment and console filtering. Preserve it as rejected history.

Move the active seven evidence files to:

  /opt/solarsage-release/20260713T143406Z/rejected-evidence/w7-r1-filtered

Write a safe manifest:

- reason = modified_spec_and_console_filter;
- filenames and hashes;
- no personal/auth data.

Use the new W8 release root evidence directory for final proof:

  /opt/solarsage-release/<STAMP>-w8b/evidence

It must start empty.

## 11. Reversible full-entitlement setup

Use synthetic Telegram identity 999999999 only.

Repeat the private snapshot, one-row temporary referral entitlement, fail-closed
trap cleanup and exact before/after AccessLedger restoration protocol from
181 section 6.

Do not print the temporary row UUID.

The permitted row covers:

- start_date 2026-07-05;
- end_date 2026-07-18;
- referral_bonus, 14 days.

Before state is expected preview; proof state must be full; after state and
snapshot must exactly equal before.

## 12. Direct public HMAC proof

While temporary full entitlement is active:

- POST /api/auth/telegram => 200;
- GET /api/profile => 200;
- GET /api/day/2026-07-08 => 200;
- validate TodayPayload with API Pydantic model;
- access.state exact full;
- versions today.v2.1 / 3 / 10;
- horizons exact long/medium/fast;
- all timing/actions/spheres/provenance assertions;
- fixture dependency false;
- logout 204;
- revoked profile 401.

Write only the allowlisted structural redacted payload evidence into the new W8
evidence directory, mode 640 astro:astro.

## 13. Exact corrected canonical browser proof

Create the temporary spec from the updated canonical TypeScript block in:

  179_STAGE_2_W7_PRODUCTION_ACCEPTANCE_TZ.md

Before execution require exact byte count, line count and SHA supplied in the
accepted W8A callback.

No deviation is allowed.

In particular:

- allowed sphere verdict statuses are good/caution/avoid/neutral;
- all console errors are collected without filtering;
- no Vercel Analytics script may exist;
- access full and screen ready are mandatory;
- three horizons and twelve sphere rows are mandatory;
- no fixture/auth-dev/interception/HAR/mock/cookie seeding.

Run exactly one chromium and one mobile project with one worker.

Require:

- 2 passed;
- zero retry, skipped, unexpected or flaky;
- zero console errors;
- zero page errors;
- zero API failures;
- zero /_vercel/insights script/request;
- evidence JSON and screenshots written to the new W8 evidence directory.

Delete the temporary spec with apply_patch pass or fail.

## 14. Visual truth

Independently inspect all four new PNGs before callback.

Require:

- no paywall or lock-only view;
- activation/personal story visibly present;
- 12-sphere navigator visibly present in day screenshots;
- why screenshots visibly contain the three-horizon backend explanation, not a
  mostly blank generic page capture;
- desktop and mobile readable;
- no personal profile/auth data.

If the canonical why locator screenshot is visually defective because of the
scroll-container geometry, stop for architect classification. Do not replace
the canonical screenshot call ad hoc.

## 15. Final runtime, logs and rollback audit

After temporary access cleanup:

- AccessLedger before/after exact count and hash match;
- temporary row absent;
- local/origin/remote main equal DEPLOY_SHA;
- API health local/public git SHA equals DEPLOY_SHA prefix;
- sidecar and API PIDs unchanged;
- frontend new PID active;
- nginx PID unchanged;
- 18091/8000/3002/5433 present;
- 3003/3010/8001/18092 absent;
- .env/.env.production unchanged;
- V2 flags true/true and dual default;
- contracts wheel unchanged/noneditable in both venvs;
- new .next-prod BUILD_ID equals W8 candidate;
- W8 immediate rollback dist retained;
- older W6 rollback assets retained;
- exactly seven final W8 evidence files mode 640;
- rejected W7 and W7-R1 evidence retained separately;
- no temporary spec/private state/process/window;
- tracked worktree/index clean;
- only five frozen untracked paths remain.

Run safe journal counts since W8 frontend start:

- traceback/critical/startup failure/unhandled => 0;
- HTTP 5xx => 0;
- restart loop => 0;
- raw auth/cookie/token/profile/birth data => 0.

Public browser must show no Vercel Analytics failure.

## 16. Final callback and stop

Return:

  READY_STAGE_2_W8B_FINAL_PRODUCTION_ACCEPTANCE_REVIEW
  deploy_sha: <40-char main SHA>
  merge_sha: <40-char>
  main_local_origin_remote: EQUAL
  feature_sha: <accepted W8A SHA>
  canonical_spec_identity: <bytes>_<lines>_<sha256>
  full_gate_matrix: PASS_WITH_EXACT_COUNTS
  frontend_redeploy: ATOMIC_NEW_PID
  sidecar_api_nginx_pids: UNCHANGED
  analytics_self_host: NO_SCRIPT_NO_REQUEST_NO_CONSOLE_ERROR
  direct_hmac: AUTH_200_PROFILE_200_DAY_200_LOGOUT_204_REVOKED_401
  payload_access: FULL
  payload_versions: TODAY_V2_1_FRONTEND_3_CONTENT_10
  horizons: LONG_MEDIUM_FAST
  browser_e2e: 2_PASS_ZERO_RETRY_SKIP_UNEXPECTED_FLAKY
  browser_state: READY
  navigator: 12_SPHERES_GOOD_CAUTION_AVOID_NEUTRAL
  console_page_api_errors: ZERO
  evidence: 7_STRICT_FULL_ACCESS_FILES
  screenshots: FULL_V2_VISIBLE_THREE_HORIZONS_READABLE
  access_ledger_before_after: EXACT_MATCH
  git_worktree_index: CLEAN
  env_contracts_backend: UNCHANGED
  ports_health_journals_privacy: PASS
  w8_rollback: RETAINED
  w6_rollback: RETAINED
  rejected_evidence: W7_AND_W7_R1_RETAINED
  goal_completion: AWAITING_ARCHITECT_INDEPENDENT_REVIEW

Then stop. Only the architect may mark the overall goal complete.
