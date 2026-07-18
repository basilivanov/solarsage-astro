# R14 Phase C1A-R7A review — rejected: recovery still swallows failures

## Verdict

R7A is **rejected**. The immediate post-mkdir signal cleanup is now fixed and
the dedicated recovery exit code exists, but active recovery still suppresses
errors and the test harness does not reach several named boundaries.

No C1B/C2, production mutation, commit or push.

## Independent results on fresh sandboxes

### Cleanup failure is reported as ordinary I/O and leaves `.current-*`

Injected failures:

1. `os.replace(current_tmp, "current", ...)` raises;
2. recovery's `os.unlink(current_tmp, ...)` also raises.

Observed:

```text
rc=13
current remained old
artifact=.current-<id>
message=Error: transaction I/O failure
```

The cleanup exception is swallowed by `except OSError: pass`; the transaction
then rethrows only the original replace error. This is exactly the unsafe
best-effort behavior R7A was supposed to remove. It must be `EXIT_RECOVERY=16`
with the safe artifact basename in the diagnostic.

### Real rollback-replace failure has no artifact diagnostic

Injected a failure immediately after `switched=True`, then a failure at the
rollback `os.replace`.

Observed:

```text
rc=16
current before=old generation
current after=new generation
artifact=.rb-<id> -> old generation
message=Error: recovery failed
```

The distinct code is correct, but the required safe artifact path is missing.
The handoff's FI12 is not this case: it mutates every env-dir fsync, allowing the
rollback replace itself to succeed before the injected recovery fsync error.

### `check-installed` ignores current symlink owner

After a valid install I changed only `current` symlink ownership to `root:root`
while the sandbox env owner remained `astro:astro`.

Observed:

```text
check-installed rc=0
check: OK gen-<id>
```

The check still calls `_validate_current_link`, which validates type/target but
not owner/group. It must call the full `read_current_state` validator.

### SIG-PRE-DIR now passes

An independent marker immediately after staging mkdir plus direct SIGHUP gave:

```text
rc=129; old current preserved; no .staging-* artifact
```

Preserve this behavior. The repository harness still pauses later, at staging
`fchown`, so it does not prove the fixed boundary itself.

## Static blockers still present

The active `cmd_install_set` contains multiple:

```text
except OSError: pass
except Exception -> RecoveryError
sys.exit(EXIT_SUCCESS)
```

and the old unused best-effort cleanup helpers remain. `sfd_open` is recorded
but not used to drive exact cleanup. `rollback_tmp` is initialized but the
recovery uses a different local name. Rollback verification uses the weak link
validator rather than the full physical validator.

The FI harness still shares one mutable environment, asserts no exact
replacement count, no artifact inventory and no canonical retry. FI13 replaces
both staging and post-switch content comparisons, so it fails before switch.

Signal boundary mismatches remain:

- SIG01 is after staging fd/fchown, not immediately after mkdir;
- SIG02 is before first write, not after first completed write;
- SIG05 is after all content verification, not immediately before it;
- no signal row checks temp/staging/rollback artifacts or live generation
  inventory before deleting the sandbox.

Implement `117_TZ_R14_PHASE_C1A_R7B_STRICT_HELPERS_AND_EXACT_ORACLES.md`.
