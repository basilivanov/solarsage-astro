# R14 Phase C1A-R2 — exact transaction and acceptance-harness correction

## Read first

- `99_TZ_R14_PHASE_C1A_ENV_PROFILE_ENGINE.md`;
- `101_TZ_R14_PHASE_C1A_R1_ATOMIC_PROFILE_ENGINE_FIX.md`;
- `102_REVIEW_R14_PHASE_C1A_R1_REJECTED_FALSE_GREEN.md`.

This is still C1A only. Do not start C1B consumer cut-over or C2 database
identity. No production/network/SSH/DB/Docker/systemd mutation, commit or push.

## A. Fix `prod-env-prepare.sh` transaction state machine

### A1. One exit owner, one rollback

Remove the current double-rollback pattern. Use one EXIT handler that receives
the original exit/signal status, performs rollback exactly once when
`ROLLBACK_ACTIVE=1`, and then returns the original status if rollback succeeds.

Rules:

- `abort_transaction <status> <symbolic-code>` does not call rollback directly;
  it records the status and exits, allowing the one EXIT handler to roll back.
- On successful rollback set `ROLLBACK_ACTIVE=0` before cleanup.
- A signal handler records 129/130/143 and exits; the EXIT handler must preserve
  that exact code after successful rollback.
- If rollback fails, preserve the root-only snapshot and return a distinct
  nonzero recovery code while emitting only the snapshot path and symbolic
  codes. Never delete a snapshot needed for recovery.
- Do not let a cleanup trap overwrite the original status.

### A2. Validate pre-state before mutation

Before snapshot/rename, require:

- env directory: real non-symlink directory, `root:astro 0750`, link count 1;
- source: real regular non-symlink, `root:astro 0640`, link count 1;
- every destination: absent, or real regular non-symlink `root:astro 0640`,
  link count 1;
- reject a partial profile set unless the documented policy explicitly handles
  it. Prefer fail-closed: only all seven absent (first install) or all seven
  present (update) are accepted.

The `--check` path must validate the same physical metadata and be read-only.
It must not accept a symlinked env directory, source hardlink or profile
hardlink. Tests must use a sandbox copy plus narrow metadata shims so they run
as ordinary `astro`; do not require the test runner to be root.

### A3. Snapshot and restore fail closed

- Snapshot presence/absence, bytes, mode, owner/group and link count for all
  destinations before mutation.
- Snapshot writes are fsynced; any snapshot error aborts before live mutation.
- Restore into a private same-directory staging area, verify every staged file,
  then rename into place. Do not `cp` directly over a live profile.
- Every `cp`, `chown`, `chmod`, `rename`, file fsync and directory fsync is
  checked. Remove all `|| true` from transaction and rollback paths.
- After rollback, verify all seven profiles byte- and metadata-exact against the
  snapshot before reporting recovery success.
- If verification/rollback fails, keep the snapshot and generation directories
  for root-only manual recovery and report their safe paths; do not claim
  atomicity.
- On a successful commit, verify the complete new set before deleting snapshot.

### A4. Test actual injected commit failures

The harness must inject a failure on each rename position (1 through 7), plus
snapshot write, chown, chmod, file fsync and directory fsync. For each case,
assert:

- nonzero original failure status;
- no mixed generation;
- all-old bytes/metadata after successful rollback;
- exact signal status for HUP/INT/TERM during commit;
- no temp cleanup when rollback is not proven.

Do not only test pre-render validation failure; that never exercises rollback.

## B. Complete `prod-env-tool.py` edge contracts

### B1. Domain and CLI

- Pass `--domain` into `parse_source` and require exact
  `astro.vasiliy-ivanov.ru` (or the explicitly passed expected domain in
  synthetic tests).
- Reject `--` in every non-`run` command.
- Reject duplicate, unknown, missing and extra options before source access.
- Keep diagnostics value-free.

### B2. Complete bounded read

After safe `open_source`/`fstat`, reject files larger than the maximum supported
size and read until EOF. Do not silently truncate after one `os.read` call.
Reject a valid first chunk followed by hidden data.

### B3. Exact values and serializer input

