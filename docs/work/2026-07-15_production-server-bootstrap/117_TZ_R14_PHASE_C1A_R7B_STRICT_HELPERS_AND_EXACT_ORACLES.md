# R14 Phase C1A-R7B — strict helpers and exact transaction oracles

## Scope and required reading

Read `116_REVIEW_R14_PHASE_C1A_R7A_REJECTED_SWALLOWED_RECOVERY.md` first.
Continue only C1A transaction/check/test work. No consumer/systemd/Docker/
deploy/production/network/SSH/DB changes, commit or push.

Preserve the now-working immediate post-mkdir HUP cleanup and parser/profile/B6
behavior. Stop only after complete direct acceptance.

## 1. Delete best-effort cleanup; introduce strict helpers

Delete the old unused `_rollback_current`, `_cleanup_staging` and
`_remove_generation` implementations. Do not leave `pass`-based alternatives.

Implement explicit helpers with contracts and GRACE function blocks:

```python
_unlink_temp_symlink_strict(env_fd, name, expected_target, uid, gid)
_remove_staging_strict(gfd, staging_name, created_files, uid, gid)
_remove_generation_strict(gfd, gen_name, expected_profiles, uid, gid)
_rollback_current_strict(env_fd, gfd, previous_state, rollback_name, uid, gid)
_close_transaction_resources(...)
```

Rules:

- catch only `FileNotFoundError` where absence is an explicitly valid final
  state; re-raise permission/type/inventory/fs errors as `RecoveryError`;
- never `except OSError: pass` in recovery;
- safe messages include only artifact basenames and operation names, for
  example `Error: recovery unlink failed: .current-<id>`;
- do not include raw exception text or secrets;
- after every cleanup, re-stat/re-list and prove the exact final state;
- fsync the owning directory after unlink/rmdir/rename.

For partial staging, track `created_files` immediately after each successful
file open. On cleanup require the staging directory inventory to equal exactly
that tracked set (a subset of the seven canonical names), validate each entry as
regular/nlink=1/expected owner, then unlink. A completed renamed generation
must have the exact seven-file inventory.

## 2. Make `cmd_install_set` structurally exact

Use one transaction state object/dict with all fds, created files and artifact
names. The active function must have:

```text
one try for mutation + post-switch verification
one except BaseException that calls strict recovery
one finally that restores handlers/unlocks/closes all resources
no pass
no sys.exit
```

Use `contextlib.ExitStack` or an equivalent explicit close collector so all
resources are attempted even when one close/unlock fails. Do not silently
discard finalization errors; convert them to a safe `RecoveryError`/I/O result
without preventing the remaining descriptors from being closed.

Set and use the same state fields consistently:

```text
staging_created, staging_fd, created_files,
generation_renamed, current_tmp, rollback_tmp, switched,
previous_state, new_generation
```

Return normally on success; `main()` owns exit translation. Remove
`sys.exit(EXIT_SUCCESS)` from `cmd_install_set`.

## 3. Exact rollback semantics and diagnostic

`_rollback_current_strict` must:

1. create the recorded rollback temp link;
2. lchown it to env uid/gid;
3. lstat/readlink and validate type, owner, group and exact previous target;
4. atomically replace current and fsync env dir;
5. call `read_current_state` and validate the complete previous generation, or
   prove exact absence for first install;
6. prove the rollback temp no longer exists.

If rollback replace/verify fails, return `EXIT_RECOVERY=16`, keep both
generations and any diagnostic temp link, and print the safe artifact basename:

```text
Error: recovery rollback failed: .rb-<32hex>
```

Never report the original ordinary I/O code after a recovery operation failed.

## 4. Full read-only check

Replace the weak current-link call with `read_current_state(env_fd, gfd, uid,
gid)`. Then validate expected profile bytes through the same
`validate_generation_physical(..., expected=...)` helper. This must reject a
current symlink with wrong uid/gid as well as extra inventory.

Make `validate_housekeeping_clean` fail on listdir/stat errors; it may not
return success after an `OSError`.

Add direct cases for:

```text
wrong current symlink owner/group -> nonzero
extra generation file -> nonzero
generation 0777 -> nonzero
stale current/staging/rb -> nonzero
valid check recursive metadata/content snapshot unchanged
```

## 5. FI cases must reach the named boundary

Refactor FI runner so each case owns a fresh `env` and baseline generation.
Use a replacement helper that checks the old snippet occurs exactly once before
writing the copied tool. Compile and run from the private sandbox cwd.

For every FI row assert exact rc, pointer, artifact names, generation inventory
and canonical retry/check outcome.

Required corrected cases:

- FI08: replace-current failure + successful cleanup -> rc 13, no `.current-*`,
  old pointer, canonical retry succeeds;
- FI08B: replace-current failure + temp-unlink failure -> rc 16,
  `.current-*` named in stderr and retained;
- FI09: post-switch env fsync failure -> old pointer restored;
- FI12: explicit post-switch fault plus rollback `os.replace` failure -> rc 16,
  new pointer retained, `.rb-*` retained and named;
- FI13: explicit post-switch fault plus rollback full-state verification
  failure -> rc 16 and retained diagnostic state.

Do not mutate all occurrences of `os.fsync(env_dir_fd)` or all occurrences of
`if vdata != fdata`. Do not count a pre-switch failure as FI12/FI13.

## 6. Signal cases at exact boundaries

Keep marker + direct PID signal delivery, but move the insertions:

```text
SIG01 immediately after `staging_created = True`, before staging open
SIG02 immediately after the first file write/fsync/close completes
SIG03 immediately after generation rename and state flag, before gfd fsync/current
SIG04 immediately after current replace + switched flag, before env fsync
SIG05 immediately before opening/reading the first post-switch profile
```

For each HUP/INT/TERM row, before deleting the sandbox assert:

- exact 129/130/143;
- old current/absence exact;
- no `.current-*`, `.rb-*`, `.rollback-*`, `.staging-*`;
- every live generation has canonical name/mode/owner/exact seven files;
- canonical `check-installed` and then canonical retry succeed;
- child is gone and lock can be acquired.

On marker failure, terminate/reap the child and preserve the sandbox path in the
failure message. Do not leave a 30-second sleeper behind.

## 7. Mutation harness isolation

Before each mutation, run the canonical transaction harness and require rc 0.
Apply exactly one mutation and require the copied harness to fail. Execute with
`cd "$sandbox"` so a broken `dir_fd` can never touch repository-root
`.profile.lock`. Snapshot the repository-root `.profile.lock` inode/mode/ctime
before and after the complete mutation suite and require no change.

## 8. Static gates before runtime acceptance

Add a small AST/static harness that fails unless:

- `cmd_install_set` contains no `Pass` node and no `sys.exit` call;
- it has a `finally`;
- production recovery helpers contain no swallowed `OSError`;
- the signal harness contains no `/usr/bin/timeout`, `--kill-after` or
  `kill ... || true`;
- each FI replacement reports an exact count of one.

## 9. Direct acceptance

Run all commands directly exactly as listed in R7A section 8. Development
timeouts are allowed only to diagnose hangs; the final acceptance and handoff
must not wrap successful commands in timeout/filter/tail pipelines. Include all
FI/SIG rows and static-gate output. Stop after handoff; no C1B/C2/commit/push.
