# TZ R14 — final deploy namespace test-contract fix

Read 167 and correct only the verification contracts. Do not change production behavior or redo the namespace move.

## Matrix runner

- Preserve the exact return code from every suite (`0`, assertion rc, timeout `124`, signal-derived rc, etc.) in `exits.log` and failure output. Compare exact codes between runs and require every first-run code to equal `0`.
- Anchor PID normalization to the exact expected Bash diagnostic form (`<file>: line <n>: <pid> Hangup ...`). An unrelated string containing `123 Hangup` must not be normalized.
- Document all normalization fields consistently in the module invariant, implementation comments, raw-status text and final report: generation ID, exact Hangup PID, outer run label and known `/tmp/solarsage-*` mktemp root.
- Add a small canonicalizer self-proof: all allowed volatile fields normalize, while an unrelated numeric/Hangup line and arbitrary error content remain byte-exact.

## Namespace/inventory contract

- Parse only the README section between `## Canonical inventory` and `## Compatibility map` for the canonical inventory.
- Do not apply `sort -u` before duplicate detection. Require every real canonical file to occur exactly once in that section, no missing paths, no extra/non-existent paths and no duplicate rows.
- Reuse the same inventory parser/validator for the live README and mutation fixtures.
- Mutation proofs must invoke the same validator and demonstrate both removal and duplication of one canonical row are rejected. Keep stale legacy/docs mutations fail-closed.
- Make the compatibility map truthful and complete. Either enumerate every moved old path or define explicit category mappings whose coverage is mechanically validated; mark the three new test/runner files as new rather than pretending they had old paths.
- Correct the legacy-root test invariant comment to `../../..`.

## Verification

Run `bash -n`, isolated Python compile, namespace and legacy-root tests, the five direct release/authority suites twice, and the 24-suite matrix. Run the completed matrix runner twice and compare its final output byte-for-byte. Raw internal transcripts must still be reported as non-identical where applicable; canonical transcripts and exact exit-code ledgers must match.

No production runtime, service, nginx, database, Git registry, sudoers installation, commit, push, reset or checkout action is authorized. Do not touch the documented `/etc/solarsage/env` and root-only pre-existing blockers. Stop for independent review.
