# REVIEW R14 Phase C2 — promotion harness rejected: execution manifest and postcondition coverage

## Verdict

`REJECTED`. The rewrite of `scripts/tests/test-prod-release-promotion.sh` is materially better than the previous harness, but it is not accepted yet. Production code was not changed by this review.

## Independent evidence

- Fresh run: `timeout 180 bash scripts/tests/test-prod-release-promotion.sh` returns `rc=1`.
- Deterministic red set: `CASE02`, `CASE06`, `CASE07`, `CASE08`.
- `CASE01`, `CASE03`, `CASE04`, `CASE05`, `CASE09`, `CASE10`, `CASE11`, `CASE12`, `CASE13`, `MUT01`, and `MUT02` pass.
- The four red cases share the production blocker in `scripts/lib/prod-release-promotion.sh:323`: validation requires an absolute old-current dirname, while the writer at `:360`/`:368` stores `releases/<sha>` relative targets.
- `bash -n scripts/tests/test-prod-release-promotion.sh` returns zero.
- The residue gate for the test file is empty.

## Reproducible harness gaps

### 1. Missing-case mutation is not detected

`try_case` writes successful labels to `MANIFEST` and failures to `FAILURES`, but `EXPECTED_MANIFEST` is compared only after the early `if [ -s "$FAILURES" ]; then exit 1` branch. A temporary copy with the entire `try_case "CASE13 ..."` invocation removed produces the same `rc=1` and byte-identical output as the baseline. Therefore the harness cannot prove that every declared case executed while another case is red.

Required correction: maintain an execution ledger independent of pass/fail, append every case label before invocation, and compare the complete expected ledger before returning either success or failure.

### 2. Failure postconditions short-circuit

`CASE06`, `CASE07`, and `CASE08` use `run_case && assert ... && assert ...`. On the current blocker, CASE08 reports only the missing flag; its `active.json` phase/recovery and service-order assertions are not executed. Required postconditions must all run and be collected for each case, even when an earlier assertion fails.

Required correction: use an assertion collector (`rc=0; assertion || rc=1` for every postcondition) and return the aggregate result. Keep exact current, previous, state, flag, service-order, and candidate-preservation checks.

### 3. Metadata oracles are incomplete

- `assert_flag present` checks only `-f`; it must reject symlinks and verify sandbox owner/group/mode.
- `assert_link` checks only symlink target; it should also verify symlink lstat owner/group and reject non-symlink replacement.

Required correction: add exact no-follow type and owner/group/mode assertions in the sandbox identity, without weakening production checks.

## Positive elements to preserve

- production files were not modified;
- exact-count substitution helper and valid 64-hex manifest fixtures;
- private scripts/lib layout and sandbox-only command mocks;
- independent per-service health registry;
- sandbox git worktree registry with exact argv checks;
- external mutation oracles with mutant syntax check and non-zero requirement;
- no reasoning/debug residue in the rewritten test file;
- deterministic red output and explicit production blocker.

## Acceptance gate after correction

Run independently from a fresh shell:

```bash
bash -n scripts/tests/test-prod-release-promotion.sh
timeout 180 bash scripts/tests/test-prod-release-promotion.sh
```

The suite may remain red only at the known production blocker, but it must prove the complete execution ledger and execute/record every postcondition. Re-run the missing-CASE13 mutation against a temporary copy and require a different failing result. Do not change production code in this correction slice.
