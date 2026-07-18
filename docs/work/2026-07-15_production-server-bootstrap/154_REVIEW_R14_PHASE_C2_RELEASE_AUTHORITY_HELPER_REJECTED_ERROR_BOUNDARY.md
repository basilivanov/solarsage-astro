# Review R14 Phase C2 — release authority helper foundation

## Verdict

**REJECTED for integration.** The foundation is close and the sandbox matrix is green, but the helper still has an unsafe error boundary and the focused harness overstates what its root oracle proves. Do not install it, add it to the live sudoers policy, or integrate it into promotion until the follow-up hardening slice is accepted.

## Independent evidence

- `bash -n scripts/tests/test-prod-release-authority.sh` — green.
- `python3.12 -I -S -m py_compile scripts/prod-release-authority.py` — green.
- `timeout 180 bash scripts/tests/test-prod-release-authority.sh` — green, `24/24`.
- A second run is byte-for-byte deterministic.
- `visudo -cf infra/production/solarsage-deploy.sudoers` — `parsed OK`.
- No production `/run`, `/opt/solarsage-runtime`, systemd, nginx, database, install, or deploy action was performed.

These checks establish the current test claims, not production acceptance.

## Blocking findings

### 1. Public filesystem failures can escape as Python tracebacks (high)

`op_maintenance_on()` and `op_maintenance_off()` call `fsync_dir()` and perform `fchown`/`fchmod`/`unlink` without an operation-level `OSError` boundary. `op_remove_pointer()` has the same issue for `unlink`/`fsync_dir`. `fsync_dir()` intentionally propagates `OSError`, so an injected directory-fsync failure produces an uncaught exception and process status `1`, rather than the module contract's status `78` with one safe error line. The current `FS01` only asserts non-zero and therefore misses this contract violation.

The pointer path catches some errors, but emits `str(exc)` directly; that can include path data or newlines and is not the promised safe one-line error envelope.

Required outcome: every supported operation must convert expected filesystem/identity errors into a fixed, one-line error and status `78`; no traceback may be emitted.

### 2. Directory fsync is not itself no-follow (medium/high)

`fsync_dir()` opens a caller-supplied path with only `os.O_RDONLY`. The callers validate the directory before mutation, but the later open is a separate pathname resolution. The helper contract requires no-follow behavior. Use directory/no-follow open flags (and retain a metadata check on the opened descriptor where practical) so the durability step cannot follow a substituted directory symlink.

### 3. Root oracle preflight is broader than the capability being tested (medium)

`ROOT01` probes `sudo -n true`, then invokes `sudo -n /usr/bin/python3.12 ...` and several unrestricted staging commands. The accepted sudoers template grants the deploy user the installed helper path and selected `systemctl` commands, not `true`, Python, `rm`, `chown`, `mkdir`, or `ln`. Thus the oracle is valid only in a broad-sudo development environment; it is not a proof that the exact production capability can invoke the installed helper. The gate must probe the actual command it will use (or explicitly identify this as a development-only root identity oracle) and must not claim production sudoers coverage.

### 4. Focused matrix has coverage gaps required by 153 (medium)

The ordinary matrix has wrong mode and symlink/type cases, and `ROOT01` combines wrong owner and wrong group in one pointer case. It does not independently exercise wrong owner, wrong group, and dangling-pointer/target cases. Add named cases so each required rejection is independently visible in the execution ledger.

### 5. Source helper is not executable (low, but release-facing)

`scripts/prod-release-authority.py` currently has mode `0664` in the worktree. The installed contract is a shebang CLI at `0755`; the source/template should carry executable mode so byte-exact host preparation cannot silently produce a non-executable helper.

## Scope protection

The accepted promotion/pointer libraries and harnesses were not changed in this review. The next slice may change only the helper and its focused harness (plus the already-added sudoers template if a syntax-only correction is necessary). No installation or real production action is authorized.

## Follow-up

Implement `155_TZ_R14_PHASE_C2_RELEASE_AUTHORITY_HELPER_HARDENING.md`, rerun the complete 153 command set plus the new mutation/coverage cases twice, and stop for another independent review.
