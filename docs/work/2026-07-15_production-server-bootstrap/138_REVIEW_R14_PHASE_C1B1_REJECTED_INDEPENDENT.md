# R14 Phase C1B1 — independent review rejected

## Verdict

**Rejected for correction.** The installed-profile runtime itself has useful
coverage and the ordinary/root happy paths pass, but the phase is not accepted
because several explicit C1B1 safety contracts are either false or untested.
No production consumer was switched, no production service/network/database
state was changed, and no commit/push was made.

The coder must continue only through the corrective task in
`139_TZ_R14_PHASE_C1B1_CORRECTIONS.md`, then stop for another independent
review. Do not start C1B2 or C2.

## Independent evidence

Passed independently in fresh commands:

```text
bash -n scripts/prod-env-run.sh scripts/tests/test-prod-env-runtime*.sh       rc=0
python3.12 -I -S compile(prod-env-tool.py)                                    rc=0
bash scripts/tests/test-prod-env-runtime.sh                                    rc=0
sudo -n bash scripts/tests/test-prod-env-runtime-root.sh                       rc=0
bash scripts/tests/test-prod-env-runtime-mutations.sh                         rc=0
```

The last command's green result is not sufficient: it was run as user
`astro`, and its root mutation branch is conditionally skipped rather than
requiring/using `sudo -n`. That is a false-green acceptance path.

## Blocking findings

### 1. FIFO lock can hang before the bounded flock

`load_installed_profile()` opens `.profile.lock` with `O_RDONLY|O_NOFOLLOW`
without `O_NONBLOCK`. A FIFO at that pathname blocks in `os.open()` before
metadata validation or `flock`. Independent synthetic probe:

```text
FIFO lock + timeout 2s → rc=124
```

This violates the C1B1 requirement that malformed lock types and contention
fail bounded and never hang. The fix must use nonblocking open for the
read-only/check path, then reject non-regular files with the normal stable
verification code. Preserve C1A install semantics; do not add a writer or
delete the lock.

### 2. Installed profile parser accepts ASCII control bytes

`deserialize_envfile()` validates syntax but does not reject control characters
inside a quoted value. Independent synthetic probe changed only optional
`CORS_ALLOWED_ORIGINS` to contain `U+0001`; `run-installed` returned `0` and
executed the child. C1B1 explicitly requires CR/NUL/control rejection before
exec. Add the same byte-level control policy used by the source parser to the
installed-file parser. Also map invalid UTF-8 to stable `EXIT_VERIFY` rather
than generic `EXIT_UNEXPECTED`.

Add regression cases for optional-value `U+0001`, DEL, CR, NUL and invalid
UTF-8; prove no child exec and no value/byte leakage.

### 3. Root mutation coverage is skipped for a normal `astro` invocation

`test-prod-env-runtime-mutations.sh` runs root baseline/mutation code only when
`id -u == 0`. When invoked as the documented/current user `astro`, it sets a
success-producing nonzero result for the root mutation branch and reports all
12 mutations green without executing MUT12. The C1B1 TZ explicitly forbids
SKIP/false-green root coverage.

Require `sudo -n` at the beginning of the mutation harness and execute the root
baseline and wrapper mutation via `sudo -n` even when the caller is `astro`.
If non-interactive sudo is unavailable, fail the harness nonzero; never skip or
count the mutation as caught. Prove the copied mutant wrapper is what the root
oracle executes.

### 4. Mutation harness silently depends on `strace`

MUT04/MUT07 use `strace`, but the harness neither declares nor checks this
dependency before running. A fresh test host without `strace` can abort or
produce an empty-log result unrelated to the mutation. Either remove this
dependency with a deterministic fd/path oracle, or add an explicit
`command -v strace` prerequisite that fails the entire harness before any green
result. It must never treat missing `strace`, empty logs or a command failure as
“mutation caught”. Keep exact mutation-count and executed-copy assertions.

### 5. Root wrapper substitution assertion contains a no-op branch

The root harness computes a replacement count and then has an empty `if` body.
Although a later Python replacement currently checks one exact line, the
dead branch is misleading and does not itself enforce the documented exact
replacement rule. Replace it with one explicit assertion: the canonical
`ENV_DIR="/etc/solarsage/env"` assignment occurs exactly once, the replacement
occurs exactly once, and the resulting copy contains no canonical path override.

### 6. Wrapper uses ambient shell utilities before sanitizing PATH

`prod-env-run.sh` invokes `id`, `dirname`, `cd` and `stat` by bare name while
still inheriting the caller's PATH. The child is later sanitized, but a root
wrapper's preflight must not resolve helper binaries from an attacker-controlled
PATH. Set a fixed trusted wrapper PATH (or use exact absolute utility paths)
before the first identity/filesystem helper call, without changing the CLI
ordering or the child fixed environment.

### 7. GRACE contract completeness for new runtime files

The new wrapper and runtime harnesses have module contracts but no explicit
`START_MODULE_MAP`/`END_MODULE_MAP` blocks. Add the required maps/semantic
blocks for every new/substantially changed file, and update the Python module
contract/module map to list `run-installed` and `run-clean` public entrypoints.
Do not rewrite unrelated old files merely for formatting.

## Non-blocking observations to preserve for the next review

- C1B1 correctly leaves API/sidecar/DB/backup/offsite/deploy/systemd/Docker
  consumers on the old loader; do not begin that cut-over in the correction.
- C2 canonical PostgreSQL identity remains intentionally unimplemented.
- The fixed child environment and command-owned frontend/migration values are
  directionally correct; retain their existing tests.
- No production path was executed by the independent probes; all probes used
  synthetic temporary directories.

## Required handoff after correction

Report exact mutation IDs and the fresh independent evidence for FIFO,
control-byte/invalid-UTF8, root-via-sudo mutation coverage and the wrapper PATH
boundary. Stop after C1B1 correction; do not commit, push, deploy or start
C1B2/C2.