- Boolean flags accept only literal lowercase `true` or `false`.
- Keep source data inert: allow ordinary backslash, quotes, `#`, `%`, `=`, `>`
  and a plain `$`; reject NUL/CR/LF/control, backticks, `${`, `$(` and `<<`.
- `deserialize_envfile` requires final LF, canonical sorted key order, valid key
  grammar, exactly double-quoted values and only the four known escape forms.
  Unknown or dangling escapes fail.
- Keep migration `PGSSLMODE=disable` in both render and `run`/`emit-nul` where
  the compatibility loader needs it.

### B4. Profile validation semantics

`validate --profile NAME` parses the complete source and validates/render-checks
that named profile; it must not reject unrelated keys belonging to other
profiles in the same source. `--profile all` validates the complete source.
Add explicit tests for both behaviors.

## C. Rewrite tests so they really execute

### C1. Never rely on `set -e` for expected failures

Add a helper such as:

```bash
expect_rc() {
  local expected="$1" label="$2"; shift 2
  set +e
  "$@"
  local got=$?
  set -e
  [ "$got" -eq "$expected" ] || fail "$label rc=$got expected=$expected"
}
```

Use it for every intentional nonzero command. The script itself must return
nonzero on any failed assertion. Do not pipe the test through `tail`; if output
is shortened, capture the command status with `pipefail` and report it.

### C2. Correct sandbox prepare setup

- Copy both `prod-env-prepare.sh` and `scripts/lib/prod-env-tool.py` to the
  sandbox; rewrite the actual computed tool path with an exact substitution
  count assertion.
- Write the synthetic source directly to the sandbox source path; do not use a
  function that writes another hardcoded path.
- Use narrow `id/stat/chown` shims only for metadata; never shim `mv`, parser,
  serializer or rollback logic.
- Assert the sandbox directory and source modes and all generated metadata.
- Run first apply, repeat update, real injected rename failure, real signal
  failure and read-only check.

### C3. Real mutation proof

`test-prod-env-profiles-mutations.sh` must copy the implementation **and run the
actual profile harness against that copy**, with exact path substitution. Each
mutation must be verified to change exactly one intended occurrence and must
make the copied harness fail.

Required mutations:

1. remove one required-key assertion;
2. remove `O_NOFOLLOW`;
3. ignore unknown CLI option;
4. remove migration `PGSSLMODE`;
5. weaken serializer escaping and prove via an independent reference parser;
6. weaken forbidden-character validation;
7. reintroduce provider-value diagnostic leak;
8. remove duplicate-option rejection;
9. remove rollback verification;
10. swallow directory fsync failure.

Do not count a mutation as proof merely because the mutated direct command
returns the expected bad value. The canonical copied harness must become red.
No fixed shared `/tmp/mut04_verify_out`; all paths are under one private test
directory and are cleaned on every outcome.

## D. Regression fixture updates

Update synthetic fixtures in `test-prod-env-loader.sh` to include all newly
required production flags. Do not weaken the validator to preserve obsolete
fixtures. Re-run B6 harness unchanged and confirm its source-loader contract
still passes.

## Acceptance and handoff

Run directly, from a fresh shell, and record each true exit code (no `tail`
masking):

```bash
bash -n scripts/lib/prod-env-loader.sh scripts/prod-env-prepare.sh \
  scripts/tests/test-prod-env-loader.sh scripts/tests/test-prod-env-profiles.sh \
  scripts/tests/test-prod-env-profiles-mutations.sh
python3.12 -I -S -c 'compile(open("scripts/lib/prod-env-tool.py", "rb").read(), "scripts/lib/prod-env-tool.py", "exec")'
bash scripts/tests/test-prod-env-loader.sh
bash scripts/tests/test-prod-env-profiles.sh
bash scripts/tests/test-prod-env-profiles.sh
bash scripts/tests/test-prod-env-profiles-mutations.sh
bash scripts/tests/test-prod-deploy-source-loader.sh
bash scripts/tests/test-prod-host-offsite-routing.sh
bash scripts/prod-infra-fingerprint.sh
git diff --check
```

Handoff must include the real rc, stdout/stderr byte counts, final line, all
rename/signal mutation IDs, snapshot-preservation proof on rollback failure and
zero stale process/temp paths. Stop after R2; do not start C1B/C2.
