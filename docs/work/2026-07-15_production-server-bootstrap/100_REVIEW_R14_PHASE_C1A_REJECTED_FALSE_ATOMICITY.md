# R14 Phase C1A review — rejected: false atomicity and false-green harness

## Verdict

C1A is **rejected**. The baseline suites are green, but the implementation does
not satisfy the transaction, filesystem, serializer, CLI or test contracts in
`99_TZ_R14_PHASE_C1A_ENV_PROFILE_ENGINE.md`.

No production deploy, network, SSH, database, Docker, systemd mutation, commit
or push was performed. All adversarial proof used synthetic files under `/tmp`.

## Baseline evidence

Independent unfiltered runs:

```text
bash -n relevant scripts                         PASS
stdlib compile prod-env-tool.py                  PASS
test-prod-env-loader.sh                          rc=0, SUCCESS
test-prod-env-profiles.sh run 1                   rc=0, 38/38
test-prod-env-profiles.sh run 2                   rc=0, 38/38
test-prod-deploy-source-loader.sh                 rc=0, 111/111
test-prod-host-offsite-routing.sh                 rc=0, SUCCESS
prod-infra-fingerprint.sh                         rc=0
git diff --check                                  PASS
stale env test directories                        0
```

This green baseline is not acceptance because important production paths are
not exercised by the new harness.

## P0 blockers

### 1. `--apply` is not an all-or-nothing transaction

At `scripts/prod-env-prepare.sh:188-202`, profiles are moved into canonical
locations one by one. The alleged rollback loop at lines 194-199 contains only
`:` and restores nothing. Existing profile bytes are not snapshotted.

Independent injected third-`mv` failure:

```text
apply_injected_mv_failure_rc=4
old_profiles=5
replaced_profiles=2
```

The command returns failure with a mixed live generation. This directly
violates the main C1A invariant and would let different services read different
configuration generations.

The directory fsync at `scripts/prod-env-prepare.sh:205` also has `|| true`, so
durability failure is reported as success.

### 2. Required production security keys may be omitted

`parse_source()` supplies safe-looking defaults for missing keys instead of
requiring explicit production declarations (`scripts/lib/prod-env-tool.py:268-286`).

Independent results:

```text
missing_required_APP_ENV_rc=0
missing_required_DEV_MODE_rc=0
missing_required_SESSION_COOKIE_SECURE_rc=0
missing_required_CORS_ALLOWED_ORIGINS_rc=0
```

An incomplete source therefore becomes green and may rely on downstream
defaults. `CORS_ALLOWED_ORIGINS` is especially required by the deployed runtime
security policy.

### 3. Canonical directory/source physical identity is not enforced

- Python `_safe_path()` uses `os.stat()` and then reopens by pathname, following
  symlinks and leaving a stat/open race (`prod-env-tool.py:173-196`).
- The shell wrapper does not reject a symlink `/etc/solarsage/env`, does not
  validate directory owner/mode, and does not check source link count.
- `verify-set` follows a symlink output directory and profile paths.

Independent results:

```text
regular_target_symlink_source_rc=0
verify_symlink_output_dir_rc=0
prepare_check_symlink_env_dir_rc=0
source_link_count=2 prepare_check_hardlinked_source_rc=0
```

The existing symlink test points to `/dev/null`; it passes only because the
target is not regular. It does not prove rejection of a symlink to a valid file.

## P1 blockers

### 4. EnvironmentFile serializer is not the promised serializer

`serialize_envfile()` writes raw `KEY=value` and `deserialize_envfile()` parses
the same private format (`prod-env-tool.py:355-387`). There is no canonical
systemd quoting implementation or independent reference round trip.

The source parser rejects every backslash and plain `>` although C1A explicitly
requires these values to be handled as inert data. Independent result:

```text
allowed_serializer_backslash_source_rc=12
```

The harness serializer section only reruns `verify-set` on ordinary URL values;
it does not test spaces, values beginning with quotes, backslashes, `#`, `%`,
`=`, Unicode or static `systemd-analyze verify`.

### 5. `run` omits command-owned migration policy

`render_profile("migration")` adds `PGSSLMODE=disable`, but `cmd_run()` builds
its environment directly from the source allowlist and never adds it
(`prod-env-tool.py:623-633`).

```text
migration_run_rc=0 pgsslmode=missing
```

The new harness has a "Fixed child environment" heading but executes no child
environment assertion.

### 6. CLI is not exact and silently ignores attacker/operator input

Every handler accepts `len(args) >= expected` and ignores unknown pairs. It also
does not reject duplicate options before doing work.

```text
unknown_cli_pair_rc=0
run_unknown_cli_pair_rc=0
```

This violates the exact CLI contract and makes typos silently succeed.

### 7. A diagnostic prints a source value

The unknown LLM provider error includes the provider value at
`prod-env-tool.py:308`.

```text
provider_invalid_rc=11 value_leaked=yes
```

Diagnostics must contain a stable symbolic code, never source values.

### 8. Registry is already incomplete relative to current application code

The API settings and canonical runbook contain current production keys missing
from the registry:

- `CONTRACT_VERSION`;
- `SOLARSAGE_V2_FRONTEND_ENABLED`;
- `SOLARSAGE_AUDIT_ARTIFACTS_ENABLED`.

The last two are explicit production rollout flags in
`apps/api/app/core/config.py:176-177` and `docs/PRODUCTION_RUNBOOK.md:70-71`.
The current engine would reject a source that follows the runbook.

### 9. The harness is materially incomplete

`scripts/tests/test-prod-env-profiles.sh` contains 38 simple cases, but:

- never executes a sandboxed `prod-env-prepare.sh --apply` or `--check`;
- has no real transaction rollback failure;
- has no HUP/INT/TERM proof;
- has no source/output owner/mode/hardlink matrix;
- has no child environment proof;
- has no serializer special-character matrix;
- has no secret-output scan;
- has no reproducible mutation section despite the handoff claiming six
  adversarial mutations.

The fake atomicity therefore remained green.

## Required correction

Implement `101_TZ_R14_PHASE_C1A_R1_ATOMIC_PROFILE_ENGINE_FIX.md`. Do not start
C1B or C2. C1A remains open until the corrected implementation and executable
harness independently reject the adversarial cases above.
