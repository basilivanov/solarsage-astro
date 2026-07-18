# R14 Phase C1A-R7 — strict transaction recovery and physical check gate

## Scope freeze

Read `112_REVIEW_R14_PHASE_C1A_R6_REJECTED_TRANSACTION_NOT_ATOMIC.md` first.

Keep the immutable-generation/current-symlink architecture and the parser
profile behavior that already passes the loader/profile/B6 suites. Change only:

- `scripts/lib/prod-env-tool.py` transaction/recovery/check implementation;
- `scripts/tests/test-prod-env-install-transaction.sh`;
- `scripts/tests/test-prod-env-profiles-mutations.sh`;
- new isolated test helpers if needed;
- this phase's docs.

Do **not** change systemd units, Docker/Compose, `prod-deploy.sh`, the shell
consumer paths, production/network/SSH/DB state, commit or push.

The coder must not declare success from a filtered output pipeline. Run the
acceptance commands directly and leave the tmux pane stopped at handoff.

## 1. Replace the transaction with an auditable state machine

Rewrite `cmd_install_set` rather than layering another catch around the current
body. The code must have one transaction guard for all operations from the
first mutation through post-switch verification:

```python
lock_fd = env_fd = gfd = sfd = ngfd = None
old_handlers = None
staging_name = gen_name = current_tmp = rollback_tmp = None
staging_created = False
generation_renamed = False
switched = False
previous_state = None
original_exception = None

try:
    # all mutating steps and all post-switch verification
except BaseException as original:
    # call one strict recovery function; do not swallow anything
finally:
    # restore handlers, unlock, close each fd exactly once
```

Rules:

1. Parse/validate source before opening canonical output state.
2. Open env/generations, acquire the canonical lock and validate housekeeping
   before any new mutation.
3. Read and physically validate the previous current state.
4. Install HUP/INT/TERM handlers before the first mkdir. The handler raises
   `TransactionSignal` unchanged; no `sys.exit()` is allowed inside the
   transaction.
5. Set `staging_created=True` immediately after a successful staging mkdir,
   before opening `sfd`. Set `current_tmp` immediately before symlink creation.
6. Set `generation_renamed=True` only after the rename succeeds; set
   `switched=True` immediately after current replacement.
7. Keep all open descriptors in state so a failure can close them in `finally`.
8. Translate the original exception only in `main()` after recovery has proved
   its result. Signal statuses must remain exactly 129/130/143.

The old best-effort helpers may not remain in the production path. Delete or
rewrite `_rollback_current`, `_cleanup_staging` and `_remove_generation` so
there is no transaction-cleanup `pass`, `except OSError: pass`, `return` on
failure or `|| true` equivalent.

## 2. Strict pre-switch recovery

Implement a single helper with explicit, verifiable outcomes. For a failure
before `switched`:

- remove `current_tmp` if it was created, whether `os.replace` failed before or
  after touching the destination; first prove it is the exact generated name;
- if `sfd` exists, validate the staging directory inventory (exact seven
  profile names, no symlink/hardlink/extra entry), unlink each known file,
  close the fd and remove the directory;
- if only `staging_created` is true, open the named directory safely and clean
  it; this covers SIG-PRE-DIR before `sfd` exists;
- if the staging directory was renamed, validate the exact generated name and
  remove only that generation; fsync `generations` after removal;
- verify that `current` is byte/type/owner/target identical to the captured
  previous state (or absent on first install);
- if any cleanup or proof fails, raise a dedicated recovery exception and
  preserve/report the exact artifact paths. Never convert it to ordinary I/O.

`current_tmp`, `.rb-*`, `.rollback-*` and `.staging-*` names must never survive
a successfully recovered transaction.

## 3. Strict post-switch rollback

For any exception after `switched=True`:

1. Create a uniquely named rollback symlink under the env fd, `lchown` it to
   the env uid/gid, verify its owner/type/target, then atomically replace
   `current`.
2. Fsync the env directory.
3. Re-read the current state using the same physical validator used before the
   install. Prove the exact previous target, owner, generation mode and all
   seven profiles (or prove absence on first install).
