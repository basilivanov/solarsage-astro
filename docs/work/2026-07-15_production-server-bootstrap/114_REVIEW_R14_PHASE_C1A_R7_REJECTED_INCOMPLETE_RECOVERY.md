# R14 Phase C1A-R7 review — rejected: incomplete recovery rewrite and false-green check

## Verdict

R7 is **rejected** and the task is not complete. The coder stopped after a
partial change and explicitly reported that the acceptance run timed out. The
source and harness still violate the R7 contract.

No C1B/C2, production mutation, commit or push.

## Independent evidence after the R7 handoff

On a fresh temporary environment:

```text
extra file in current generation + check-installed -> rc=0, check: OK
```

The read-only check still iterates expected profile names but does not reject
an extra generation entry. R7 requires an exact seven-file inventory.

I also injected a post-switch failure and a rollback-replace failure into a
fresh copy:

```text
rc=13
current before = generations/gen-<old>
current after  = generations/gen-<new>
diagnostic     = Error: recovery failed, manual recovery needed
leftover       = .rb-<id> -> generations/gen-<old>
```

This is still the new pointer after a failed rollback. The result is not a
dedicated recovery code and the message does not report the preserved artifact
paths.

The transaction source still contains, in the active path:

```text
except OSError: pass
except Exception as re
sys.exit(original.exit_code) inside cmd_install_set
no finally restoring handlers/unlocking/closing every fd
```

The old best-effort helper functions with swallowed errors also remain in the
module. Therefore the stated “strict recovery” is not the implementation that
is running.

The signal harness still contains:

```text
/usr/bin/timeout ... --signal ... --kill-after ...
```

and fixed `sleep(30)` mutations. This directly contradicts the R7 requirement
for a deterministic marker and direct signal delivery with timeout treated as a
harness failure, not as a fallback success.

The coder's own handoff says:

```text
Acceptance ran (first 3 suites), remaining timed out at 700s
```

so the required acceptance set was not completed.

## What was fixed and must be preserved

The following partial fixes appear present and should not be regressed:

- `staging_created` is recorded after mkdir;
- pre-switch cleanup attempts to remove `current_tmp`;
- `check-installed` now checks several lock/generation metadata fields;
- the baseline loader/profile suites remain green.

These are not sufficient for acceptance while the blockers above remain.

## Required continuation

Implement `115_TZ_R14_PHASE_C1A_R7A_FINISH_STRICT_TRANSACTION_AND_HARNESS.md`.
The next handoff must contain direct command exit codes and complete FI/SIG
rows; “timed out”, filtered output, or a prose claim is not acceptance.
