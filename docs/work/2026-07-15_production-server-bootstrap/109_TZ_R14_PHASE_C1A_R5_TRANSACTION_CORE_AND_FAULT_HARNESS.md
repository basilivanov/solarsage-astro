# R14 Phase C1A-R5 — transaction core and dedicated fault harness only

## Narrow scope

Do not redesign profiles or parser again. Preserve the green 75/75 parser
baseline and immutable-generation architecture. Work only on:

1. transaction/path validation in `scripts/lib/prod-env-tool.py`;
2. a new dedicated `scripts/tests/test-prod-env-install-transaction.sh`;
3. replacement of `scripts/tests/test-prod-env-profiles-mutations.sh` with real
   transaction-aware mutation oracles;
4. minimal profile harness updates needed to invoke the new dedicated harness.

Read `108_REVIEW_R14_PHASE_C1A_R4_REJECTED_UNCAUGHT_POST_SWITCH_FAILURES.md`.
No C1B/C2, prod/network/SSH/DB/Docker/systemd mutation, commit or push.

## 1. One transaction guard catches every failure

Remove nested catch blocks that reclassify `TransactionSignal`. Structure
install around one guarded state machine:

```python
state = TransactionState(...)
try:
    install_handlers()
    validate_clean_prestate()
    build_and_verify_generation()
    switch_current()
    verify_new_current()
except BaseException as original:
    recover_according_to_state(original)
    raise normalize_after_recovery(original)
finally:
    restore_handlers()
    unlock_if_locked()
    close_all_fds()
```

Do not catch and wrap `TransactionSignal` inside staging. Do not call
`sys.exit()` inside transaction functions. `main()` alone translates:

- `ToolError.code`;
- `TransactionSignal.exit_code`;
- unexpected `OSError` normalized to stable `EXIT_IO` **after recovery**;
- other unexpected exception normalized to `EXIT_UNEXPECTED` after recovery.

Any exception after `switched=True`, including direct `OSError`, must call the
same pointer rollback and verify it before return.

## 2. Exact prestate helpers

Implement and use these semantic helpers (names may differ, behavior may not):

### `read_current_state(env_fd, generations_fd, uid, gid)`

- `lstat("current", follow_symlinks=False, dir_fd=env_fd)`;
- only ENOENT means absent;
- otherwise require symlink, uid/gid exact;
- `readlink` target exact `generations/gen-[0-9a-f]{32}`;
- open only `gen-<id>` via already validated generations fd;
- call physical generation validator;
- return exact target and generation id.

Regular current, permission error, malformed target or missing/corrupt target is
nonzero and is never overwritten.

### `validate_generation_physical(gfd, gen_name, uid, gid, expected=None)`

- directory opened O_DIRECTORY|O_NOFOLLOW by gfd;
- uid/gid exact, mode 0750;
- `os.listdir(gen_fd)` exact set equals seven profile filenames;
- each profile regular, nlink=1, uid/gid, mode 0640;
- bounded complete read;
- if `expected` supplied, byte-exact content match;
- no extra file/subdirectory/symlink.

Use it for previous rollback target, staging/new generation and check-installed.

### `validate_housekeeping_clean(env_fd, generations_fd)`

Reject before install/check:

- direct legacy `api.env`/other profile files in env dir;
- `.current-*`, `.rollback-*`, `.rb-*` in env dir;
- `.staging-*` in generations;
- noncanonical entries in generations other than `gen-[0-9a-f]{32}`.

Do not silently delete stale state.

## 3. Exact lock/generations metadata on both paths

`check-installed` validates, without changing:

- generations uid/gid/mode 0750;
- lock regular/nlink=1/uid/gid/mode 0640.

Install creation of lock/generations fsyncs the new entry's parent directory.
Remove dead placeholder expressions such as `... if False else None`.

## 4. Durable generation build

