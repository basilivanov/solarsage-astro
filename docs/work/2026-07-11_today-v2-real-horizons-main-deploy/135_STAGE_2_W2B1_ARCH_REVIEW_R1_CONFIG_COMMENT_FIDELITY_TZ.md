# Stage 2.W2B-1 — architect review R1: ESLint config comment fidelity

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`84014495095a19286f0c2edf33531be5052fd5fa`
Parent: `134_STAGE_2_W2B1_TYPESCRIPT_AWARE_ESLINT_RULE_SEMANTICS_TZ.md`

Статус: **REWORK REQUIRED — COMMENT-ONLY, SAME CONFIG SCOPE, NO COMMIT/PUSH**

## 1. Accepted behavior

Architect accepts the dependency/config behavior and evidence:

```text
parser/plugin                    8.60.0 / 8.60.0
TS core no-undef                 off
TS core no-unused-vars           off
TS extension no-unused-vars      error
JS core rules                    preserved
fresh real remainder             33 errors / 6 warnings / 28 paths
telegram declaration false noise 0
typecheck/focused/contracts/prod PASS
```

Do not change any executable config, dependency, rule, severity, ordering,
ignore, global, source file or lockfile content.

## 2. Review finding

The comment immediately before the generic core `no-unused-vars` block still
says:

```text
ENFORCED_GLOBS block below sets no-unused-vars: "off" to let GRACE
contracts-only-import do the policing instead.
```

That statement is now false. The later GRACE block disables only the core rule,
while all TypeScript paths, including `ENFORCED_GLOBS`, inherit the active
`@typescript-eslint/no-unused-vars` extension rule.

Configuration commentary must describe the calculated behavior accurately.

## 3. Exact correction

Edit only the stale comment in:

```text
eslint.config.mjs
```

Replace the three-line comment above the generic core rule with this exact
two-line wording:

```js
  // Core JavaScript unused-variable policy. The TypeScript block below replaces
  // it with @typescript-eslint/no-unused-vars for all TS/TSX, including GRACE.
```

No other byte in `eslint.config.mjs`, `package.json` or `pnpm-lock.yaml` may
change. Architect docs 134 and 135 remain unchanged and untracked.

## 4. Proof

After the comment-only correction require:

```bash
node --check eslint.config.mjs
pnpm typecheck
pnpm exec eslint . -f json > /tmp/stage2-w2b1-r1-eslint.json
git diff --check
```

Preserve the expected ESLint exit 1 and parse JSON. It must remain exactly:

```text
33 errors / 6 warnings / 28 paths
@typescript-eslint/no-unused-vars = 27 errors
no-empty = 5 errors
require-yield = 1 error
react-hooks/exhaustive-deps = 5 warnings
unused eslint-disable directive = 1 warning
parsing/fatal/unmatched/build-doc findings = 0
```

Also prove via `--print-config` that one ordinary TypeScript path and one GRACE
TypeScript path both retain core `no-unused-vars=off` and extension
`@typescript-eslint/no-unused-vars=error`.

Final tracked scope remains exactly:

```text
eslint.config.mjs
package.json
pnpm-lock.yaml
```

Index empty. Runtime unchanged. No commit/push.

## 5. Callback

```text
READY_STAGE_2_W2B1_R1_COMMENT_FIDELITY_REVIEW
comment_only_correction: PASS
executable_config_delta_from_134: ZERO
tracked_scope: EXACT_3_CONFIG_DEPENDENCY_PATHS
ordinary_ts_extension_rule: ERROR
grace_ts_extension_rule: ERROR
remaining_real_source: 33 errors / 6 warnings / 28 paths
typecheck: PASS
git_diff_check: PASS
index: EMPTY
commit_push: NOT_PERFORMED
runtime_services: UNCHANGED
ports: 3003/8001/18092 ABSENT
architect_docs: UNCHANGED_134_135
```

Then stop for architect review.
