# R14 Phase C1A-R7F review — rejected: signal and mutation postconditions missing

## Verdict

The core production recovery paths now pass independent FI08, first-install,
owner-check and FI12 checks. R7F is still **rejected only at the harness layer**.

## Remaining exact gaps

- SIG02 marker is still inserted after `data = ...`, before the first write;
  required boundary is after first write/fsync/close.
- SIG05 marker is still inserted at `os.close(ngfd)`, after all post-switch
  content verification; required boundary is before first post-switch profile
  open/read.
- `sig_test` asserts only rc/current and immediately removes the sandbox. It
  does not assert transaction artifact absence, generation inventory,
  canonical check/retry, dead child or unlocked lock.
- marker-not-found calls `fail` without killing/reaping the sleeping child.
- mutation runner checks only byte inequality, not one exact replacement, and
  has no canonical green baseline gate.

FI13 no longer creates `None(...)`; preserve that correction. FI08/FI08B/FI12
production semantics must not be refactored again.

Implement `127_TZ_R14_PHASE_C1A_R7G_FINAL_TEST_TAIL_ONLY.md`.