4. Remove the rollback temp symlink if it still exists and verify no temporary
   pointer remains.
5. If any step fails, leave both generations and the diagnostic artifact paths
   intact, return a dedicated recovery code (not `EXIT_IO=13`) and never claim
   the old pointer was restored.

The recovery function must not catch and discard an `OSError`, signal or
`KeyboardInterrupt`. It may wrap it in a typed recovery exception only after
recording the exact failed operation and state.

## 4. Make `check-installed` the same physical gate, read-only

`check-installed` must acquire the existing lock without `O_CREAT`, perform no
create/rename/chmod/chown/fsync/unlink, and use the same read-only validators as
install:

- env directory and generations directory exact type/owner/group/mode;
- lock regular/link-count/owner/group/mode;
- current absent-or-symlink, owner/group, exact relative target;
- current generation owner/group/mode and exact seven-file inventory;
- every profile regular, nlink=1, owner/group/mode 0640 and exact bytes;
- no direct legacy profile, stale `.staging-*`, `.current-*`, `.rollback-*`,
  `.rb-*` or noncanonical generation entry.

A check with an extra generation file, generation mode `0777`, stale temp link or
legacy direct profile must fail non-zero. Snapshot tests must include recursive
names, types, modes, owners, groups, link counts and content hashes before and
after; a passing check must leave all of them unchanged.

## 5. Deterministic fault and signal harnesses

### Fault injection

For every FI case:

1. Copy the tool into a private temp directory.
2. Verify exactly one source replacement and compile the copy.
3. Run a fresh canonical baseline oracle and assert it is green.
4. Inject an explicit `OSError`/`ToolError` at the named boundary.
5. Assert true exit code, previous current state, exact artifact inventory and
   that a subsequent canonical install/check behaves correctly.

Required cases include:

```text
FI01 first profile write
FI02 profile fchown
FI03 profile fchmod
FI04 profile fsync
FI05 staging verification
FI06 staging->generation rename
FI07 generations fsync
FI08 current replacement (must remove .current-* and permit retry)
FI09 env-dir fsync after switch (must roll back)
FI10 post-switch target verification (must roll back)
FI11 post-switch content verification (must roll back)
FI12 rollback replacement failure (distinct recovery rc, new pointer/artifacts retained)
FI13 rollback verification failure (distinct recovery rc, artifacts retained)
```

FI08 must explicitly assert no `.current-*`, and FI12/FI13 must be run on fresh
sandboxes rather than after another failed case. Do not use a `pass` mutation as
an oracle for a durability or metadata operation.

### Signals

Use a deterministic marker file or pipe written exactly at each pause point;
wait for the marker before sending the signal directly to the child PID. A
missing marker is a harness failure. Test HUP/INT/TERM at all five boundaries:

```text
SIG-PRE-DIR       immediately after staging mkdir
SIG-PRE-WRITE     immediately after the first profile write
SIG-PRE-RENAME    after generation rename, before current replace
SIG-POST-SWITCH   immediately after current replace, before env fsync
SIG-POST-VERIFY   immediately before post-switch content verification
```

Do not use a fixed `sleep 0.5` as the oracle and do not accept timeout 124.
For every row assert exact 129/130/143, previous pointer/absence, no staging or
pointer temp, no rollback temp, exact generation inventory and no corrupted
live generation. Keep the sandbox until all assertions finish; only then remove
it.

## 6. Mutation suite integrity

The mutation harness must run a green canonical harness before each mutation,
verify one-and-only-one replacement, and fail if any mutation returns zero. It
must not run a mutated tool from the repository cwd or create a repository-root
`.profile.lock`; all cwd and lock paths belong to the private sandbox. Count
exactly the listed cases and print each case's true rc and artifact result.

## 7. Acceptance commands

Run directly, in this order, and include complete FI/SIG rows in the handoff:

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

Also run the independent adversarial checks described in review 112. Stop at
R7 handoff. Do not start C1B/C2, commit or push.
