# 56_HANDOFF_R13_PHASE_B3_ACCESS_ONLY — Complete Access Contract Matrix Handoff

## 1. Acceptance Verification Results

The complete access contract matrix has been verified using `scripts/tests/test-prod-github-access.sh` in a strict isolated sandbox.

### 1.1 Shell Syntax Check
`bash -n` checks for both scripts passed with exit code 0:
```bash
bash -n scripts/prod-github-access.sh scripts/tests/test-prod-github-access.sh
```

### 1.2 Access Harness Execution
- **Command:** `timeout 300 bash scripts/tests/test-prod-github-access.sh`
- **Exit Code:** `0` (two separate runs, both rc 0)
- **Total Cases Executed:** 162 cases
- **ID Manifest Verification:** sorted exact `cmp -s` of `expected_case_ids` vs actual `case_ids` — both 162 lines, no mismatch (not just count check)
- **Mock self-check:** `verify_mock_contracts` passed — proves fail-closed behavior for outside-path, unexpected argv, owner rejection (`root:root`), nonexistent/symlink/wrong-category source, arbitrary temp template, arbitrary sandbox file for ssh-keygen, wrong-basename temp for python3.12 on all 9 mocks (stat, chown, mv, git, curl, timeout, ssh-keygen, mktemp, python3.12)
- **Forbidden Subcommands/Mocks Log:** verified empty (no unexpected git fetch/checkout/push commands)
- **Temp Files Cleanup:** verified clean — canonical temp patterns (`validation.??????`, `known_hosts.github.??????`, `config.??????`, `authorized_keys.??????`) scanned across entire `$TEST_DIR`
- **NET call count audit per case:** `assert_net_audit` proves exact curl=1, git-get-url=1, ls-remote=expected, timeout=expected, git-set-url=0 per NET case
- **Global output scan:** verified clean — no private keys, token base64, Actions comments, credential URLs, API body sentinel (`API_BODY_SENTINEL_R13`), malformed remote sentinel (`MALFORMED_REMOTE_SENTINEL_R13`), env secret sentinel (`ENV_SECRET_SENTINEL_R13`), or PEM markers leaked in any per-case stdout/stderr
- **Sentinels proven in dangerous channel:**
  - `API_BODY_SENTINEL_R13` injected via `MOCK_CURL_BODY_SENTINEL` in `NET21_TIMEOUT` — curl writes to stderr, global scan confirms no leak
  - `MALFORMED_REMOTE_SENTINEL_R13` injected via `MOCK_GIT_LS_REMOTE_OUT` in `NET13` — git ls-remote includes sentinel, global scan confirms no leak
  - `ENV_SECRET_SENTINEL_R13` exported to child environment — global scan confirms no leak
- **Diagnostic exit trap:** configured to log case IDs and exit codes safely on failure without `cat` of raw output
- **Old `/tmp/solarsage-r13-access-test.Mq98br`:** cleaned up (owner verified as `astro`, exact path, harness fixtures only)
- **No leaked harness temp directory:** verified after successful runs

### 1.3 Section Counts (sum = 162)

| Section | Count | IDs |
|---------|-------|-----|
| CLI | 15 | CLI01–CLI15 |
| PATH (path/type/mode/owner) | 40 | PATH01–PATH40 |
| PATH installed state | 9 | PATH41_SYMLINK, _MODE, _OWNER (×3 for known_hosts, config, authorized_keys) |
| KEY | 16 | KEY01–KEY16 |
| CFG | 15 | CFG01–CFG15 |
| AK | 11 | AK01–AK11 |
| ORIGIN | 8 | ORIGIN01–ORIGIN08 |
| NET | 30 | NET01–NET07, NET08_NONZERO, NET08_TIMEOUT, NET09–NET20, NET21_403/429/500/503, NET21_INVALID, NET21_CURL, NET21_TIMEOUT, NET22, NET23 |
| FAIL (failure + recovery) | 18 | FAIL01–FAIL09 + FAIL01_REC–FAIL09_REC |
| **Total** | **162** | |

All IDs verified by sorted manifest `cmp -s`.

### 1.4 R3 Gap Fixes Applied

1. **ID manifest (not just count):** Created `$TEST_DIR/expected_case_ids` with canonical sorted list of all 162 IDs. At end of harness, sorted expected and actual into temp copies, `cmp -s` verified exact match. Line counts both 162. Renamed `NET21-403` → `NET21_403` etc. to match handoff.

