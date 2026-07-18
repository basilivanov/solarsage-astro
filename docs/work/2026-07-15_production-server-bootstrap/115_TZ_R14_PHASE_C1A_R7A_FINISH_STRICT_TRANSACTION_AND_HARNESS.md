# R14 Phase C1A-R7A — finish strict transaction and honest harness

## Read first and scope

Read reviews `112_REVIEW_R14_PHASE_C1A_R6_REJECTED_TRANSACTION_NOT_ATOMIC.md`
and `114_REVIEW_R14_PHASE_C1A_R7_REJECTED_INCOMPLETE_RECOVERY.md`, then this
file completely.

Only finish the C1A transaction/check implementation and its isolated tests:

- `scripts/lib/prod-env-tool.py`;
- `scripts/tests/test-prod-env-install-transaction.sh`;
- `scripts/tests/test-prod-env-profiles-mutations.sh`;
- new private test helper files if necessary.

Do not touch consumers, systemd, Docker, deploy flow, production/network/SSH/
DB state, commit or push. Do not report handoff until every command in section
8 has actually completed with rc 0.

## 1. Production transaction must be genuinely one-guard/finally

Replace the active `cmd_install_set` body. Do not leave a second legacy helper
that can be mistaken for the implementation. In the active transaction range
there must be:

- one `try` covering all mutations and post-switch verification;
- one `except BaseException as original` that calls a strict recovery function;
- one `finally` that restores signal handlers, unlocks and closes every owned fd
  exactly once;
- no `except OSError: pass`, no `except Exception` around recovery, no cleanup
  return that means “best effort”, and no `sys.exit()` before `main()`.

Use a typed `RecoveryError` with a dedicated exit code different from
`EXIT_IO=13`. Preserve safe artifact basenames in the diagnostic (never secret
values or exception reprs). If recovery fails, do not alter the pointer again,
do not unlink the new/old generations, and report the exact `.rb-*`,
`.current-*`, `.staging-*` or generation path that remains.

## 2. Complete pre-switch cleanup

Track these transitions before the operation that can fail:

```text
staging_created  immediately after mkdir
sfd_open         immediately after open
current_tmp      before symlink creation
generation_renamed after rename succeeds
switched         immediately after current replace succeeds
```

For every failure before `switched`:

1. Remove the exact current temp symlink if it exists, including replace
   failure. Verify it is absent.
2. Clean a staging directory even when `sfd` was never opened. Validate exact
   seven-file inventory before unlinking and fsync `generations` after removal.
3. Remove a renamed generation only when its name/id was created by this
   transaction and it is not current. Validate final absence.
4. Prove current is exactly the captured old target or absent.

The next canonical install must succeed after an injected current-replace
failure and after SIG-PRE-DIR. Add those assertions to the harness.

## 3. Complete post-switch rollback

For any failure after `switched`:

1. Create rollback symlink with the exact previous target, lchown/verify its
   type, owner, group and target.
2. Atomically replace `current`, fsync env dir and re-read with the same full
   physical validator used before install.
3. Verify the old generation's owner/mode/exact seven profiles, or verify first
   install absence.
4. Remove/verify rollback temp only after successful replacement.

Inject a post-switch fault plus rollback-replace failure on a fresh sandbox. It
must return the dedicated recovery rc, leave `current` at the new generation,
leave both generations and the diagnostic artifact, and never call that state a
successful rollback. A normal post-switch fault with working recovery must
return its ordinary mapped rc and restore the old pointer.

## 4. `check-installed` exact inventory and read-only proof

Use the same physical validator as install, not a weaker duplicate loop. It
must reject:

- any extra/missing/noncanonical entry under the current generation;
- generation mode/owner/group mismatch;
- profile type/link-count/owner/group/mode/content mismatch;
- stale `.staging-*`, `.current-*`, `.rollback-*`, `.rb-*`, direct legacy
  profile or noncanonical generation entry;
- invalid current symlink owner/target and invalid lock metadata.

The check path may only open/read/stat/list/flock. Snapshot recursive names,
types, mode, uid, gid, nlink and content digest before and after a successful
check and assert byte/metadata equality.

## 5. Honest FI harness

Each FI case gets a fresh sandbox (or an explicit clean baseline restored and
verified before the mutation). For each mutation:

1. Copy the tool outside the repository cwd.
2. Apply exactly one replacement; assert replacement count is exactly one.
3. Compile the copy.
4. Run the unmodified canonical oracle and require rc 0.
5. Run the mutated copy and assert the named rc, pointer and artifact state.
6. Run a canonical retry/check and assert the expected recovery behavior.

Do not use `if True`/`pass` as a substitute for an observable fault. FI12 and
FI13 must actually reach rollback, not merely fail earlier at housekeeping.

## 6. Honest signal harness — no timeout fallback

Remove all `/usr/bin/timeout`, `--kill-after`, fixed `sleep(0.5)` and
`kill ... || true` from the signal oracle. Each copied tool must write a unique
marker immediately at the exact pause boundary:

```text
SIG-PRE-DIR       after staging mkdir
SIG-PRE-WRITE     after first profile write
SIG-PRE-RENAME    after generation rename, before current replace
SIG-POST-SWITCH   after current replace, before env fsync
SIG-POST-VERIFY   immediately before post-switch content verification
```

The harness waits for the marker with a bounded polling loop; missing marker,
child exit before marker, or any timeout is a harness failure. Once the marker
exists, send HUP/INT/TERM directly to the child PID and wait for it. Assert
exact 129/130/143, unchanged old pointer/absence, no temp/staging/rollback
artifact, exact live-generation inventory and no stale child/lock holder.
Keep the sandbox until every assertion passes; only then remove it.

## 7. Mutation harness isolation

Run every copied tool with its cwd and all relative paths inside the private
sandbox. It must never create or modify repository-root `.profile.lock`.
Verify exact mutation count, canonical baseline green per case, and nonzero
exit if any mutation is not detected. Print true rc and artifact result per
case; do not use a pipeline that masks the harness status.

## 8. Mandatory direct acceptance

Run each command directly, not through `grep`, `tail`, `PIPESTATUS`, or an
outer timeout used as success:

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

Record complete FI01–FI13 and SIG01–SIG15 rows, exact return codes, pointer and
artifact state. Stop immediately after handoff. No C1B/C2/commit/push.
