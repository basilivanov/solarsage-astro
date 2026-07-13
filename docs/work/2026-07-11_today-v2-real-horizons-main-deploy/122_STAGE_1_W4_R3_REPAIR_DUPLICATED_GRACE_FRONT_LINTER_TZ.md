# Stage 1.W4.R3 — repair duplicated frontend GRACE linter, then finish W4 gates

Дата: `2026-07-13`
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted base: `7d37acbaa31118a8545987a39a5fabe18fbb6e32`
Amends:

- `121_STAGE_1_W4_R2_ARCH_REVIEW_AND_BASELINE_LINT_CONTINUATION_TZ.md` sections 4.2 and 5.

Статус: **AUTHORIZED MINIMAL TOOLCHAIN REPAIR + CONTINUATION — NO COMMIT/PUSH/RESTART/PREVIEW**

## 1. Proven blocker and history

`bash scripts/grace/check-markers.sh` fails before checking any frontend file:

```text
scripts/grace_front_lint.py:588
from __future__ import annotations
SyntaxError: from __future__ imports must occur at the beginning of the file
```

The worktree file is byte-identical to accepted HEAD:

```text
sha256 = edd437608ea5c9b3f47c0e777575cb4477e1572b043e3b34d49ac068cb610031
lines  = 1097
mode   = executable / tracked 100755
```

Architect history review proves commit `748ff963b8fdc4c01086864052265339856427c5`
accidentally appended a second copy of almost the entire module after the first
working CLI terminator. The file has:

```text
from __future__ import annotations: lines 44 and 588
main():                           lines 509 and 1053
if __name__ == "__main__":       lines 550 and 1094
```

The pre-corruption parent was one 553-line executable module. This is a real
tracked toolchain defect, not a W4 implementation regression and not an
acceptable permanently skipped gate.

## 2. Authorized repair path

Expand the tracked diff allowlist by exactly one path:

```text
scripts/grace_front_lint.py
```

No other tooling/config/test path may change.

Repair with `apply_patch`; do not use checkout/reset or overwrite the whole file.

Required final structure:

1. retain the first real module implementation and its CLI;
2. delete the complete accidental duplicate beginning immediately after the
   first `sys.exit(main())`;
3. retain/add one final `# END_BLOCK: CLI` after the first CLI implementation;
4. exactly one future import, one `_parse_args`, one `main`, one `__main__` guard;
5. preserve executable mode `100755`;
6. no linter algorithm, marker grammar, path discovery, size threshold, error
   code or CLI behavior change;
7. final file must be below 600 lines.

The current top module contract falsely says this production tool consumes
“Mocks, fixtures” and outputs “Assertions”. Correct only those contract fields
to truthful, bounded wording:

```text
purpose: Enforce frontend GRACE banners, marker pairing and size limits.
inputs: CLI paths or grace/frontend.paths plus matching TS/JS source files.
outputs: Process status and machine/human-readable violation reports.
dependencies: Python standard library and repository frontend path manifest.
side_effects: Reads repository files and writes stdout/stderr.
emitted_logs: none.
invariants: Missing/empty active slice fails closed; lint behavior is deterministic.
failure_policy: Return 1 for configuration/read/contract violations, else 0.
```

Do not otherwise reformat or modernize the old file. Do not edit
`scripts/test_grace_front_lint.py`, `scripts/grace/check-markers.sh`,
`scripts/grace/check-negative.sh`, `eslint.config.mjs` or `scripts/guardrails.sh`.

## 3. Repair proof

Run exactly:

```bash
python3 -m py_compile scripts/grace_front_lint.py
python3 scripts/test_grace_front_lint.py
python3 scripts/grace_front_lint.py --quiet
bash scripts/grace/check-markers.sh
bash scripts/grace/check-negative.sh
```

All must pass. Also prove:

```bash
test "$(rg -c '^from __future__ import annotations$' scripts/grace_front_lint.py)" -eq 1
test "$(rg -c '^def main\(' scripts/grace_front_lint.py)" -eq 1
test "$(rg -c '^if __name__ == "__main__":' scripts/grace_front_lint.py)" -eq 1
test "$(stat -c '%a' scripts/grace_front_lint.py)" = 755
test "$(wc -l < scripts/grace_front_lint.py)" -lt 600
```

If any semantic linter/self-test/marker/negative gate fails after duplicate
removal, stop with the exact failure. Do not weaken the linter to make it pass.

## 4. Continue remaining R2 gates

After section 3 is fully green:

1. run the build-output-excluded ESLint diagnostic from 121 and record exact
   baseline errors/warnings;
2. prove every ESLint error reported for a touched lint-covered file is outside
   the current diff hunks;
3. run contracts generate, exact zero generated diff and contracts check from 121;
4. run the isolated build from 121;
5. remove only `.next-stage1-w4-r1-build` after successful build;
6. prove `next-env.d.ts` and `tsconfig.json` tracked bytes/mode/git diff unchanged;
7. capture final exact git/runtime/doc witnesses.

The aggregate `pnpm guardrails:frontend` need not be rerun: its ESLint stage is
already classified in 121. The actual GRACE marker and negative components must
now be green after this repair.

## 5. Final tracked scope

Exact nine tracked implementation/repair/test paths:

```text
apps/api/app/services/today_preview_access.py
apps/api/app/api/day.py
apps/api/tests/test_today_preview_access.py
lib/adapters/today-payload.ts
__tests__/lib/adapt-payload.test.ts
components/today/today-screen.tsx
__tests__/components/TodayScreen.test.tsx
e2e/real-v2-preview.spec.ts
scripts/grace_front_lint.py
```

Index empty. No commit/push, no service restart/reload, no 3003 start.
Architect docs 117–122 byte-identical after delivery. Frozen unrelated paths
remain untouched.

## 6. Callback

```text
READY_STAGE_1_W4_R3_GATES
r2_change: removed unrelated whole-file SHA guards only
toolchain_repair: duplicate frontend GRACE linter removed; behavior preserved
scope: EXACT_9_PATHS
preview_access_test_lines: N <= 700
grace_linter_lines_mode: N < 600 / 755
focused_backend: 83 passed
focused_frontend: 121 passed
typecheck: PASS
grace_linter_selftests: PASS (exact count)
grace_markers: PASS
grace_negative: PASS
frontend_eslint: CLASSIFIED_BASELINE (exact errors/warnings)
contracts_generate_diff: ZERO
contracts_check: PASS
isolated_build: PASS
next_env_tsconfig: BYTE_MODE_GIT_UNCHANGED
runtime_services: UNCHANGED
ports: 3003/8001/18092 ABSENT
index: EMPTY
commit_push: NOT_PERFORMED
architect_docs: UNCHANGED_117_TO_122
```

Then stop and wait for architect review.
