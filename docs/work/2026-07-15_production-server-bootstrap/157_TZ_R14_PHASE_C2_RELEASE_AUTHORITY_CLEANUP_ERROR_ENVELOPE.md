# TZ R14 Phase C2 — cleanup error envelope

Read:

- `152_ARCH_R14_PHASE_C2_PRIVILEGED_RELEASE_AUTHORITY.md`
- `153_TZ_R14_PHASE_C2_RELEASE_AUTHORITY_HELPER_FOUNDATION.md`
- `154_REVIEW_R14_PHASE_C2_RELEASE_AUTHORITY_HELPER_REJECTED_ERROR_BOUNDARY.md`
- `155_TZ_R14_PHASE_C2_RELEASE_AUTHORITY_HELPER_HARDENING.md`
- `156_REVIEW_R14_PHASE_C2_RELEASE_AUTHORITY_HARDENING_MICRO_FIX.md`

## Task

Fix only the temporary-symlink cleanup error path in `scripts/prod-release-authority.py` and add a focused mutation/assertion in `scripts/tests/test-prod-release-authority.sh` proving that a cleanup failure still returns `78`, emits exactly one fixed operation error line, and never emits a traceback, raw exception, path, or a second cleanup line.

The cleanup must not be silently swallowed. Route it into the existing operation-level fixed error boundary. Preserve all successful pointer semantics, no-follow fsync flags, ownership checks, and postconditions.

Do not modify promotion/pointer production code or accepted harnesses. No installation or real production action. Keep source mode `0755`.

## Verification

Run the complete 155 verification set, including:

```bash
bash -n scripts/tests/test-prod-release-authority.sh
python3.12 -I -S -m py_compile scripts/prod-release-authority.py
timeout 180 bash scripts/tests/test-prod-release-authority.sh  # twice, byte-identical output
visudo -cf infra/production/solarsage-deploy.sudoers
```

Report exact return codes and stop for independent review.
