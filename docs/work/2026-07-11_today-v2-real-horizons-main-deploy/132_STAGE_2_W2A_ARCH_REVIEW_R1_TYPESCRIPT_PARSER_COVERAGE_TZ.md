# Stage 2.W2A — architect review R1: complete TypeScript parser coverage

Дата: `2026-07-13`
Parent: `131_STAGE_2_W2A_ESLINT_PERIMETER_AND_RUNTIME_GLOBALS_TZ.md`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`58c9136b97fde78f4ad776bcd83c8591481ecde4`

Статус: **REWORK REQUIRED — SAME ONE-FILE SCOPE, NO COMMIT/PUSH**

## 1. Review finding

The perimeter/ignore/global direction is correct:

```text
build-output findings = zero
docs capture findings = zero
aggregate/source compare = byte-identical
standard global false no-undef = zero
```

But the new Node/test file glob caused authored `.ts` tests to become matched by
ESLint without a TypeScript parser. Result:

```text
55 parsing-error findings
94 total errors / 79 paths
```

This exposes a pre-existing config hole: ordinary TypeScript files outside the
TSX and GRACE-specific blocks were previously reported as “no matching
configuration” and were not actually linted.

Release lint must cover authored TypeScript. Do not hide or ignore those files.

## 2. Exact correction

Continue editing only:

```text
eslint.config.mjs
```

Add one general TypeScript language block applying to all authored:

```text
**/*.{ts,tsx}
```

It must set:

```js
parser: tsParser
parserOptions: {
  ecmaVersion: "latest",
  sourceType: "module",
  ecmaFeatures: { jsx: true },
}
```

Place it so matching TypeScript files receive the parser before rule evaluation.
Existing more-specific TSX hooks and GRACE blocks may retain their parser
declarations; do not remove them in this narrow correction unless exact config
proof shows harmless deduplication is needed. Prefer the smallest addition.

Keep the W2A ignores and globals exactly. Do not:

- ignore `.ts`/`.tsx` paths;
- disable `parsing-error`, `no-unused-vars`, `no-undef` or hooks rules;
- add TypeScript source paths one by one;
- introduce type-aware project parsing or a new dependency;
- edit any source/test file.

## 3. Required proof

Run:

```bash
node --check eslint.config.mjs
pnpm exec eslint . > /tmp/stage2-w2a-r1-eslint.log 2>&1
```

Non-zero is expected because W2B source debt remains. Required exact
properties:

1. `parsing-error = 0`;
2. zero “File ignored because no matching configuration” for authored
   `.ts/.tsx`;
3. representative config for each has `@typescript-eslint/parser`:

```text
lib/adapters/today-payload.ts
__tests__/lib/adapt-payload.test.ts
components/today/today-screen.tsx
e2e/real-v2-preview.spec.ts
packages/contracts/index.ts
```

4. ignored/build/docs representative paths remain ignored;
5. false global `no-undef` set from 131 remains zero;
6. report the new exact real source errors/warnings/path/rule counts for W2B.

Run regressions:

```bash
pnpm typecheck
npx vitest run __tests__/guardrails/preview-isolation.test.ts \
  __tests__/scripts/preview-v2-real.test.ts
pnpm contracts:check
pnpm guardrails:prod
git diff --check
```

## 4. Final callback

```text
READY_STAGE_2_W2A_R1_TYPESCRIPT_COVERAGE_REVIEW
tracked_scope: ESLINT_CONFIG_ONLY
config_syntax: PASS
typescript_parser_coverage: PASS_ALL_AUTHORED_TS_TSX
parsing_errors: ZERO
unmatched_authored_typescript: ZERO
build_docs_findings: ZERO
standard_global_false_undef: ZERO
remaining_real_source: <exact counts/rules/paths>
typecheck: PASS
focused_tests: 33 PASS
contracts_check: 110 PASS
prod_guard: PASS
git_diff_check: PASS
index: EMPTY
commit_push: NOT_PERFORMED
runtime_services: UNCHANGED
ports: 3003/8001/18092 ABSENT
architect_docs: UNCHANGED_131_132
```

Then stop for architect review.
