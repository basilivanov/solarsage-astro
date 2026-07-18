# Review R14 Phase C2 — hardening slice

## Verdict

**Conditionally accepted; one blocking micro-fix remains before integration.** The hardening slice now satisfies the requested error status, no-follow fsync, mode, coverage, and deterministic-harness requirements in the normal and injected-fsync paths. Do not integrate it into promotion until the cleanup error envelope is made single-line.

## Green evidence

- `scripts/prod-release-authority.py` is executable (`0755`).
- `bash -n scripts/tests/test-prod-release-authority.sh` — `0`.
- `python3.12 -I -S -m py_compile scripts/prod-release-authority.py` — `0`.
- Two independent `timeout 180` runs — `0`, `33/33` each; output is byte-identical.
- `visudo -cf infra/production/solarsage-deploy.sudoers` — parsed OK.
- Root oracle uses the exact command it invokes and labels broad-sudo staging as development-only, not production sudoers proof.
- No real production path or service was touched.

## Blocking finding

`op_switch_pointer()` prints `Error: temporary symlink cleanup failed` from its `finally` block and then lets the original `OSError` reach `main()`, which prints `Error: switch-pointer failed`. An independent injected probe produced:

```text
rc 78
lines ['Error: temporary symlink cleanup failed', 'Error: switch-pointer failed']
```

This violates the helper module contract and 155's fixed one-line error envelope. The cleanup failure must remain fail-closed and must not be silently swallowed, but it must be represented through the single operation-level fixed error path (for example, raise an `OSError` from cleanup and let `main()` emit only the operation's fixed line, without printing the cleanup detail).

## Scope

Only the helper and focused harness may change for this micro-fix. No promotion library/CLI, accepted promotion/pointer harness, installation, real `/run`, real runtime, systemd, nginx, database, or sudoers installation is authorized.

Implement `157_TZ_R14_PHASE_C2_RELEASE_AUTHORITY_CLEANUP_ERROR_ENVELOPE.md`, rerun all 155 checks twice, and stop for review.
