# 66_HANDOFF_R13_PHASE_B4_WRAPPER_CONTRACT — Forced-Command Wrapper Contract Matrix Handoff

## 1. Acceptance Verification Results

The complete forced-command wrapper contract matrix has been verified using `scripts/tests/test-prod-github-wrapper.sh` in a strict isolated sandbox.

### 1.1 Shell Syntax Check
`bash -n` passes with exit code 0:
```bash
bash -n scripts/tests/test-prod-github-wrapper.sh
```

### 1.2 Harness Execution
- **Command:** `timeout 120 bash scripts/tests/test-prod-github-wrapper.sh`
- **Exit Code:** `0` (two consecutive runs, both rc 0)
- **Total Cases Executed:** 48 product cases + 9 self-tests (outside count)
- **Fail-closed path substitution:** verified before any test — deploy and access canonical paths each appear exactly once before substitution, zero times after; sandbox mock paths appear exactly once each
- **Mock target audit:** each mock records full `exec` argv in `printf '%q\n'` format, verified via `cmp -s` against expected audit files
- **Propagation integrity:** rc 0/1/42/126 from mock target propagated correctly through wrapper to caller
- **Self-test block (9 mutations):** all pass — each mutation introduces a real bug that the harness would detect:
  - Self-test 1: mock adds extra argv → audit mismatch
  - Self-test 2: mock reorders argv → audit mismatch
  - Self-test 3: deploy/access paths swapped → wrong target called
  - Self-test 4: exec replaced with exit → audit missing
  - Self-test 5: two argv concatenated into one → audit mismatch
  - Self-test 6: target called twice → 8 audit lines instead of 4
  - Self-test 7: literal-space check bypassed → tab-separated command accepted
  - Self-test 8: regex widened to accept uppercase SHA
  - Self-test 9: `$` end-anchor removed → trailing content accepted

### 1.3 Case Manifest (48 product cases)

**Negative matrix — deploy (19 cases):** DEP_N01–DEP_N19
- Covers: empty command, positional args, uppercase SHA, non-hex SHA, short SHA, long SHA, missing SHA, two spaces, leading space, trailing space, tab, trailing LF, trailing CR, extra token, semicolon, command substitution, pipe/&&, other verb, arbitrary command
- Each verified with rc 126, no target called, no audit file created

**Negative matrix — source-check (19 cases):** SRC_N01–SRC_N19
- Same coverage as deploy, all verified with rc 126, no target called

**Positive matrix — deploy (5 cases):** DEP_V01, DEP_V02, DEP_P01–DEP_P03
- DEP_V01: valid SHA1 → rc 0, deploy audit matches expected
- DEP_V02: valid SHA2 → rc 0, deploy audit matches expected
- DEP_P01: propagation rc 1 → rc 1, deploy audit matches expected
- DEP_P02: propagation rc 42 → rc 42, deploy audit matches expected
- DEP_P03: propagation rc 126 → rc 126, deploy audit matches expected

**Positive matrix — source-check (5 cases):** SRC_V01, SRC_V02, SRC_P01–SRC_P03
- Same structure as deploy positive, verify access audit matches

### 1.4 Verification Artifacts

| Artifact | Path |
|----------|------|
| Wrapper under test | `infra/production/solarsage-github-deploy` |
| Test harness | `scripts/tests/test-prod-github-wrapper.sh` |
| Canonical deploy target | `scripts/prod-deploy.sh` |
| Canonical access target | `scripts/prod-github-access.sh` |
| Tech zadanie | `64_TZ_R13_PHASE_B4_WRAPPER_FINAL_CONTRACT.md` |

All temp directories are created under `/tmp/solarsage-r13-wrapper-test.XXXXXX` and cleaned up on exit.

## 2. Proven Claims

| Claim | Evidence |
|-------|----------|
| Fail-closed path substitution works | Pre/post path counts verified: canonical 1→0, sandbox 0→1 for both targets |
| All 38 negative cases (19 deploy + 19 source-check) return rc 126, call no target | Each case: `[ -f "$DEPLOY_AUDIT" ]` false; rc matches 126 |
| All 10 positive cases (5 deploy + 5 source-check) call correct target with correct argv | Audit file `cmp -s` matches expected, asserting `/bin/bash`, target path, `--expected-sha`, SHA value |
| Return codes propagate through wrapper | `MOCK_TARGET_RC=1/42/126` produce rc 1/42/126 from wrapper |
| 9 self-test mutations each produce a detectable harness failure | Each self-test introduces unique bug and verifies harness assertion catches it |
| Duplicate case IDs rejected | `run_case` checks against `case_ids` file via `grep -Fxq` |
| Invalid case ID format rejected | `run_case` validates `^[A-Z0-9_]+$` |
| Wrapper rejects positional args | DEP_N02, SRC_N02: `"$#" -ne 0` check returns 126 |
| Wrapper rejects empty SSH_ORIGINAL_COMMAND | DEP_N01, SRC_N01: `-z` check returns 126 |
| Wrapper requires exactly `deploy<space><40 lower hex>` | Full negative matrix proves no variation accepted |
| Wrapper requires exactly `source-check<space><40 lower hex>` | Full negative matrix proves no variation accepted |
| Literal-space check is independent from regex | `deploy<tab>SHA1` passes `[[:space:]]` regex but caught by `!= "deploy "*` check (DEP_N11) |

## 3. Risks / Assumptions

- **No production changes applied:** This harness tests the wrapper via fail-closed path substitution only. No real deploy/access scripts are executed.
- **No network/SSH/git/systemd operations:** All targets are stubbed with mock scripts that record argv and exit with controlled return codes.
- **Self-tests 7–9 verify mutation effectiveness, not production behavior:** Each introduces a specific regex/validation bug and confirms the harness would detect it. They do not test the production wrapper's behavior — that is covered by the 48 product cases.
- **Line-number-dependent sed mutations:** Self-tests 7, 9 rely on line numbers (59, 67) and specific pattern shapes in the wrapper. If the wrapper is restructured, these self-tests may need updating.
- **Hash collision not tested:** No test verifies behavior with two different 40-char hex strings resolving to the same object. This is outside the wrapper contract scope.
