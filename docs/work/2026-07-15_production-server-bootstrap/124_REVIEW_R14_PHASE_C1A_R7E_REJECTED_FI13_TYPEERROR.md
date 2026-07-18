# R14 Phase C1A-R7E review — rejected: FI13 is a TypeError, not verification failure

## Verdict

Production FI08, first-install rollback, owner check and FI12 now pass direct
independent checks. R7E is still **rejected** because the FI13/FI08B harness
oracles are not honest.

## FI13 exact failure

The current mutation changes:

```python
cur_state = read_current_state(env_fd, gfd, uid, gid)
```

with a partial sed substitution that produces:

```python
cur_state = None(env_fd, gfd, uid, gid)
```

Direct result:

```text
SyntaxWarning: 'NoneType' object is not callable
rc=16
message=Error: recovery failed
```

This is a runtime TypeError caught by generic recovery wrapping. It does not
exercise the intended rollback full-state verification failure.

## FI helper is assertions-by-comment

`inject_fi_dual` asserts only `rc != 0`. Pointer expectations, rc16, artifact
existence/target and stderr basename exist only as comments. It will report
PASS for the wrong state.

FI08B still replaces cleanup with `pass`, not an explicit cleanup `OSError`,
and does not assert retained `.current-*` or retry failure.

Signal rows still remove the sandbox after only rc/current checks; SIG02 and
SIG05 are not at their specified exact boundaries.

Implement `125_TZ_R14_PHASE_C1A_R7F_HONEST_FINAL_HARNESS.md`. Production logic
should not be broadly refactored again; fix the final oracles and run direct
acceptance.
