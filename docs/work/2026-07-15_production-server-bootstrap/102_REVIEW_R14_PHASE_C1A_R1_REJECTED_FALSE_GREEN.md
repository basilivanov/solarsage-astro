# R14 Phase C1A-R1 review — rejected: acceptance harness is false-green

## Verdict

C1A-R1 is **rejected**. The implementation improved the parser and added
rollback-looking code, but the independent acceptance does not pass and the
transaction still has destructive failure paths.

No production, network, SSH, database, Docker, systemd, commit or push action
was performed.

## Independent baseline (current worktree)

```text
test-prod-env-loader.sh                  rc=0
test-prod-env-profiles.sh                rc=2
test-prod-env-profiles-mutations.sh      rc=0  (not meaningful proof)
test-prod-deploy-source-loader.sh        rc=0, 111/111
test-prod-host-offsite-routing.sh        rc=0
```

`test-prod-env-profiles.sh` stops at its first expected nonzero CLI case:

```text
stdout final: === 1. Exact CLI ===
rc=2
```

The coder's acceptance command piped each test through `tail -3` without
`pipefail`; `tail` returned zero and hid the failing test. Therefore the
reported `38/38` was not an execution result.

## P0 findings

### 1. Commit failure can delete every live profile

`prod-env-prepare.sh` calls `rollback_profiles` in the `mv` error branch, then
immediately calls `cleanup_snapshot`, then exits. The global EXIT trap runs
again while `ROLLBACK_ACTIVE=1`; with an empty `SNAPSHOT_DIR`, its loop treats
every profile as previously absent and removes all seven destinations.

The rollback function itself contains `|| true` for copy, chown, chmod and
directory fsync (`scripts/prod-env-prepare.sh:59-76`). It never verifies the
restored bytes or metadata.

Independent sandbox with a synthetic failure on the third `mv`:

```text
current_apply_mv3_rc=1 old=0 changed=0 absent=7 mv_calls=3
```

The seven live profile files were all removed. The error even reported the
wrong profile name because the rollback loop overwrote the `fname` variable.

### 2. Signal/rollback contract is still broken

Signal traps call `exit 129/130/143`, but the EXIT trap unconditionally executes
`exit 1` (`prod-env-prepare.sh:78-81`). A signal therefore cannot preserve its
required status. Rollback failures are swallowed, and the snapshot is deleted
regardless of recovery success.

### 3. Main harness cannot test the new path

With `set -e`, all expected nonzero commands in lines 65-72 and throughout the
harness terminate the script before `assert_rc` runs. The apply sandbox also
does not copy the Python tool to the path produced by the rewritten prepare
script, and `write_full_source > "$MOCK_SOURCE"` does not write the source
there (the function writes a different fixed path). The apply/rollback section
is consequently unreachable in a correct execution.

## P1 findings

### 4. Domain option is accepted but ignored

`parse_cli` checks only that `--domain` exists; `parse_source()` has no domain
argument and never compares it. Independent result:

```text
wrong_domain_rc=0
```

### 5. Non-run `--` and extra command material are silently accepted

`validate ... -- ignored` returns zero. The `--` separator must be rejected for
all subcommands except `run`.

### 6. Exact boolean contract is weakened

`TRUE` is accepted because flags are lowercased before comparison. The contract
requires literal lowercase `true|false`.

```text
uppercase_boolean_rc=0
```

### 7. Oversized source is truncated and can hide forbidden data

`parse_source()` performs one `os.read(fd, 1024*1024)` and does not verify EOF or
file size. A 1,048,588-byte synthetic source with a valid first MiB followed by
`PATH=attack` returned zero:

```text
oversized_source_with_hidden_PATH_rc=0
```

### 8. Canonical profile format is not enforced on final LF/ordering/escapes

`deserialize_envfile()` accepts a profile with its final LF removed:

```text
missing_profile_final_lf_rc=0
```

It also accepts unknown backslash escapes and does not enforce canonical sorted
order. The independent serializer reference parser is missing.

### 9. Mutation harness does not prove that a test catches a mutation

`test-prod-env-profiles-mutations.sh` often runs a mutated tool directly on a
valid source and expects the mutated bad result. Examples:

- removing the required-key check is tested with all required keys present;
- duplicate-option mutation is invoked without duplicate options;
- serializer mutation is never checked by an external parser;
- the harness itself is never run against the mutated implementation.

All eight rows can therefore be green while the real regression tests would not
detect the mutation. This is a mutation-report false positive, not coverage.

## Required next task

Implement `103_TZ_R14_PHASE_C1A_R2_TRANSACTION_AND_HARNESS_FIX.md`. Do not start
C1B/C2. Re-run the actual scripts directly, never through a `tail` pipeline
without `pipefail`.
