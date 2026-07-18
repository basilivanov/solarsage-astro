# REVIEW R14 Phase C2 — pointer slice rejected pending test fidelity and adversarial coverage

## Verdict

`REJECTED` pending test-only corrections. The production pointer implementation is structurally aligned with TZ 149 and changes the main harness from 11/15 to 14/15 green, but the remaining red is caused by CASE06 mock fidelity and the adversarial pointer contract is not yet executable evidence.

## Independent evidence

- `bash -n` for library, CLI, and harness returns zero.
- Main harness after the production change: 14/15 green; only CASE06 is red.
- CASE02, CASE07, and CASE08 now pass, proving the original relative/absolute pointer inconsistency was removed.
- CASE06 candidate restart fails before any health request. The harness nevertheless keeps the independent per-service health registry at candidate SHA B during rollback to old SHA A, so production correctly enters `recovery_required`.
- A temporary test-only copy that changes only CASE06 health registry from SHA B to SHA A returns `15/15 green`. Production code is unchanged in that proof.

## Required test-only correction

1. In CASE06, model the old stack explicitly: set the independent health registry to SHA A. Do not derive health identity from the current symlink. The candidate fails at the first systemctl restart, so no candidate health response is needed.
2. Keep exact expected service order and rollback postconditions.
3. Add a focused isolated pointer-contract harness, preferably `scripts/tests/test-prod-release-pointer-contract.sh`, without growing the already large main harness.
4. The pointer harness must copy/source the production library in a private sandbox with exact substitutions and test at least:
   - canonical current relative target succeeds and returns exact SHA;
   - canonical previous relative target succeeds;
   - absolute target rejected;
   - traversal target rejected;
   - extra path component rejected;
   - uppercase/non-40-hex target rejected;
   - dangling symlink rejected;
   - non-symlink entry rejected;
   - canonical raw target resolving to a symlink/non-directory release target rejected.
5. Add a mutation self-proof for the canonical raw-target guard or resolved-target equality so weakening it makes the focused harness fail.
6. Do not modify production code in this correction slice.

## Acceptance commands

```bash
bash -n scripts/tests/test-prod-release-promotion.sh \
  scripts/tests/test-prod-release-pointer-contract.sh
timeout 180 bash scripts/tests/test-prod-release-promotion.sh
timeout 180 bash scripts/tests/test-prod-release-pointer-contract.sh
```

Both suites must pass independently and deterministically, with empty reasoning/debug residue gates and no real production paths or commands touched.
