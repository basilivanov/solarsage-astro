# Stage 2.W8A — self-hosted analytics fix and truthful acceptance contract

Date: 2026-07-13
Owner: coder in tmux astro:0.0
Reviewer: architect
Branch: fix/solarsage-v2-self-hosted-analytics-clean-console

## 1. Context

The product V2 UI is deployed and a temporary full-entitlement proof confirmed
that the public frontend can render the 12-sphere navigator and three backend
horizons.

The proof also exposed two separate issues which must not be conflated:

1. Acceptance-contract defect:
   the W7 temporary spec expected concrete advice row data-status values
   supportive/neutral/tense, while the canonical backend/frontend verdict
   contract is good/caution/avoid/neutral.

2. Product defect:
   app/layout.tsx mounts @vercel/analytics whenever NODE_ENV is production.
   This systemd deployment is self-hosted, not deployed to Vercel, so the SDK
   requests /_vercel/insights/script.js and receives 404. Filtering that console
   error in acceptance is forbidden; the product must stop emitting the invalid
   request on self-hosted production.

Installed package evidence for @vercel/analytics 1.6.1:

- package README describes use for apps deployed to Vercel;
- production default script source is /_vercel/insights/script.js;
- current public endpoint returns 404.

## 2. Goal

Implement a minimal, explicit deployment-boundary fix:

- Vercel Analytics renders only for an actual Vercel production deployment;
- self-hosted production renders no Vercel Analytics component and performs no
  /_vercel/insights request;
- development and test also render no Vercel Analytics component;
- no new environment variable or self-host analytics proxy is introduced;
- the W7 canonical browser acceptance block uses the actual four-value verdict
  enum and remains strict about every console error;
- all frontend and repository gates pass;
- commit and push the isolated fix branch for architect review.

## 3. Absolute restrictions

- Do not change backend or sidecar behavior.
- Do not change Today V2 payloads, horizons, timing, actions, copy or scoring.
- Do not change the concrete advice verdict contract.
- Do not map avoid into caution or remove the four-value distinction.
- Do not add a console-error filter.
- Do not ignore /_vercel/insights failures in tests.
- Do not add an nginx proxy for /_vercel.
- Do not add a fake analytics endpoint.
- Do not add a new .env or .env.production flag.
- Do not modify systemd or nginx in W8A.
- Do not deploy in W8A.
- Do not touch production database.
- Do not touch W6 rollback assets or release evidence.
- Do not touch the five frozen unrelated paths.
- Do not stage unrelated files.
- Do not force-push.

## 4. Entry and branch

Require:

- current branch main;
- HEAD, origin/main and remote main equal
  4d8f03b5c89da050790eaf7391e0b3e8baaa31c5;
- tracked worktree and index clean;
- the only additional task document is untracked 181 plus the new W8 docs;
- production services remain active.

Create:

  fix/solarsage-v2-self-hosted-analytics-clean-console

Do not branch from any other SHA.

## 5. Deployment-boundary helper

Create:

  lib/analytics/vercel.ts

The module must include complete GRACE AI_HEADER, module contract, module map,
function contract and semantic block.

Expose one pure function with an explicit environment input, for example:

  shouldRenderVercelAnalytics(env)

Required truth table:

- NODE_ENV=production and VERCEL=1 => true;
- NODE_ENV=production and VERCEL absent => false;
- NODE_ENV=production and VERCEL=0 => false;
- NODE_ENV=development and VERCEL=1 => false;
- NODE_ENV=test and VERCEL=1 => false;
- malformed/partial input => false.

Use exact equality. Do not treat any non-empty VERCEL string as true.

The default call path may use process.env, but tests must be able to pass a
plain explicit object without mutating global process state.

The helper is server-layout infrastructure. It must not become a client module.

## 6. Root layout integration

Modify only the necessary part of:

  app/layout.tsx

Requirements:

- import the helper;
- replace NODE_ENV-only rendering with the helper result;
- actual Vercel production still renders Analytics;
- self-hosted production does not render Analytics;
- TelegramProvider, TelegramInit, CorrelationInit, metadata, fonts, error
  listeners and children remain behaviorally unchanged.

Update the existing GRACE module contract because it currently describes the
layout inaccurately as an API client. The corrected contract must state:

- root document shell ownership;
- Telegram/correlation bootstrap;
- global client crash capture;
- Vercel-only analytics injection;
- no direct business API fetch owned by RootLayout;
- analytics invariant is fail-closed outside Vercel production.

Do not perform an unrelated layout rewrite.

## 7. Unit tests

Create:

  __tests__/lib/vercel-analytics.test.ts

Include GRACE test-file preamble consistent with repository conventions.

Test every truth-table row from section 5.

Add a source/integration assertion that app/layout.tsx delegates analytics
visibility to the helper and no longer uses NODE_ENV alone as its Analytics
condition. Prefer a stable structural assertion; do not snapshot the full
layout.

