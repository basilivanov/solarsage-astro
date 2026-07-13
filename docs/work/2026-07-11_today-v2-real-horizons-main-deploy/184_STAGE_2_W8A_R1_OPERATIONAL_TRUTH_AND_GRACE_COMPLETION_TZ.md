# Stage 2.W8A-R1 — operational truth and GRACE completion

Date: 2026-07-13
Owner: coder in tmux astro:0.0
Reviewer: architect
Branch: fix/solarsage-v2-self-hosted-analytics-clean-console

## 1. Review result

W8A commit 560454113340367fd9252c11d380fd4537303869 is not yet accepted.

The product logic is directionally correct, but the callback and branch state
are incomplete.

Authoritative findings:

1. Documents 181, 182 and 183 are present but untracked.
2. The commit contains only app/layout.tsx, lib/analytics/vercel.ts, its unit
   test and the narrow 179 correction.
3. shouldRenderVercelAnalyticsFromEnv is an exported public function but is
   missing from START_MODULE_MAP and has no START_FUNCTION_CONTRACT.
4. A broad pkill candidate-cleanup command deactivated the canonical production
   frontend at 2026-07-13 18:55:35 MSK.
5. systemd restarted the same deployed frontend at 18:55:45 MSK:
   - old accepted frontend PID: 204066;
   - current frontend PID: 298359;
   - NRestarts: 1;
   - current service active/running and port 3002 healthy.
6. The callback statement production_mutated: FALSE is therefore false.
7. A candidate was briefly started without loopback hostname and then stopped;
   current port 3010 is absent.
8. No product build swap occurred; current .next-prod BUILD_ID remains the W6B
   build HBrg3x9QiX5xEyK9-HCET.

This review wave must record facts rather than conceal them.

## 2. Goal

- Complete GRACE contracts for both exported helper functions.
- Track task documents 181 through 184 in the feature branch.
- Update W8B entry expectations to use the actual current frontend PID/start
  while preserving W6B sidecar/API/nginx identities.
- Record the operational incident explicitly.
- Re-run focused static/unit gates.
- Commit and push a clean follow-up commit.
- Do not rebuild, rerun the candidate, restart production, or deploy.

## 3. Absolute restrictions

- No functional change to the analytics truth table.
- No backend, sidecar, contract, payload or UI behavior change.
- No production process command.
- No systemctl, kill, pkill, killall, nohup or tmux candidate launch.
- No port 3010 process.
- No build.
- No env edit.
- No commit amend or force-push.
- No deletion or rewriting of rejected evidence.
- No touching frozen unrelated paths.
- No false production_mutated claim.

## 4. GRACE completion

Modify lib/analytics/vercel.ts only in comments/contracts:

- add shouldRenderVercelAnalyticsFromEnv to public_entrypoints;
- give it a complete START_FUNCTION_CONTRACT;
- state that it reads process.env and returns the pure helper result;
- side effects none;
- emitted logs none;
- error behavior fail closed through the pure helper.

Do not alter either function body unless a type/format gate proves a defect.

Ensure module map and contracts use the exact public names.

## 5. Track the release task documents

Add:

- 181_STAGE_2_W7_R1_FULL_ACCESS_PROOF_CORRECTION_TZ.md;
- 182_STAGE_2_W8A_SELF_HOSTED_ANALYTICS_AND_ACCEPTANCE_CONTRACT_FIX_TZ.md;
- 183_STAGE_2_W8B_MERGE_FRONTEND_REDEPLOY_AND_FINAL_ACCEPTANCE_TZ.md;
- 184_STAGE_2_W8A_R1_OPERATIONAL_TRUTH_AND_GRACE_COMPLETION_TZ.md.

Do not edit 181 to erase its rejected-proof history.

In 183, correct the W8B entry text:

- sidecar PID remains 202964;
- API PID remains 203504;
- nginx PID remains 1048;
- frontend pre-W8B PID is now 298359;
- frontend start is 2026-07-13 18:55:45 MSK;
- NRestarts is 1 because W8A candidate cleanup accidentally terminated the
  prior production frontend;
- current BUILD_ID is still HBrg3x9QiX5xEyK9-HCET;
- W8B must replace PID 298359 with the intentional new frontend deployment PID.

Add an explicit prohibition in 183:

- never use pkill -f, pkill, killall or process-name matching;
- only exact systemd frontend stop/start for deployment;
- only exact tmux candidate window lifecycle for port 3010.

## 6. Focused verification

Run:

  npx vitest run __tests__/lib/vercel-analytics.test.ts
  pnpm typecheck
  pnpm guardrails:prod
  pnpm guardrails:frontend
  pnpm guardrails:secrets
  git diff --check

Verify without mutation:

- branch HEAD starts at 560454113340367fd9252c11d380fd4537303869;
- origin branch matches before new commit;
- production frontend active PID 298359;
- sidecar/API/nginx PIDs unchanged;
- port 3002 present;
- port 3010 absent;
- public root and API health 200;
- current and W6 rollback BUILD_ID values retained;
- no candidate process/window/dist remains.

## 7. Exact diff review

The follow-up commit may contain only:

- comment/contract-only diff in lib/analytics/vercel.ts;
- tracked docs 181, 182, 183, 184.

No app/layout or test logic change is expected in R1.

The full branch diff from deployed main remains:

- W8A product/test/doc changes from commit 5604541;
- the R1 GRACE comment completion;
- task documents 181–184.

## 8. Commit and push

Stage exact R1 files.

Commit subject:

  docs(release): complete W8A operational review

Push the same feature branch normally.

Require:

- local feature, origin feature and remote feature equal new SHA;
- tracked worktree clean;
- index empty;
- only five frozen untracked paths remain.

## 9. Callback and stop

Return:

  READY_STAGE_2_W8A_R1_OPERATIONAL_TRUTH_REVIEW
  base_sha: 4d8f03b5c89da050790eaf7391e0b3e8baaa31c5
  implementation_sha: 560454113340367fd9252c11d380fd4537303869
  feature_sha: <new 40-char SHA>
  branch_remote: EQUAL
  analytics_logic: UNCHANGED_PASS
  grace_public_functions: COMPLETE
  docs_181_184: TRACKED
  production_incident: ACKNOWLEDGED_FRONTEND_AUTO_RESTART
  production_frontend: PID_298359_START_2026_07_13_18_55_45_NRESTARTS_1
  production_build: UNCHANGED_HBrg3x9QiX5xEyK9-HCET
  sidecar_api_nginx_pids: 202964_203504_1048_UNCHANGED
  focused_tests_guards: PASS
  port_3010_candidate_process_window_dist: ABSENT
  tracked_worktree: CLEAN
  index: EMPTY
  frozen_untracked: EXACT_FIVE
  production_mutated_in_r1: FALSE

Then stop. Do not start 183 without architect authorization.
