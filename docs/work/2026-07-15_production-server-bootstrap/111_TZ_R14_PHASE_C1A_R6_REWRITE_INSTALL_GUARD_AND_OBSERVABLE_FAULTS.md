# R14 Phase C1A-R6 — rewrite install guard and use observable fault oracles

## Scope freeze

Keep the current immutable generations/current-symlink architecture and the
green parser/profile tests. Rewrite only `cmd_install_set` transaction control,
its rollback/cleanup helpers, and the transaction/fault tests. No C1B/C2,
production/network/SSH/DB/Docker/systemd mutation, commit or push.

Read `110_REVIEW_R14_PHASE_C1A_R5_REJECTED_ONE_GUARD_NOT_REAL.md` first.

## 1. Replace `cmd_install_set` wholesale

Do not patch the existing nested `try` incrementally. Replace the body after
source parsing with one state machine and one `try/except BaseException/finally`.

Required state:

```python
lock_fd = env_fd = gfd = None
old_handlers = None
staging_name = gen_name = current_tmp = None
generation_renamed = False
switched = False
previous_state = None
original_exception = None
```

Required order:

1. open/validate env dir and generations dir;
2. acquire canonical exclusive lock;
3. run `validate_housekeeping_clean`;
4. `read_current_state` (physical validation of previous target);
5. install signal handlers;
6. parse/render source profiles in-memory;
7. create/write/verify staging;
8. rename staging to immutable generation and fsync generations;
9. create/lchown/verify temp current symlink, replace current, set
   `switched=True`, fsync env dir;
10. verify current target and complete generation;
11. success cleanup/unlock/close.

The only transaction guard is:

```python
try:
    # all steps 5–10
except BaseException as original:
    # exactly one recovery path
    recover(original, state)
finally:
    # restore handlers, unlock, close every fd
```

No inner `except Exception` may wrap `TransactionSignal`. No `sys.exit()` inside
the transaction. `ToolError`, `TransactionSignal`, `OSError`, `KeyboardInterrupt`
and unexpected exceptions all enter the same recovery function.

After recovery, translate only in `main()`:

- successful recovery + `TransactionSignal` → exact 129/130/143;
- successful recovery + `ToolError` → original tool code;
- successful recovery + `OSError`/unexpected → stable IO/unexpected code;
- failed recovery → distinct recovery code and preserved artifact paths.

## 2. Recovery semantics

### Before `switched`

- remove current temp symlink if created;
- remove staging by its directory fd, verifying exact seven-file inventory;
- if renamed to generation, remove only that known generation after physical
  validation; if safe removal fails, preserve/report it;
- prove previous current target/absence unchanged.

### After `switched`

- `_rollback_current_strict` creates/lchowns a rollback temp symlink, atomically
  replaces current, fsyncs env dir, then calls `read_current_state` and proves
  the exact previous target (or absence on first install);
- rollback failure is never swallowed and never reported as original success;
- do not delete old/new generations on recovery failure.

Cleanup helpers return `None` only after verified success; otherwise raise a
recovery exception. Remove every `pass`/`|| true` from transaction cleanup.

## 3. Exact physical checks

Before install/check:

- current regular file, permission error or malformed link is a hard failure;
- current symlink owner/group equals env uid/gid;
- previous target generation owner/group/mode 0750 and exact seven-file set;
- each profile owner/group/mode 0640, regular, nlink=1;
- no direct legacy profile in env dir;
- no stale `.staging-*`, `.current-*`, `.rollback-*`, `.rb-*`;
- no noncanonical generation entries.

`check-installed` must use existing lock/generations only and make zero creates,
renames, chmod/chown, fsync or unlink operations.

## 4. Signal matrix

The handler must re-raise `TransactionSignal` unchanged through every helper.
Add pause mutations to a copied tool at all five points:

```text
SIG-PRE-DIR       after staging mkdir
SIG-PRE-WRITE     after first profile write
SIG-PRE-RENAME    after generation rename, before current switch
SIG-POST-SWITCH   immediately after current replace, before fsync
SIG-POST-VERIFY   before post-switch content verification
```

Run each HUP/INT/TERM. Assert exact 129/130/143, pointer old/absent, no temp
symlink/staging and no live generation corruption. Do not accept timeout 124 as
success; a timeout is a harness failure. Use a deterministic pause marker and
send the signal directly to the child PID.

## 5. Observable fault injection (no `pass` mutations)

The existing FI tests that replace a call with `pass` are invalid because a
missing durability/metadata operation may leave the same visible bytes.

For each FI case, mutate a copied tool to raise an explicit `OSError` or
`ToolError` at exactly one named boundary, then assert recovery. Required:

```text
FI01-FI07 each profile write/fchown/fchmod/final fsync -> no current change
FI08 generation fsync -> no current change
FI09 current replace -> old current unchanged
FI10 env-dir fsync after switch -> pointer rollback
FI11 post-switch target verify -> pointer rollback
FI12 post-switch content verify -> pointer rollback
FI13 rollback replace failure -> distinct recovery error + artifacts retained
```

The mutation application must verify exactly one replacement and compile. A
canonical fault oracle must be green before the mutation and red after it.

## 6. Mutation suite must be honest

Keep at least 12 observable transaction mutations. Do not report “detected” for
an unobservable fd leak or metadata removal. Either add an oracle that proves the
invariant (e.g. inspect `/proc/<pid>/fd`, exact mode/owner after install) or
replace the mutation with an observable weakening:

- current lstat removed;
- lock dir_fd removed;
- check O_CREAT introduced;
- lock contention ignored;
- housekeeping removed;
- generation inventory removed;
- previous-target validation removed;
- rollback call removed;
- rollback verification removed;
- signal status changed;
- ordinary OSError catch removed;
- safe diagnostic changed to traceback/value.

The mutation harness must exit nonzero if any listed mutation is not detected.
Handoff may not claim partial detection as acceptance.

## 7. Acceptance commands

Run directly, not through grep/tail pipelines:

```bash
bash -n scripts/lib/prod-env-loader.sh scripts/prod-env-prepare.sh \
  scripts/tests/test-prod-env-loader.sh scripts/tests/test-prod-env-profiles.sh \
  scripts/tests/test-prod-env-install-transaction.sh \
  scripts/tests/test-prod-env-profiles-mutations.sh
python3.12 -I -S -c 'compile(open("scripts/lib/prod-env-tool.py", "rb").read(), "scripts/lib/prod-env-tool.py", "exec")'
bash scripts/tests/test-prod-env-loader.sh
bash scripts/tests/test-prod-env-profiles.sh
bash scripts/tests/test-prod-env-install-transaction.sh
bash scripts/tests/test-prod-env-install-transaction.sh
bash scripts/tests/test-prod-env-profiles-mutations.sh
bash scripts/tests/test-prod-deploy-source-loader.sh
bash scripts/tests/test-prod-host-offsite-routing.sh
bash scripts/prod-infra-fingerprint.sh
git diff --check
```

Handoff must include every FI/SIG row with true rc and pointer/artifact state.
Stop after R6; no C1B/C2/commit/push.
