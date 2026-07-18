# R14 Phase C1A-R4 — harden immutable transaction and fault proof

## Scope

Keep the immutable generation + atomic `current` architecture from R3. Fix only
transaction correctness, physical validation and executable fault coverage.

Read `106_REVIEW_R14_PHASE_C1A_R3_REJECTED_IMMUTABLE_TRANSACTION_GAPS.md` first.
No C1B/C2, production/network/SSH/DB/Docker/systemd mutation, commit or push.

## 1. Internal error model: never `sys.exit` inside a transaction

Add a private exception:

```python
class ToolError(Exception):
    def __init__(self, code: int, safe_message: str): ...
```

Parser/serializer/transaction helpers raise `ToolError`. `main()` alone catches
it, prints the safe message and returns/exits its code. Remove raw traceback and
exception output.

Successful handlers may return normally; `main()` returns 0. Avoid `SystemExit`
as internal control flow. This makes one transaction `try/except/finally` catch
every expected failure and clean/rollback deterministically.

## 2. Canonical lock

Open `.profile.lock` by `env_dir_fd`:

```python
os.open(
    ".profile.lock",
    os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW | O_CREAT_FOR_INSTALL_ONLY,
    0o640,
    dir_fd=env_dir_fd,
)
```

Install behavior:

- may create lock;
- fstat regular, nlink=1;
- fchown env uid/gid, fchmod 0640, fsync on creation/change;
- exclusive nonblocking flock; contention is stable nonzero.

Check behavior:

- must not use `O_CREAT`;
- missing/invalid lock is stable nonzero and causes no mutation;
- shared nonblocking flock; contention is stable nonzero, never `pass`.

Tests prove no lock appears in cwd and exact mode/owner inside env dir.

## 3. Install-only creation vs read-only check

Split generations open into:

```python
open_generations_for_install(..., create=True)
open_generations_for_check(..., create=False)
```

Only install may create. On creation, fchown env uid/gid, fchmod 0750 and fsync
env dir. Both paths fstat the directory and require exact uid/gid/mode 0750.

`check-installed` takes before/after directory-entry and metadata snapshots in
the harness. Missing generations/lock/current must fail without creating or
changing anything.

## 4. Exact current and generation physical validation

Distinguish `ENOENT` from all other `readlink/lstat` failures. A regular current
file, permission error or malformed symlink is not "absent".

Validate current:

- symlink target exact `generations/gen-[0-9a-f]{32}`;
- symlink lstat uid/gid equal env uid/gid;
- target generation opened from the already validated `generations` fd using
  only `gen-<id>`, not by re-traversing `generations/...` from env fd;
- generation dir uid/gid, mode 0750;
- exact entry set equals the seven profile filenames, no extras;
- each profile regular, nlink=1, uid/gid, mode 0640, bounded complete read;
- reject direct legacy `/env-dir/api.env` etc;
- reject stale `.staging-*`, `.current-*`, `.rollback-*`, `.rb-*` before work.

Before installing a new generation, physically validate the previous target as
a safe rollback target. Its bytes need not match the new source, but its
directory/inventory/metadata must be valid.

## 5. Staging creation and durability

- Create staging under `generations` by dir fd.
- fchown/fchmod staging dir to env uid/gid and 0700 while building.
- Write every profile with a loop until all bytes are written.
- fchown/fchmod each profile, then fsync it **after** final metadata.
- Reopen and verify all seven bytes/metadata and exact staging inventory.
- Set staging dir 0750, fsync it, rename to `gen-<id>`, fsync generations.

On any pre-switch `ToolError`, `OSError` or transaction signal:

- close every fd;
- remove files by staging dir fd, then rmdir staging by generations fd;
- if staging already renamed, remove only the known new generation by its fd
  after exact inventory validation, or preserve/report it if safe removal cannot
  be proven;
- leave current byte-exact unchanged;
- do not use cwd-relative unlink and do not swallow cleanup errors.

## 6. Atomic switch and proven rollback

State explicitly:

```python
previous_target: str | None
new_target: str
switched: bool
```

