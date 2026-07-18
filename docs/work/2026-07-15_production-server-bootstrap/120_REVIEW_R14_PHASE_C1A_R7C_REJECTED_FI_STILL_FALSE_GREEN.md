# R14 Phase C1A-R7C review — rejected: FI12/FI13 still false-green

## Verdict

R7C is **rejected**. The direct transaction suite reports 37/37, but the named
rollback fault cases are not the cases they claim to be.

## Independent direct output

```text
PASS: FI12 post-switch+rollback replace fail (rc=13)
PASS: FI13 post-switch+rollback verify fail (rc=13)
```

The current harness definitions are identical:

```text
FI12: insert `raise OSError("post_switch")` after `switched = True`
FI13: insert `raise OSError("post_switch")` after `switched = True`
```

Neither mutates `_rollback_current_strict`'s `os.replace(rollback_name, ...)`
nor its full-state verification. Both only exercise the ordinary post-switch
failure path, and both return the ordinary `EXIT_IO=13`. This is not evidence
for the required dedicated recovery path.

FI08B has the same problem: it replaces cleanup with `pass`, then asserts only
`rc != 0` and unchanged pointer. It does not assert `EXIT_RECOVERY=16`, the
retained `.current-*` artifact or its safe diagnostic basename.

The active transaction still contains:

```text
try: os.unlink(current_tmp, ...)
except OSError: pass
```

so a cleanup failure is still swallowed in production code.

Signal rows still assert only rc/current and delete the sandbox; they do not
prove temp/staging/rollback inventory, generation integrity or canonical retry.

## Required continuation

Implement `121_TZ_R14_PHASE_C1A_R7D_FINAL_FAULT_ORACLES.md`. Do not hand off on
the 37 count until FI12/FI13 have distinct, exact mutations and artifact
assertions.
