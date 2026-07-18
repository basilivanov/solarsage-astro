# REVIEW R14 Phase C2 — pointer canonicalization accepted independently

## Verdict

`ACCEPTED` for the canonical current/previous pointer slice from TZ 149, including the test-fidelity correction from review 150.

This verdict does not yet accept the complete promotion/rollback/GC transaction.

## Independent evidence

```text
bash -n library + CLI + both harnesses -> rc=0
test-prod-release-promotion.sh -> rc=0, 15/15
test-prod-release-pointer-contract.sh -> rc=0, 11 pointer cases + mutation proof
reasoning/debug residue gate -> empty
```

The promotion harness is deterministic and the focused pointer harness is deterministic.

## Accepted behavior

- Canonical raw pointer form is exactly `releases/<40 lowercase hex>`.
- current and previous use one GRACE-contracted parser in promote, rollback, and GC.
- Absolute, traversal, extra-component, uppercase, malformed, dangling, non-symlink, release-target-symlink, and release-target-file cases are rejected.
- Symlink lstat owner/group and resolved target equality are verified.
- Writers remain relative; first-install absence remains valid while dangling/non-symlink entries fail closed.
- Removing resolved-target equality makes PTR10 fail and the focused harness non-zero.
- CASE06 uses an independent old-release health registry and no longer derives health identity from the current symlink.

## Files in the accepted slice

- `scripts/lib/prod-release-promotion.sh`;
- `scripts/tests/test-prod-release-promotion.sh` — CASE06 fidelity correction only;
- `scripts/tests/test-prod-release-pointer-contract.sh` — new focused adversarial harness.

`scripts/prod-release-promote.sh` was not changed by this slice.

## Remaining promotion blockers

The following are outside this accepted pointer slice and remain unaccepted:

- proof-driven restoration of both current and previous on every failure;
- removal of unchecked restore/delete paths;
- maintenance flag create/delete metadata and fsync lifecycle;
- first-install recovery semantics;
- rollback transaction symmetry;
- GC canonical repository binding instead of caller-cwd discovery;
- fail-closed running-request directory/file metadata handling;
- deletion proof and recovery-state coverage for GC.

Proceed with a separate transaction/flag/GC TZ and retain both accepted harnesses unchanged except for explicitly reviewed new cases.