Create temp symlink by env fd, lchown it to env uid/gid, validate exact target,
then atomically replace `current` and fsync env dir. Set `switched=True` only
after replace.

All post-switch steps, including fsync and full new generation verification,
remain inside one guarded transaction. Any failure after `switched=True` calls
one rollback function:

- previous target: atomically replace current with a newly created validated
  temp symlink to previous target;
- first install: unlink current;
- fsync env dir;
- validate current is exactly previous target/absent and previous generation is
  physically valid;
- only then report original error/signal.

Rollback errors are never swallowed. On rollback failure, return a distinct
recovery code and preserve old/new generation and safe temp paths.

## 7. Signal handling

Temporarily install handlers for HUP/INT/TERM that raise
`TransactionSignal(signum)`. Restore previous handlers in `finally`.

- before switch: clean staging/new generation, current unchanged;
- after switch: rollback pointer;
- successful recovery exits exactly 129/130/143;
- failed recovery returns recovery error and preserves artifacts.

Add real subprocess tests that pause a verified sandbox copy at pre-switch and
post-switch boundaries using an exact source mutation of the copy (no production
runtime hook), send each signal, then assert pointer and process/temp cleanup.

## 8. Finish small engine correctness gaps

- `check-installed` must not mutate anything;
- profile bounded read checks size before/while reading and reaches EOF;
- canonical deserializer rejects interior blank lines and dangling backslash;
- named `validate --profile X` calls `render_profile(parsed, X)`;
- legacy `render-set`/`verify-set` operate through validated dir fds or are
  explicitly deprecated and kept out of production install path; retain B6
  compatibility;
- tool stderr contains no source values or traceback;
- shell wrapper must not discard safe tool errors with `2>/dev/null`.

## 9. Rewrite fault tests (required, not optional)

The canonical profile harness must add direct assertions for every result from
review 106:

```text
lock_in_cwd=no
lock_in_env=yes mode=640
check under exclusive lock -> nonzero
fresh check -> nonzero and zero filesystem changes
extra generation file -> nonzero
generation mode 0777 -> nonzero
post-switch verification failure -> old/absent current
pre-switch write failure -> no staging and current unchanged
```

Add generation/current malformed target, current regular file, profile symlink,
profile hardlink, stale temp and direct legacy-file cases.

Replace `test-prod-env-profiles-mutations.sh`. It must have at least 12
transaction-aware cases and for each mutation run a specific safety oracle that
is green on canonical code and red on mutated code. Required mutations:

1. lock without env dir fd;
2. check `O_CREAT`;
3. lock contention ignored;
4. previous generation validation removed;
5. partial-write loop weakened;
6. final file fsync removed;
7. post-switch verification rollback removed;
8. rollback verification removed;
9. current traversal regex weakened;
10. exact generation inventory weakened;
11. signal status changed;
12. safe error changed to traceback/value leak.

Verify each textual mutation applies exactly once and remains syntactically
valid. No fixed shared `/tmp` paths. Mutation success means the safety oracle
detects the regression; do not merely assert the mutated bad command's expected
result.

## 10. Acceptance

Direct execution only:

```bash
bash -n scripts/lib/prod-env-loader.sh scripts/prod-env-prepare.sh \
  scripts/tests/test-prod-env-loader.sh scripts/tests/test-prod-env-profiles.sh \
  scripts/tests/test-prod-env-profiles-mutations.sh
python3.12 -I -S -c 'compile(open("scripts/lib/prod-env-tool.py", "rb").read(), "scripts/lib/prod-env-tool.py", "exec")'
bash scripts/tests/test-prod-env-loader.sh
bash scripts/tests/test-prod-env-profiles.sh
bash scripts/tests/test-prod-env-profiles.sh
bash scripts/tests/test-prod-env-profiles-mutations.sh
bash scripts/tests/test-prod-deploy-source-loader.sh
bash scripts/tests/test-prod-host-offsite-routing.sh
bash scripts/prod-infra-fingerprint.sh
git diff --check
```

Handoff must include real fault/signal IDs and current target before/after, not
only aggregate case counts. Stop after R4; no C1B/C2/commit/push.
