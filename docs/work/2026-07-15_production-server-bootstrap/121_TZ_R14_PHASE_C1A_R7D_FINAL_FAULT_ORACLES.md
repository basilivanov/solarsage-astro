# R14 Phase C1A-R7D — final strict cleanup and rollback fault oracles

## Scope

Read review 120. Change only `prod-env-tool.py` and the two C1A transaction/
mutation harnesses. No production, consumers, C1B/C2, commit or push.

## 1. Remove the last swallowed production cleanup

Replace the active inline current-temp unlink with
`_unlink_temp_symlink_strict(env_fd, current_tmp, symlink_target, uid, gid)`.
Update that helper to validate exact symlink type, uid, gid and target before
unlink. Catch only `FileNotFoundError` as an already-absent success; every other
failure is `RecoveryError` naming `.current-<id>`.

Remove dead `sfd_open`. In first-install rollback, do not attempt to unlink a
rollback temp that was never created; if checking a possible temp, catch only
ENOENT and raise for every other error. Compare recovered current target exactly
to `previous_state[0]`, not merely non-None.

## 2. FI12 must mutate rollback replace, not ordinary fault only

Create a fresh copied tool and apply **two exact one-count edits**:

1. insert an explicit post-switch `OSError` after the unique `switched=True`;
2. replace the unique rollback
   `os.replace(rollback_name, "current", src_dir_fd=env_fd, dst_dir_fd=env_fd)`
   with explicit `OSError("rollback_replace")`.

Assert exactly:

```text
rc=16
current=new generation (rollback did not happen)
.rb-<id> exists and points to old generation
stderr names that .rb-<id>
old and new generations both remain physically valid
```

## 3. FI13 must mutate rollback verification

Fresh copy, two exact one-count edits:

1. same explicit post-switch fault;
2. force only the unique comparison/full-state verification after rollback to
   raise `RecoveryError("...<rollback basename>...")`.

Assert `rc=16`, actual pointer state after replacement, both generations,
artifact/diagnostic semantics and no claim of ordinary rc13. FI13 source bytes
must differ from FI12 source bytes.

## 4. FI08B exact assertions

Inject current replace failure plus explicit cleanup unlink `OSError` (not
`pass`). Assert exact rc16, old pointer, retained `.current-*`, stderr basename,
and that canonical retry fails closed because the diagnostic artifact remains.

Each FI sandbox is fresh. Mutation helper must assert each old snippet count is
exactly one before replacement and print the counts.

## 5. Signal postconditions

Before `rm -rf "$td"`, assert no `.current-*`, `.rb-*`, `.rollback-*` or
`.staging-*`; validate canonical generation inventory; run canonical
`check-installed`, then a canonical retry; verify child is gone and lock is
obtainable. Move SIG02 after first file close and SIG05 before the first
post-switch profile open/read.

On marker failure, kill/reap child and remove/preserve the temp path explicitly;
no `/tmp/sig.*` may survive.

## 6. Final gate

Directly run the complete acceptance list. Handoff must include FI08B/FI12/FI13
exact rc, pointer, artifact and stderr basename plus two direct transaction
runs and mutation 12/12. No timeout/filter pipeline in final evidence. Stop.
