# R14 Phase C1A-R7C — first-install rollback and exact fault boundaries

## Scope

Read review 118 and preserve all valid parser/profile/check fixes. Only modify
the C1A tool and isolated transaction/mutation harnesses. No production,
consumer, systemd, Docker, deploy, commit or push changes.

## 1. Fix first-install rollback before anything else

In `_rollback_current_strict` branch on `previous_state is None`:

```text
do not create a rollback symlink;
unlink current only if it is the new transaction pointer;
fsync env dir;
prove current is absent with lstat;
remove any rollback temp name if one was already created;
return success only after absence is verified.
```

Add a fresh-sandbox test:

1. no current/generation exists;
2. inject a fault immediately after current switch;
3. assert mapped original failure after successful recovery;
4. assert `current` is absent, no `.rb-*`/`.current-*` remains, and a normal
   canonical install succeeds afterward.

The literal string `absent_marker` must not exist in production transaction
code.

## 2. Isolate exact FI boundaries

Replace broad `sed` substitutions with a helper that edits a copied tool using
an exact old snippet and asserts replacement count exactly one. Each FI gets a
fresh env and a canonical baseline install where appropriate.

Required isolated cases:

```text
FI08 replace current -> explicit OSError at the one current replace call;
       successful cleanup: old pointer, no .current-*, retry succeeds.
FI08B same fault plus explicit cleanup unlink OSError;
       rc=16, old pointer, .current-* retained and named.
FI09 post-switch env fsync -> old pointer restored, ordinary rc.
FI12 explicit post-switch fault + only rollback os.replace failure;
       rc=16, new current retained, .rb-* retained and named.
FI13 explicit post-switch fault + only rollback verification failure;
       rc=16, artifact state retained and named.
```

Do not replace every `os.fsync(env_dir_fd)` or every content comparison. The
test output must show one replacement count per row and the true rc.

## 3. Strict cleanup requirements

Remove the remaining active `except OSError: pass` around `current_tmp` unlink.
Only an explicitly checked `ENOENT` may be treated as already-clean; any other
unlink/lstat/rmdir/fsync error is a `RecoveryError` with the artifact basename.
The old best-effort helper definitions must stay deleted, not merely unused.

Rollback verification must use full physical state, including exact previous
generation inventory/content, and cleanup must close every descriptor exactly
once. Do not leave `sfd_open` as dead state.

## 4. Signal and mutation harness acceptance

Keep marker/direct-PID delivery, but add the first-install signal branch and
assert artifact inventory before deleting each sandbox. On marker timeout,
terminate/reap the child and fail; never leave `/tmp/sig.*` behind.

Mutation harness must `cd` into its private sandbox, snapshot the repository
root `.profile.lock` before/after, assert one replacement and run a green
canonical baseline before every mutation.

## 5. Direct handoff gate

Do not hand off on `36/36` alone. Run the complete direct acceptance list from
R7A plus all FI08B/FI12/FI13 and first-install rows. Include exact rc, pointer,
artifact and retry state. Stop after handoff; no C1B/C2/commit/push.
