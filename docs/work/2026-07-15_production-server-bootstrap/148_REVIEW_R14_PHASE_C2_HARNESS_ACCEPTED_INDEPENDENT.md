# REVIEW R14 Phase C2 — promotion harness accepted as an honest red gate

## Verdict

`ACCEPTED` for `scripts/tests/test-prod-release-promotion.sh` as the independent harness for the promotion slice. This verdict does **not** accept `scripts/lib/prod-release-promotion.sh`, `scripts/prod-release-promote.sh`, or the promotion slice as production-ready.

## Independent evidence

```text
bash -n scripts/tests/test-prod-release-promotion.sh -> rc=0
timeout 180 bash scripts/tests/test-prod-release-promotion.sh -> rc=1
residue rg -> rc=1, no matches
```

The deterministic red set is exactly:

- `CASE02 normal rotation promotion success`;
- `CASE06 systemctl failure rollback`;
- `CASE07 health mismatch rollback`;
- `CASE08 rollback failure recovery required`.

The remaining 9 contract cases and both production-code mutation proofs pass.

## False-green audit

- The execution ledger records every declared case before invocation and is compared before the red-suite exit.
- A canonical temporary copy with the CASE13 invocation removed, `REPO_ROOT` pinned, and `PRM_PROMOTION_SELFP=1` returns non-zero and reports `execution ledger mismatch` plus `CASE13 gc protects running request success` as declared but not executed.
- CASE06/07/08 aggregate every required postcondition. The current red output proves that phase, recovery class, flag, and service-order failures are all evaluated rather than short-circuited.
- `maintenance.flag` checks reject symlinks and verify regular-file owner/group/mode in the sandbox identity.
- current/previous checks require symlink type, exact relative `releases/<40hex>` target, and lstat owner/group.
- Production-code mutants are syntax-checked; the unmutated oracle must pass and the mutant must return non-zero.
- Sandbox command copies replace production paths and real systemctl/curl/git with exact-count substitutions and mock registries.
- No reasoning/debug residue remains in the harness.

## Confirmed production blocker

`scripts/lib/prod-release-promotion.sh:323` validates the old current target dirname only as the absolute `$PROD_PRM_RELEASES_DIR`, while the same library writes current/previous targets as relative `releases/<sha>` at `:360` and `:368`. Consequently every second promotion fails with rc 78 and `Error: old current path format is invalid` before maintenance flag creation or service switching.

## Next task

Proceed to production fixes in `scripts/lib/prod-release-promotion.sh` and, only if required, `scripts/prod-release-promote.sh`. Do not weaken or rewrite the accepted harness. Fix the pointer representation/validation first, then run the harness to expose the next red production invariant. Continue until all 15 checks pass, preserving manual-only execution and without touching real production state.