- Maintain a registry of every open fd and close it in `finally`.
- Full write loop.
- fchown/fchmod, then final file fsync.
- Exact staging inventory and metadata/content validation before rename.
- Rename staging to gen, fsync generations.
- If pre-switch failure occurs after rename, safely remove the known new
  generation only if exact validation permits; otherwise preserve and report a
  recovery path/code.
- Cleanup functions return a verified result or raise recovery error; no `pass`
  on unlink/rmdir/fsync failures.

## 5. Switch and rollback proof

Before replacing current:

- create temp symlink by env fd;
- lchown temp symlink to uid/gid with `follow_symlinks=False`;
- lstat/readlink validate it;
- replace current, set `switched=True`, fsync env dir.

Post-switch validates current symlink ownership/target and new generation exact
inventory/content.

Rollback:

- previous target: create/lchown/validate rollback symlink, replace current,
  fsync, then call `read_current_state` and prove exact previous target;
- first install: unlink current, fsync, lstat proves ENOENT;
- any rollback failure produces a distinct recovery error and retains both
  generation dirs; never claims original error only.

Clean current temp symlink on pre-switch failure. No error path may leave a
hidden temp without reporting recovery state.

## 6. Signals

Handlers remain installed for the full transaction. `TransactionSignal` must be
re-raised unchanged through all inner helpers.

Dedicated tests inject pauses at:

1. after staging dir creation;
2. after first profile write;
3. after generation rename but before current switch;
4. after current replace but before fsync;
5. during post-switch verification.

For HUP/INT/TERM assert exact 129/130/143, old/absent current and no orphan
staging/current-temp. A rollback-failure mutation must instead return recovery
error and preserve artifacts.

## 7. Dedicated executable fault harness

Create `scripts/tests/test-prod-env-install-transaction.sh` with isolated temp
dirs and no production hooks. It runs canonical success cases directly and
verified sandbox-code mutations for fault boundaries.

Mandatory canonical cases:

```text
TX01 first install
TX02 repeat install, old generation retained/unchanged
TX03 check read-only byte+metadata+entry snapshot
TX04 lock path/mode/owner and no cwd lock
TX05 exclusive lock blocks check/install
TX06 regular current rejected/unchanged
TX07 malformed/traversal current rejected
TX08 previous generation mode/extra/profile symlink/hardlink rejected
TX09 stale staging/current-temp/direct legacy rejected
TX10 fresh check creates nothing
```

Mandatory injected cases:

```text
FI01-FI07 failure at each profile write/final fsync
FI08 generation-dir fsync
FI09 current replace
FI10 env-dir fsync after replace (ordinary OSError)
FI11 post-switch target verify
FI12 post-switch content verify
FI13 rollback replace failure -> recovery error + artifacts preserved
SIG01-SIG15 HUP/INT/TERM at five boundaries
```

For every FI/SIG report rc, previous target, final target, staging/temp counts and
generation inventory. The test fails on mixed/unverified state.

The harness must not depend on root. Lower-level Python derives sandbox uid/gid;
test the shell wrapper separately with narrow `id/stat` shims only.

## 8. Replace mutation harness

At least 12 cases. Each mutation has:

1. exact occurrence count = 1;
2. syntax valid;
3. canonical fault oracle green on original;
4. same oracle red on mutated copy.

Cover lock dir_fd, check O_CREAT, lock contention, current ENOENT distinction,
exact inventory, full write, final fsync, catching OSError, post-switch rollback,
rollback verify, signal preservation and safe error output.

The existing eight direct-command rows are not acceptable and must be removed,
not merely retained beside new rows.

## 9. Small residual engine fixes in scope

- named `validate --profile X` must call `render_profile(parsed, X)`;
- canonical deserializer rejects interior blank lines and dangling backslash;
- bounded complete read for legacy `verify_profile`;
- shell wrapper preserves safe stderr (remove `2>/dev/null`).

## 10. Acceptance

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

Direct rc capture only. Handoff must list TX/FI/SIG IDs and recovery evidence.
Stop after R5; no C1B/C2/commit/push.
