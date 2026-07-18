# R14 Phase C1A-R7B review — rejected: first-install rollback corrupts `current`

## Verdict

R7B remains **rejected**. The ordinary 36-case transaction harness is green,
but a fresh first-install post-switch fault leaves an invalid canonical pointer.

## P0: first-install rollback creates `current -> absent_marker`

On a fresh env with no previous generation/current, I injected an explicit
failure immediately after `switched = True`.

Observed:

```text
rc=16
current -> absent_marker
message=Error: recovery rollback verification failed
```

The new `_rollback_current_strict` always creates a rollback symlink using
`previous_target or "absent_marker"`. For a first install it must remove
`current`, fsync the env directory and prove absence; `absent_marker` is not a
canonical target and is a persistent broken state.

The existing SIG/FI rows all start with a successful install, so they cannot
detect this first-install branch.

## Additional evidence

- The direct `check-installed` owner mismatch is now correctly rejected; keep
  that fix.
- The direct transaction suite reports 36/36, but FI12's `sed` replacement
  changes multiple `os.fsync(env_dir_fd)` occurrences and does not isolate the
  rollback-replace call. A green/nonzero result is not proof of FI12.
- The mutation harness still runs from the repository cwd and does not assert
  exact replacement count or a per-case canonical baseline.

## Required continuation

Implement `119_TZ_R14_PHASE_C1A_R7C_FIRST_INSTALL_AND_EXACT_FAULTS.md` before
any acceptance claim.
