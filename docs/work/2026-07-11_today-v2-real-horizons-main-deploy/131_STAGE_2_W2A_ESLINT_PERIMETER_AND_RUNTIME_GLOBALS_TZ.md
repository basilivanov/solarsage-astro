# Stage 2.W2A — ESLint perimeter and runtime globals

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`58c9136b97fde78f4ad776bcd83c8591481ecde4`
Parent: `127_STAGE_2_CORRECTIVE_RELEASE_MAIN_DEPLOY_WAVE_MASTER.md`
Evidence: `/tmp/stage2-w0-guardrails-frontend.log`,
`/tmp/stage2-w0-eslint-source.log`

Статус: **AUTHORIZED CONFIG-ONLY CORRECTION — NO SOURCE ERROR SUPPRESSION**

## 1. Problem

The aggregate frontend guard reports:

```text
10695 errors / 62 warnings
```

Of those:

```text
ignored Next build outputs = 10631 errors / 57 warnings
tracked source              = 64 errors / 5 warnings
historical docs capture JS  = outside product/tool source perimeter
```

The current flat ESLint config ignores only `.next/**`, so canonical production,
preview and release-candidate build trees are linted as source. It also gives
all files one incomplete browser-global set, producing false `no-undef` errors
for standard DOM/type globals and Node-only `Buffer`.

This wave fixes only the lint boundary and environment facts. It must not hide
real tracked-source unused-variable or hooks findings.

## 2. Exact edit scope

Coder may edit only:

```text
eslint.config.mjs
```

Architect document 131 remains byte-identical and untracked until later
acceptance. No other product/test/config/docs file edit. No commit/push in this
implementation wave.

## 3. Build and non-source ignores

In the top global ignore block, preserve all current ignores and add truthful
repository-output boundaries:

```text
.next-*/**
docs/**
playwright-report/**
test-results/**
```

Rationale:

- `.next-*/**` covers canonical `.next-prod`, real/dev preview dist, isolated
  `.next-stage*`, `.next-release-*` and rollback Next build directories;
- all are generated/rollback artifacts, never authored source;
- `docs/**` contains Markdown/evidence/capture artifacts, not runtime JS source;
- Playwright result/report trees are generated evidence.

Keep `.next/**` explicitly. Do not ignore `app`, `components`, `lib`, `hooks`,
`__tests__`, `e2e`, `packages` or the repository root generally.

Do not add exact individual failing source files to ignores.

## 4. Runtime-global model

Keep the existing browser globals and extend them only with standard names that
are already provided by TypeScript DOM/modern JS runtime and are used in tracked
browser/test code:

```text
URL
Event
Node
NodeFilter
FrameRequestCallback
structuredClone
```

Add a separate Node/test global block, scoped only to authored test/e2e/config
JavaScript/TypeScript paths that need Node runtime facts. At minimum cover:

```text
__tests__/**/*.{ts,tsx,js,jsx,mjs,cjs}
e2e/**/*.{ts,tsx,js,jsx,mjs,cjs}
*.config.{ts,js,mjs,cjs}
```

Declare there:

```text
Buffer: readonly
```

`process` is already in the existing globals; do not duplicate or remove it
unless necessary for a clean deterministic config shape.

Do not add application-specific names, disable `no-undef`, or mark arbitrary
identifiers global.

## 5. Rule invariants

Preserve:

- `js.configs.recommended`;
- `no-unused-vars` error with underscore convention;
- React hooks rules on TSX/JSX;
- GRACE plugin enforced globs and rules;
- no rule severity downgrade;
- no eslint-disable comments.

This wave is expected to leave real tracked source errors for W2B. A non-zero
aggregate ESLint result is acceptable only if all remaining findings are
authored source paths and no ignored/build/docs path appears.

## 6. Gates and exact classification

Run:

```bash
node --check eslint.config.mjs
pnpm typecheck
pnpm guardrails:prod
```

Then diagnostic commands, preserving exit codes:

```bash
pnpm exec eslint . > /tmp/stage2-w2a-eslint-aggregate.log 2>&1

pnpm exec eslint . \
  --ignore-pattern '.next-prod/**' \
  --ignore-pattern '.next-v2-preview/**' \
  --ignore-pattern '.next-v2-real-preview/**' \
  > /tmp/stage2-w2a-eslint-source-compare.log 2>&1
```

Required:

1. aggregate and source-compare have the exact same authored-source
   error/warning/path set;
2. zero path begins `.next`, `docs/`, `test-results/` or `playwright-report/`;
3. false `no-undef` findings for `URL`, `Event`, `Node`, `NodeFilter`,
   `FrameRequestCallback`, `structuredClone`, `Buffer` are zero;
4. real remaining errors/warnings are reported without suppression;
5. aggregate log shrinks from 11,534 lines to a bounded tracked-source report.

Also prove config ignore behavior directly using `--debug` or calculated config
for representative paths, without printing environment values:

```text
.next-prod/server/...                       ignored
.next-v2-real-preview/server/...            ignored
.next-stage2-probe/server/...               ignored
docs/work/.../capture-audit.cjs              ignored
e2e/mock-visual/start-v2-preview.mjs         linted with Buffer global
components/today/today-screen.tsx            linted
```

Do not create persistent probe files. Use existing paths or `/tmp` plus
`--stdin-filename` where possible.

## 7. Regression gates

Run:

```bash
npx vitest run __tests__/guardrails/preview-isolation.test.ts \
  __tests__/scripts/preview-v2-real.test.ts
pnpm contracts:check
git diff --check
```

No generated contract diff.

## 8. Final state and callback

Tracked diff exact one path: `eslint.config.mjs`. Index empty. Architect doc 131
unchanged. Frozen untracked paths untouched. Runtime services unchanged and
3003/8001/18092 absent.

Callback:

```text
READY_STAGE_2_W2A_ESLINT_PERIMETER_REVIEW
tracked_scope: ESLINT_CONFIG_ONLY
config_syntax: PASS
build_output_findings: ZERO
docs_capture_findings: ZERO
standard_global_false_undef: ZERO
aggregate_equals_source: PASS
remaining_source: <exact errors/warnings/paths/rules>
typecheck: PASS
prod_guard: PASS
focused_tests: <exact count> PASS
contracts_check: 110 PASS
git_diff_check: PASS
index: EMPTY
commit_push: NOT_PERFORMED
runtime_services: UNCHANGED
ports: 3003/8001/18092 ABSENT
architect_doc: UNCHANGED_131
```

Then stop for architect review.
