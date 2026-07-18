# R14 Phase C1A-R7J — close root:astro symlink ownership and recovery gap

## Scope and protocol

Read review 132. The coder may modify only the C1A env-profile tool and its
test harnesses. Do not change consumers, systemd, nginx, Docker, deploy order,
or production hosts. Do not commit or push. Do not start C1B/C2.

The architect will independently review and run the acceptance commands after
the coder handoff.

## Canonical production identity

`scripts/prod-env-prepare.sh --apply` runs the Python tool as root. Its
validated env directory is:

```text
/etc/solarsage/env              root:astro 0750
source.env                      root:astro 0640
generations/                    root:astro 0750
gen-<32 hex>/                   root:astro 0750
each profile                    root:astro 0640
current -> generations/gen-*    root:astro symlink
.profile.lock                  root:astro 0640
```

The implementation must work when the process euid/egid is root:root while the
expected uid/gid are derived from the env directory as root:astro. Existing
tests that run as astro:astro are not sufficient.

## Required production-code changes

### 1. One strict temporary-symlink helper

Add or reuse a small helper with a GRACE function contract. It must operate
only through the already-open env directory fd and must:

1. create the named symlink with the exact relative target;
2. `lchown` it to the env directory uid/gid using `dir_fd=env_dir_fd` (never a
   cwd-relative pathname);
3. lstat it through the same fd and verify symlink type, uid, gid, and exact
   target bytes;
4. report a safe basename on failure and never expose secret values.

Use this helper for `.current-<id>` before `os.replace` and for `.rb-<id>` in
rollback. The `current` temporary must be fully validated before any canonical
pointer replacement. After replacement, `switched` is true only once the
replace succeeded.

The rollback implementation must replace the existing cwd-relative call with
the fd-relative operation, for example `os.lchown(name, uid, gid,
dir_fd=env_fd)` (or an equivalent `os.chown(..., follow_symlinks=False,
dir_fd=env_fd)`). No path under `/opt/solarsage-astro` may be used for these
env-directory entries.

### 2. Safe failure before ownership is complete

If creation succeeds but the current-temp `lchown` or validation fails, the
transaction must remove exactly the symlink it just created and prove that it
is absent. Since the failed lchown may leave the symlink with the creator's
uid/gid, cleanup must not falsely require the post-lchown owner; it must still
validate exact symlink type and target and use the transaction's unique name.
If that exact cleanup cannot be proven, return `EXIT_RECOVERY=16` with the
safe `.current-<id>` basename. Never leave a stale temp that blocks the next
canonical retry silently.

For a rollback-temp lchown/validation failure after a switch, preserve the
new/current pointer and the exact `.rb-<id>` artifact, return `EXIT_RECOVERY`,
and include the safe artifact basename. This is the documented manual-recovery
state; do not claim rollback succeeded.

### 3. Full post-switch physical validation

Replace the weak post-switch link-only check with the full read-only state
validator (current owner/type/target, generation owner/mode, exact seven-file
inventory, nlink, profile owner/mode/content). The install command must never
print `install: OK` for a current symlink that `check-installed` would reject.

Keep the existing byte/content verification and do not delete old immutable
generations in this phase.

## Required tests

### A. Production-identity runtime oracle

Add a focused test (or an explicit section in the transaction harness) that
creates a private env directory and source owned `root:astro`, runs the tool as
root, and asserts:

1. first `install-set` returns 0;
2. `current` owner is exactly `root:astro` and its target is canonical;
3. canonical `check-installed` returns 0;
4. a second install and check both return 0;
5. the test leaves no temp/staging/rollback artifacts.

The test must fail closed if the required root/sudo/group capability is absent;
do not silently skip it in the local acceptance run. If portability for CI is
needed, gate it with an explicit documented `ROOT_IDENTITY_TEST=1` mode while
the production acceptance command enables that mode.

### B. Root-owner current-replace fault

On a fresh root:astro env with a valid old generation, mutate only the
canonical current `os.replace` call to raise. Assert the exact recovery code,
old current target unchanged, no `.current-*` or staging/new-generation leak,
and a canonical retry succeeds.

Also mutate the cleanup unlink to raise and assert `EXIT_RECOVERY=16`, old
pointer preserved, `.current-<id>` retained with a safe basename in stderr, and
no false-green retry claim.

### C. Root-owner post-switch rollback fault

On a fresh root:astro env, inject one post-switch failure and one exact rollback
replace failure. Assert `EXIT_RECOVERY=16`, new current preserved when rollback
cannot be proven, `.rb-<id>` exists and points to the old canonical target, and
stderr names that basename. The normal post-switch fault with a successful
rollback must assert old current, no `.rb-*`, and canonical check/retry green.

### D. Honest mutation and source gates

Extend the mutation matrix so removing the active current-temp lchown and
changing the rollback lchown to a cwd-relative call each makes the production-
identity oracle fail. Keep exact-one source replacement, compile, canonical
baseline, private cwd, root `.profile.lock` snapshot, artifact assertions, and
nonzero mutated result. Do not make a mutation target an unused helper.

## Acceptance command set

The handoff must record direct command exit codes and final lines, without
`grep`/`tail`/pipeline filters hiding failures:

```text
bash -n scripts/prod-env-prepare.sh
bash -n scripts/tests/test-prod-env-install-transaction.sh
bash -n scripts/tests/test-prod-env-profiles-mutations.sh
python3.12 -I -S -m py_compile scripts/lib/prod-env-tool.py
bash scripts/tests/test-prod-env-install-transaction.sh
bash scripts/tests/test-prod-env-profiles-mutations.sh
bash scripts/tests/test-prod-env-loader.sh
bash scripts/tests/test-prod-env-profiles.sh
bash scripts/tests/test-prod-deploy-source-loader.sh
bash scripts/tests/test-prod-host-offsite-routing.sh
scripts/prod-infra-fingerprint.sh
git diff --check
```

Run the new root-identity/fault section directly and record its rc and
postconditions. Repeat the ordinary transaction harness twice as before.
Do not commit, push, or proceed to C1B/C2. Stop after the coder writes the
handoff and waits for architectural review.