The tests must fail against current main and pass after the fix.

## 8. Correct the canonical W7 acceptance contract

Modify only the necessary lines inside:

  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/179_STAGE_2_W7_PRODUCTION_ACCEPTANCE_TZ.md

Inside the canonical temporary Playwright block:

1. Change the concrete advice allowed status set to:

     good, caution, avoid, neutral

2. Add an exact DOM assertion that no Vercel Analytics script is injected:

     script[src*="/_vercel/insights/"]

   count must be zero.

3. Keep the unfiltered collection and exact zero assertion for every console
   error.

4. Do not add an allowlist or exception for third-party/Vercel errors.

5. Keep all existing HMAC, access full, ready state, 12 spheres, three
   horizons, focus, no fixture, no auth/dev, no interception and evidence
   assertions.

After editing, compute and report the new canonical code-block:

- byte count;
- line count;
- SHA-256.

Do not edit 181 to conceal or rewrite the rejected-history record.

## 9. Static and unit gates

Run:

  npx vitest run __tests__/lib/vercel-analytics.test.ts
  npx vitest run
  pnpm typecheck
  pnpm guardrails:prod
  pnpm guardrails:contracts
  pnpm guardrails:frontend
  pnpm guardrails:secrets

Run contract drift gates:

  pnpm contracts:generate
  git diff --exit-code -- packages/contracts/openapi.json
    packages/contracts/_generated.ts
    packages/contracts/_generated.zod.ts
  pnpm contracts:check
  pnpm contracts:compat
  pnpm contracts:fixture:check

No generated contract file may change.

Run formatting/lint checks applicable to changed TypeScript files.

## 10. Isolated self-host candidate proof

Build an isolated candidate with VERCEL explicitly absent:

  env -u VERCEL
  NODE_ENV=production
  NEXT_TELEMETRY_DISABLED=1
  NEXT_DIST_DIR=.next-w8a-self-host
  pnpm exec next build

Do not overwrite .next-prod.

Start the candidate on loopback port 3010 only.

Use a temporary Playwright proof, created and deleted with apply_patch, that:

- opens the candidate root in a new browser context;
- records all requests, failed requests, console errors and page errors;
- requires root 200;
- requires zero script elements whose src contains /_vercel/insights/;
- requires zero requests whose path starts /_vercel/insights;
- requires zero failed requests caused by Vercel Analytics;
- requires zero console/page errors;
- does not use API interception, fixtures, auth/dev or mocks.

Also curl:

- candidate root => 200;
- candidate /api/health through the normal proxy behavior expected for this
  isolated mode, classified explicitly if unavailable;
- production remains untouched.

Stop 3010 and prove the listener/window/process absent.
Delete .next-w8a-self-host after evidence is collected.

## 11. Diff and scope review

Expected product/test files:

- app/layout.tsx;
- lib/analytics/vercel.ts;
- __tests__/lib/vercel-analytics.test.ts.

Expected documentation files:

- 179 updated narrowly;
- 181 added as the rejected-proof audit record;
- 182 and 183 task documents.

No backend, sidecar, contract artifact, env, service or deployment file changes.

Review:

- git diff --check;
- no secret material;
- no raw auth/profile data;
- no generated drift;
- no unrelated staged paths;
- GRACE completeness for new/significantly changed code.

## 12. Commit and push

Only after all W8A gates pass:

1. Stage exact expected files.
2. Commit with subject:

     fix(frontend): gate Vercel analytics to Vercel deployments

3. Push only:

     origin/fix/solarsage-v2-self-hosted-analytics-clean-console

Do not merge to main and do not deploy.

## 13. Callback and stop

Return:

  READY_STAGE_2_W8A_SELF_HOST_ANALYTICS_REVIEW
  base_sha: 4d8f03b5c89da050790eaf7391e0b3e8baaa31c5
  branch: fix/solarsage-v2-self-hosted-analytics-clean-console
  feature_sha: <40-char>
  product_files: <exact list>
  docs_files: <exact list>
  helper_truth_table: PASS
  layout_delegate: PASS
  verdict_contract: GOOD_CAUTION_AVOID_NEUTRAL
  canonical_w7_block: <bytes>_BYTES_<lines>_LINES_<sha256>
  console_filtering: ZERO
  self_host_candidate: ROOT_200_NO_VERCEL_SCRIPT_REQUEST_CONSOLE_ERROR
  contracts: DRIFT_ZERO_CHECK_COMPAT_FIXTURE_PASS
  vitest: <files/tests exact>
  typecheck_guards: PASS
  temporary_port_process_dist: ABSENT
  tracked_worktree: CLEAN
  index: EMPTY
  frozen_untracked: PRESERVED
  production_mutated: FALSE

Then stop for architect review.

