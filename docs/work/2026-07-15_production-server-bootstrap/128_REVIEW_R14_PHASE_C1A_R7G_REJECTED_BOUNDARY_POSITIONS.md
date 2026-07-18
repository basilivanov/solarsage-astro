# R14 Phase C1A-R7G review — rejected: two signal markers still misplaced

## Verdict

The production fault paths and ordinary suites are green. The final test tail
is still not accepted because its markers do not prove the requested boundaries
and the mutation runner has no exact-one gate.

## Evidence

Current test expressions:

```text
SIG02: after “Reopen and verify all profiles in staging” comment
       (before the first profile write verification, not after write/fsync/close)
SIG05: after os.close(ngfd)
       (after all post-switch profile reads, not before the first one)
```

The mutation runner still does only `cmp -s` and runs the copied harness; it
does not prove one source replacement or a canonical baseline before mutation.

Do not report the current timeout/filter run as final direct evidence.

Implement `129_TZ_R14_PHASE_C1A_R7H_FINAL_MARKERS_AND_MUTATION_GATE.md`.
