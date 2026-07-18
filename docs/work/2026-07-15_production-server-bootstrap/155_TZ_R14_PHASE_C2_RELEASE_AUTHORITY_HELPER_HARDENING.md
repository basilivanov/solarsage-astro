# TZ R14 Phase C2 — release authority helper hardening

Read first:

- `docs/work/2026-07-15_production-server-bootstrap/152_ARCH_R14_PHASE_C2_PRIVILEGED_RELEASE_AUTHORITY.md`
- `docs/work/2026-07-15_production-server-bootstrap/153_TZ_R14_PHASE_C2_RELEASE_AUTHORITY_HELPER_FOUNDATION.md`
- `docs/work/2026-07-15_production-server-bootstrap/154_REVIEW_R14_PHASE_C2_RELEASE_AUTHORITY_HELPER_REJECTED_ERROR_BOUNDARY.md`

## Objective

Harden only the foundation helper and its focused harness. Do not integrate promotion, install anything, invoke real `/run` or `/opt/solarsage-runtime`, reload nginx/systemd, touch the database, or modify the accepted promotion/pointer harnesses.

## Allowed files

- `scripts/prod-release-authority.py`
- `scripts/tests/test-prod-release-authority.sh`
- `infra/production/solarsage-deploy.sudoers` only if a syntax-only correction is unavoidable

Set the helper source mode to `0755`.

## Required helper changes

1. Preserve the fixed roots, exact argv contract, canonical pointer target, ownership checks, atomic same-directory temporary symlink, fsyncs, and postconditions already present.
2. Add a single explicit error boundary around each supported operation. Convert expected `OSError`, identity lookup, and metadata failures to a fixed one-line `Error: ...` message and exit `78`. No Python traceback may escape. Do not print raw exception strings or user-controlled paths.
3. Make `fsync_dir()` open a real directory with `O_DIRECTORY|O_NOFOLLOW` (where available), close the descriptor reliably, and preserve the non-swallowing/fail-closed behavior. The public operation must report the failure as status `78`.
4. Keep `maintenance-on` fail-closed if any post-create metadata/fsync step fails; never report success unless file type, owner, group, mode, and parent durability checks all pass.
5. Keep `finalize-release` and `gc-remove` unimplemented and non-zero.

## Required harness changes

1. Keep exact-count substitutions, private `/tmp` trees, execution ledger, residue gate, and deterministic output.
2. Extend mutation coverage so an injected `fsync_dir` failure in each relevant public operation is asserted as exactly status `78` with no traceback text.
3. Add independently named cases for wrong owner, wrong group, wrong mode, and dangling/non-canonical pointer/target behavior. Use the root oracle only where ownership cannot be staged as the unprivileged test user.
4. Make the root-oracle capability gate probe the command actually used by the oracle; report an explicit `UNMET ACCEPTANCE GATE` if that command is unavailable. Do not use `sudo -n true` as a proxy and do not describe broad-sudo staging as proof of the production sudoers boundary.
5. Keep the mutation self-proof: removing `O_NOFOLLOW|O_EXCL` or the relevant postcondition must make the same oracle non-zero. The unmutated helper must remain green.

## Verification (all required)

```bash
bash -n scripts/tests/test-prod-release-authority.sh
python3.12 -I -S -m py_compile scripts/prod-release-authority.py
timeout 180 bash scripts/tests/test-prod-release-authority.sh
timeout 180 bash scripts/tests/test-prod-release-authority.sh
diff -u <(first-run-output) <(second-run-output)
visudo -cf infra/production/solarsage-deploy.sudoers
```

The final report must include exact return codes, the root-oracle result (green or explicit unmet gate), the two-run determinism result, and confirmation that no real production path or service was touched. Stop after the foundation hardening for independent review.