2. **Fail-closed mock contracts:**
   - **`chown`:** Only `astro:astro` allowed (not `root:root`). Target must exist, be regular non-symlink, have exact basename `known_hosts.github.<6alnum>`, `config.<6alnum>`, or `authorized_keys.<6alnum>`.
   - **`mv`:** Source must exist, be regular non-symlink, have exact 6-alnum suffix matching mktemp output (not broad `config.*`).
   - **`ssh-keygen`:** `-y -P '' -f` only for exact checkout private fixture. `-l -f` only for exact checkout private or Actions public fixture. Arbitrary sandbox file rejected.
   - **`mktemp`:** One-arg form must match exactly one of three template strings (`$MOCK_HOME/.ssh/{known_hosts.github,config,authorized_keys}.XXXXXX`). Arbitrary `.ssh` prefix templates rejected.
   - **`python3.12`:** Verification helper `verify_regfile_basename` added. Host-parse target must be existing regular non-symlink `validation.<6alnum>`. Config-write/authorized-write temp must be existing regular non-symlink with correct basename pattern.
   - **`verify_mock_contracts`:** Added negative self-checks for: `chown root:root` on valid sandbox temp; mv nonexistent/symlink/wrong-category source; ssh-keygen on arbitrary sandbox file; mktemp arbitrary template; python host-parse on arbitrary sandbox file; python config/authorized temp with wrong basename.

3. **NET exact read-only call counts:** Added `assert_net_audit <remote_expected:0|1>` helper. Verifies exact counts: curl=1, git get-url=1, ls-remote=remote_expected, timeout=remote_expected, git set-url=0, forbidden git empty. Called after every NET case with per-case mapping. Timeout mock refactored to always delegate to git mock (timeout trigger handled in git mock), ensuring consistent audit.

4. **Sentinels in dangerous channel:**
   - `NET21_TIMEOUT`: `MOCK_CURL_BODY_SENTINEL` set to `$API_BODY_SENTINEL_R13`. Curl writes sentinel to stderr. Global scan confirms no leak.
   - `NET13`: `MOCK_GIT_LS_REMOTE_OUT` includes `$MALFORMED_REMOTE_SENTINEL_R13` in ls-remote output. Global scan confirms no leak.
   - `ENV_SECRET_SENTINEL_R13` already exported at harness setup. All three sentinels proven by global output scan.

5. **Failure/recovery contract:**
   - Canonical expected state built once outside `CASE_COUNT` via `build_canonical_state_ref()`: successful sandbox `--apply`, canonical bytes+modes saved for all 3 destinations + origin.
   - Each `FAIL01–09`: asserts no "Successfully applied" message, no temp files, each destination is either full canonical bytes+mode or equals old snapshot (never truncated/partial), origin contract enforced, forbidden git audit confirmed empty.
   - Each `FAIL01_REC–FAIL09_REC`: asserts full canonical installed state: 3 regular non-symlink files with exact canonical bytes + mode `600`, canonical SSH origin. Recovery rc 0 not sufficient alone.
   - `FAIL09`: explicitly verifies origin remains old HTTPS (not mutated to canonical).
   - `prepare_installed_state` failure: safe diagnostics (label, rc, file paths only — no raw `cat` of stdout/stderr).

6. **Safe diagnostics and cleanup:**
   - `prepare_installed_state` failure: replaced raw `cat` with safe label, rc, paths to output.
   - Old `/tmp/solarsage-r13-access-test.Mq98br` cleaned up after owner/path/fixture verification.

### 1.5 Minimal Production Defects Found & Fixed (from R2)
1. **Template known-hosts self-comparison**: Fixed in `scripts/prod-github-access.sh` by introducing an audited template SHA-256 constant for verification instead of comparing the file to itself.
2. **Host alias validation outside managed block**: Updated python-based case-insensitive config parser to verify all host pattern fields, catching alias matches when listed as second/third pattern.
3. **Test-only absolute path fallbacks**: Removed fallback absolute paths from cmp checks in `scripts/prod-github-access.sh`.
4. **Credential logging in origin validation**: Removed raw `$current_origin` value from err logging to avoid printing credential-bearing URLs in clear text.
5. **Python host parser crash masking**: Configured python host parser to return explicit status codes and handled exception parsing without masking parser crashes as "alias found".

---

## 2. Safety Declarations
- No git commits or pushes were performed.
- No live systemd restarts, SSH, or GitHub API network connections occurred.
- No changes to production `scripts/prod-github-access.sh` (test harness only).
- Frozen path variables and baseline templates remain untouched.
- The modified test file (`scripts/tests/test-prod-github-access.sh`) has been updated with all R3 gap fixes as described above.
