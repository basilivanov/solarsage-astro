# R14 Phase C1A-R7F — honest final FI/signal harness

## Scope

Read review 124. Preserve the now-working production transaction logic. Change
only narrow recovery diagnostic text if needed and the two C1A harnesses. No
production state, C1B/C2, commit or push.

## 1. Fix FI13 mutation exactly

Do not create `None(...)`. Replace one unique verification condition or line so
the rollback pointer replacement succeeds and then only the rollback
verification raises a `RecoveryError` naming `rollback_name`.

Assert:

```text
mutation count for each edit = 1
compile has no warning/error
rc = 16
current after = old current
both old and diagnostic new generation remain valid
no unexpected .current-* or staging
stderr contains safe rollback artifact/state identifier
```

## 2. FI08B explicit cleanup failure

Keep the current-replace fault, but inject explicit `OSError` at the unique
`os.unlink(name, dir_fd=env_fd)` inside `_unlink_temp_symlink_strict`; do not
replace anything with `pass`.

Assert rc16, old pointer, one retained `.current-*`, stderr contains its exact
basename, and a canonical retry fails closed on that artifact.

## 3. Make dual runner enforce expectations

Pass expected rc and pointer mode (`old|new`) into `inject_fi_dual`. Capture
stderr. Assert artifact glob count, symlink target, both generation inventories
and expected retry/check result. A comment is not an assertion.

Each source edit must verify old-snippet count exactly one before replacement.
Remove `rm -rf ... || true`; cleanup failure fails the harness after printing
the sandbox path.

## 4. Finish signal boundary/postcondition proof

- SIG02 marker goes after first profile fsync+close, not before write.
- SIG05 marker goes immediately before first post-switch profile open/read.
- Before deleting each sandbox assert no transaction temp/staging/rollback
  artifacts, exact generation inventory, canonical check success, canonical
  retry success and dead child/unlocked lock.
- Marker failure must kill/reap child and fail with the preserved sandbox path.

## 5. Mutation runner

Assert exactly one source replacement per mutation and run a canonical green
baseline before the mutated copy. Keep sandbox cwd and repository lock snapshot.

## 6. Direct acceptance

Run the complete acceptance list directly, including transaction twice. Handoff
must print FI08/FI08B/FI12/FI13 exact rc, pointer, artifact and stderr assertions
and SIG postconditions. No timeout/filter final evidence. Stop afterward.
