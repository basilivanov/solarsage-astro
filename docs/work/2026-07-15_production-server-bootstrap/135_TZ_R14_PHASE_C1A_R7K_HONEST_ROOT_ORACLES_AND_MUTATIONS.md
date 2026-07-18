# R14 Phase C1A-R7K — make root:astro proof and ownership mutations fail-closed

## Scope

Read review 134. Modify only `scripts/lib/prod-env-tool.py` and C1A test
harnesses. No consumers, systemd, nginx, Docker, deploy sequence, production
host, commit, push, C1B, or C2.

## Production helper requirements

Keep the new fd-relative helper, but make it strict:

1. `os.symlink(target, name, dir_fd=env_fd)`;
2. `os.chown(name, uid, gid, follow_symlinks=False, dir_fd=env_fd)` (or an
   equivalent fd-relative `lchown`);
3. lstat/readlink through `env_fd` and verify type, uid, gid, and exact target;
4. on any failure, attempt exact-name cleanup and prove absence;
5. if cleanup/proof fails, raise `RecoveryError` with only the safe basename —
   never `pass`/swallow the unlink error.

Use it for both `.current-<id>` and `.rb-<id>`. The rollback helper must not
reintroduce a cwd-relative operation. Keep the full post-switch
`read_current_state` validation.

If the lchown itself fails before ownership is established, cleanup may verify
exact symlink type and exact transaction target without requiring the desired
owner (the name is unique and held under the locked env directory); after a
successful lchown, all normal cleanup must require the expected owner/group.

## Mandatory root identity test

Prefer a dedicated `scripts/tests/test-prod-env-root-identity.sh` so the proof
cannot be accidentally omitted from the ordinary astro:astro suite. It must:

- require `id -u = 0` and `getent group astro` (fail, never skip, when invoked);
- install a private env/source owned exactly `root:astro`, mode 0750/0640;
- trap cleanup on every exit and use a private temp root;
- assert first install rc=0, `current` owner `root:astro`, canonical target,
  every generation/profile/lock owner and mode, and check-installed rc=0;
- assert second install/check rc=0 and no temp/staging/rollback artifacts;
- use `chown` without `|| true` and fail closed on any setup operation.

Record its direct rc and postconditions in the handoff. The final acceptance
must explicitly run it, for example:

```text
sudo -n env TOOL_OVERRIDE=/path/to/tool \
  bash scripts/tests/test-prod-env-root-identity.sh
```

If keeping the block in the transaction harness, the final command must set
`ROOT_IDENTITY_TEST=1` and the handoff must show the `ROOT_A/B/C` output; a
default invocation without that variable is not evidence.

## Exact root fault oracles

Use fresh root:astro environments for every case, with traps and no shared
state.

### ROOT-B: current replace failure

Mutate exactly the active current `os.replace` call to raise `OSError`. Assert:

- exact ordinary transaction I/O rc (the documented `EXIT_IO`, not any nonzero);
- old current target and owner unchanged;
- no `.current-*`, `.staging-*`, or unreferenced new generation remains;
- stderr starts with a safe `Error:` and contains no traceback/secret;
- canonical retry and check-installed both return 0.

Add a paired cleanup-failure case that also makes the exact unlink fail. Assert
`EXIT_RECOVERY=16`, old pointer preserved, `.current-<id>` retained, and stderr
contains that safe basename. Do not report retry success for this manual-recovery
state.

### ROOT-C: post-switch rollback

Case C1: inject a post-switch failure only. Assert exact original error code,
old current restored with owner/target correct, no `.rb-*`, no stale staging,
and canonical check/retry green.

Case C2: inject post-switch failure plus the exact rollback `os.replace` fault.
Assert exactly `EXIT_RECOVERY=16`, current remains the new generation, one
`.rb-<id>` remains and points to the old target, and stderr names that basename.
Also assert the child is gone and the lock is released. No OR expression that
accepts either old pointer or rc16 is allowed.

## Honest ownership mutation matrix

Keep the existing exact-one diff/compile/canonical-baseline/private-cwd/root
`.profile.lock` gates. Add two mutations that actually change active source:

1. `MUT13_NO_CURRENT_CHOWN`: replace the unique helper line
   `os.chown(name, uid, gid, follow_symlinks=False, dir_fd=env_fd)` with a
   syntax-valid no-op (for example a same-line `os.lstat(...)`) and run the
   mandatory root identity oracle. It must fail because `current` remains
   root:root.
2. `MUT14_ROLLBACK_CWD`: in the unique rollback call/context, change the
   fd-relative ownership operation to a cwd-relative one while preserving valid
   syntax. Run ROOT-C2 and require the oracle to fail. Do not use selectors
   mentioning inactive variable names (`current_tmp`/`rollback_name`) when the
   helper parameter is `name`.

The mutation runner must actually invoke the root oracle for these two cases
(as root, with the copied tool path), not only the astro:astro ordinary
harness. If the full ordinary harness is too expensive, use a focused root
oracle for MUT13/MUT14; it must still be independent and exact.

## Direct handoff evidence

Before handoff, run and record without output filters hiding status:

```text
python3.12 -I -S -m py_compile scripts/lib/prod-env-tool.py
bash scripts/tests/test-prod-env-install-transaction.sh
ROOT_IDENTITY_TEST=1 bash scripts/tests/test-prod-env-install-transaction.sh   # when running as root
bash scripts/tests/test-prod-env-profiles-mutations.sh
bash scripts/tests/test-prod-env-loader.sh
bash scripts/tests/test-prod-env-profiles.sh
bash scripts/tests/test-prod-deploy-source-loader.sh
bash scripts/tests/test-prod-host-offsite-routing.sh
scripts/prod-infra-fingerprint.sh
git diff --check
```

If the root command is a dedicated script, list that command instead. Include
exact rc, artifact, pointer, owner, and stderr assertions. Stop after handoff;
no commit/push.
