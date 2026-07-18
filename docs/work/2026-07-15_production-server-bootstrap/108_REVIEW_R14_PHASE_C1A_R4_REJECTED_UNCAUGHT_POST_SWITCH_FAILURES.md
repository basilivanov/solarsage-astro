# R14 Phase C1A-R4 review — rejected: ordinary post-switch failures bypass rollback

## Verdict

R4 fixed canonical lock placement, lock contention and fresh-check mutation.
The immutable transaction is still **rejected** because ordinary `OSError`
after the atomic switch bypasses rollback, and physical generation validation
is incomplete.

No production/network/SSH/DB/Docker/systemd mutation, commit or push occurred.

## Genuine baseline

```text
test-prod-env-loader.sh             rc=0
test-prod-env-profiles.sh           rc=0, 75/75
test-prod-env-profiles-mutations.sh rc=0, old 8/8
test-prod-deploy-source-loader.sh   rc=0, 111/111
```

## Fixed since R3

Independent proof:

```text
lock_in_cwd=no lock_in_env=yes lock_mode=640
check_while_lock_rc=13
fresh_check_rc=14 before=source.env after=source.env
toolerror_post_switch_rc=14 current=absent
```

These improvements are retained.

## Remaining blockers

### P0.1 Ordinary `OSError` after switch leaves unverified current

The outer transaction catches only `(ToolError, TransactionSignal)`. Direct
filesystem `OSError` from symlink/fsync/open/read paths reaches `main()` generic
error without pointer rollback.

```text
oserror_post_switch_rc=1
current=generations/gen-<new-id>
```

### P0.2 Existing regular `current` is treated as absent and overwritten

`_validate_current_link` maps every `readlink` error to `None`, not only ENOENT.

```text
install_with_regular_current_rc=0 current_type=symlink
```

This destroys unexpected operator state instead of failing closed.

### P0.3 Pre-switch signal can lose exact signal status

`TransactionSignal` raised inside the inner staging `try` is caught by
`except Exception`, cleaned, then wrapped as `ToolError(EXIT_IO)`.

```text
inner_pre_switch_TERM_rc=13 current=absent staging=0
```

The required result is 143.

### P1.1 Generation physical contract still accepts corruption

```text
check_extra_and_mode777_rc=0
```

Generation directory metadata and exact inventory are not checked.

### P1.2 Rollback/cleanup remain best-effort

`_rollback_current`, `_cleanup_staging` and `_remove_generation` return success or
swallow errors without verifying final state. Current symlink owner, previous
rollback generation and stale temp entries are not validated.

### P1.3 Test coverage was not implemented

The main harness is still 75 cases and its only rollback scenario is a
pre-validation failure. The mutation harness remains the old eight direct
behavior rows; it has no lock, pointer, fsync, OSError, rollback or signal case.

## Required correction

Implement `109_TZ_R14_PHASE_C1A_R5_TRANSACTION_CORE_AND_FAULT_HARNESS.md` only.
Parser/profile work outside listed residuals is frozen.
