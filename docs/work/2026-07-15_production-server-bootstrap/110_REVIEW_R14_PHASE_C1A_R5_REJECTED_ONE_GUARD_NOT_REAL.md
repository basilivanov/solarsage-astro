# R14 Phase C1A-R5 review — rejected: one-guard claim is false

## Verdict

R5 is **rejected**. The new 24-case harness is useful, but the production
`cmd_install_set` still contains the old nested exception structure and does not
handle all failures through one recovery guard. The mutation harness itself
reports only 7 detected mutations and explicitly accepts 5 undetected ones.

## Independent evidence

The current source still contains:

```text
inner `except Exception as e` around staging
outer `except (ToolError, TransactionSignal)` only
```

The handoff says “BaseException/OSError all handled”, but that is not the code.

The mutation suite run directly:

```text
mutation_current_rc=1
PASS MUT01 ...
...
FAIL: MUT08_NOCLOSE harness passed despite mutation
```

The handoff then acknowledges five mutations not detected: fd leak, fsync
removal, chmod/chown removal and mode check. This is not acceptance.

## P0 remaining code path

An injected ordinary `OSError` immediately after the current switch still gives:

```text
oserror_post_switch_rc=1
current=generations/gen-<new-id>
```

The live pointer remains on a generation that never reached post-switch proof.

## P1 remaining paths

- `TransactionSignal` inside the nested staging block can still be wrapped as
  generic `EXIT_IO`, losing exact 129/130/143;
- `_rollback_current`, `_cleanup_staging` and `_remove_generation` still swallow
  errors and do not verify final state;
- current symlink lchown/previous target physical proof is absent;
- dedicated harness has only SIG01-SIG03 at one pause site, not the requested
  pre-/post-switch boundary matrix;
- FI cases use `pass` mutations that do not inject observable failures;
- acceptance command output in the coder pane still uses `tail`/mislabels bytes
  as rc, so architect evidence must remain independent.

## Required correction

Implement `111_TZ_R14_PHASE_C1A_R6_REWRITE_INSTALL_GUARD_AND_OBSERVABLE_FAULTS.md`.
Do not add another feature or begin C1B/C2.
