# Review R14 — namespace correction still rejected for false-green edges

## Verdict

**REJECTED pending one final test-only correction.** The real legacy root regression is fixed and both 24-suite matrix invocations are green, but two verification contracts can still produce false confidence.

## Independent blocking findings

1. `run-deploy-matrix.sh` records every non-zero suite result as `1`; it does not preserve the actual exit code (for example timeout `124`). This violates the exact per-suite exit-code contract.
2. PID normalization uses the broad substitution `[0-9]+ Hangup` rather than matching only the expected Bash `file: line N: PID Hangup ...` diagnostic. The module invariant and raw-status text also omit the added mktemp-path normalization.
3. README inventory is converted through `sort -u` before the duplicate check, making duplicates impossible to detect. An independent temporary-copy mutation appended a second `scripts/deploy/prod-backup.sh` inventory row and the namespace test still returned `0`.
4. Mutation A uses a different parser (`scripts/deploy/[^ |]+`) from the real inventory check; its output includes closing backticks and directory fragments, so the mutation can pass for the wrong reason.
5. The compatibility map names only a subset of moved production/library/test files, while the README contract claims a truthful old-to-new map.
6. `test-prod-legacy-root-discovery.sh` code correctly checks `../../..`, but its invariant comment still says `../..`.

The bulk refactor, legacy runtime-path fix, active-reference scan, release suites and canonical matrix results remain retained. Do not redo them.

Implement `168_TZ_R14_DEPLOY_NAMESPACE_FINAL_TEST_CONTRACT_FIX.md` and stop for independent review.
