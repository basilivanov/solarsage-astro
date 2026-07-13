# Stage 2.W2B-1 — TypeScript-aware ESLint rule semantics

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`84014495095a19286f0c2edf33531be5052fd5fa`
Parent: `133_STAGE_2_W2A_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md`

Статус: **AUTHORIZED CONFIG/DEV-DEPENDENCY CORRECTION — NO SOURCE EDITS, NO COMMIT/PUSH**

## 1. Problem proved by accepted W2A inventory

W2A correctly made every authored TypeScript file parseable and exposed:

```text
152 errors / 6 warnings / 55 paths
```

But the generic ESLint core rules are not TypeScript-aware:

- core `no-unused-vars` reports declaration-only callback parameter names and
  global interface declarations as unused; `types/telegram-web-app.d.ts` alone
  receives 34 false errors;
- core `no-undef` does not use the TypeScript type environment and reports
  valid DOM, Node and TypeScript names such as `RequestInit`, `Response`,
  `HeadersInit`, `NodeJS`, `AbortSignal`, `DOMException`, `require` and
  `__dirname`, while canonical `pnpm typecheck` passes;
- adding more type names to a hand-maintained global list would be an
  incomplete, environment-leaking workaround;
- renaming declaration parameters or changing runtime code to satisfy these
  false findings would corrupt the public type surface and obscure the real
  W2B debt.

Official typescript-eslint guidance requires:

1. disable the base `no-unused-vars` rule for TypeScript and enable the
   `@typescript-eslint/no-unused-vars` extension rule;
2. disable core `no-undef` for TypeScript files and let TypeScript validate
   identifiers/types.

Primary references:

- `https://typescript-eslint.io/rules/no-unused-vars/`
- `https://typescript-eslint.io/troubleshooting/faqs/eslint/#i-get-errors-from-the-no-undef-rule-about-global-variables-not-being-defined-even-though-there-are-no-typescript-errors`

This subwave establishes truthful lint semantics first. It deliberately does
not fix any resulting real source finding; the exact new inventory becomes the
input to W2B-2.

## 2. Exact edit scope

Coder may edit only:

```text
package.json
pnpm-lock.yaml
eslint.config.mjs
```

Architect document 134 must remain byte-identical and untracked during this
implementation wave. No app/component/hook/lib/test/e2e/type/generated file
edit. No commit or push.

## 3. Mandatory preflight

Before editing:

1. read this document completely;
2. prove branch, local HEAD, tracking ref and remote branch all equal the base
   SHA above;
3. prove `main` and `origin/main` still equal
   `c9bc36bd9a947566eddb1ffcf5617967c7412676` and are an ancestor of HEAD;
4. prove tracked worktree and index are clean;
5. prove only the five frozen unrelated untracked paths plus architect doc 134
   are present;
6. record hashes of `package.json`, `pnpm-lock.yaml`, `eslint.config.mjs` and
   document 134;
7. prove canonical services unchanged and 3003/8001/18092 absent.

Frozen paths remain untouchable and must never enter the index:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Stop on any mismatch. No reset/rebase/force operation.

## 4. Add the exact TypeScript ESLint extension dependency

The installed parser resolved by W2A is:

```text
@typescript-eslint/parser 8.60.0
```

Add the matching plugin as an exact dev dependency through pnpm, not by manual
lockfile editing:

```bash
pnpm add --save-dev --save-exact @typescript-eslint/eslint-plugin@8.60.0
```

Required after installation:

```text
package.json contains exact version 8.60.0
pnpm-lock.yaml is regenerated only by pnpm
resolved parser version = 8.60.0
resolved plugin version = 8.60.0
pnpm install --frozen-lockfile = PASS
```

Do not update any other dependency, change package-manager metadata or run a
broad dependency upgrade. If pnpm proposes unrelated version movement, stop and
report it.

## 5. Exact ESLint semantic model

In `eslint.config.mjs`:

1. import the plugin:

```js
import tsPlugin from "@typescript-eslint/eslint-plugin";
```

2. extend the general `files: ["**/*.{ts,tsx}"]` block created in W2A;
3. preserve its parser and parser options exactly;
4. register the plugin under its canonical namespace:

```js
plugins: { "@typescript-eslint": tsPlugin },
```

5. add these rules only in that TypeScript block:

```js
rules: {
  "no-undef": "off",
  "no-unused-vars": "off",
  "@typescript-eslint/no-unused-vars": [
    "error",
    {
      argsIgnorePattern: "^_",
      varsIgnorePattern: "^_",
      caughtErrorsIgnorePattern: "^_",
      destructuredArrayIgnorePattern: "^_",
      ignoreRestSiblings: true,
    },
  ],
},
```

Architectural meaning:

- TypeScript/TSX identifier validity remains enforced by `pnpm typecheck`;
- real unused TypeScript variables/imports/parameters remain errors through the
  extension rule;
- underscore is the explicit intentional-unused convention;
- a property extracted only to omit it before a rest object is not treated as
  a fake unused value;
- ordinary JS/JSX/MJS/CJS files retain core recommended `no-undef` and
  `no-unused-vars` behavior;
- the existing Buffer scope for test/e2e/root-config files remains truthful for
  JavaScript as well as harmless for TypeScript;
- GRACE rules, React Hooks rules, ignores and W2A parser coverage remain active.

Do not use `tsPlugin.configs.recommended` or another preset in this subwave: it
would enable unrelated rules and make the inventory non-isolatable. Do not add
an ESLint disable, severity downgrade, global wildcard, source ignore or
per-file exception.

## 6. Required semantic proof

Run:

```bash
node --check eslint.config.mjs
pnpm install --frozen-lockfile
pnpm typecheck
```

Prove with `eslint --print-config`:

### TypeScript representative paths

```text
types/telegram-web-app.d.ts
lib/adapters/today-payload.ts
__tests__/lib/adapt-payload.test.ts
components/today/today-screen.tsx
e2e/real-v2-preview.spec.ts
packages/contracts/index.ts
```

Each must show:

```text
parser = typescript-eslint/parser@8.60.0
no-undef = off
no-unused-vars = off
@typescript-eslint/no-unused-vars = error
```

### JavaScript representative paths

```text
next.config.mjs
e2e/mock-visual/start-v2-preview.mjs
```

Each must retain core `no-undef` and `no-unused-vars`; the e2e path must retain
`Buffer: readonly`. The TypeScript extension rule must not accidentally apply
to JavaScript.

### Ignore representatives

The following remain ignored:

```text
.next-prod/server/app/page.js
.next-v2-real-preview/server/app/page.js
.next-stage2-probe/server/app/page.js
docs/work/.../capture-audit.cjs
```

No persistent probe file may be created.

## 7. Fresh honest inventory

Run aggregate ESLint as JSON while preserving its expected non-zero exit:

```bash
pnpm exec eslint . -f json > /tmp/stage2-w2b1-eslint.json
```

Parse and report exact error/warning/path/rule counts. Required properties,
not a guessed total:

1. parsing/fatal/config errors = 0;
2. unmatched authored TS/TSX = 0;
3. build/docs/report paths = 0;
4. core `no-undef` findings in TS/TSX = 0;
5. core `no-unused-vars` findings in TS/TSX = 0;
6. `types/telegram-web-app.d.ts` has zero unused-variable findings without any
   edit to that file;
7. valid type-only/function-signature names are not reported;
8. real source findings are emitted as
   `@typescript-eslint/no-unused-vars`, `no-empty`, `require-yield`, React Hooks
   or other truthful rule IDs;
9. no rule is suppressed merely to reach zero.

Write a deterministic per-path/per-rule inventory to:

```text
/tmp/stage2-w2b1-eslint-inventory.txt
```

This is temporary evidence only and must not be staged.

## 8. Regression gates

Run:

```bash
npx vitest run __tests__/guardrails/preview-isolation.test.ts \
  __tests__/scripts/preview-v2-real.test.ts
pnpm contracts:check
pnpm guardrails:prod
git diff --check
```

Expected focused Vitest count is 33 and contracts check is 110. Do not require
`pnpm lint` or `guardrails:frontend` to be green yet: the honest W2B-2 source
remainder is intentionally still present. Do require their ESLint phase to be
the same deterministic remainder if either aggregate command is run.

No generated contract diff, runtime change, service restart or port start.

## 9. Final state and callback

Required final tracked diff exact paths:

```text
eslint.config.mjs
package.json
pnpm-lock.yaml
```

Index empty. Document 134 unchanged. Frozen paths untouched. No commit/push.

Return:

```text
READY_STAGE_2_W2B1_TYPESCRIPT_AWARE_LINT_REVIEW
tracked_scope: EXACT_3_CONFIG_DEPENDENCY_PATHS
plugin_parser_versions: 8.60.0_EQUAL
frozen_install: PASS
typescript_parser_coverage: PASS_ALL_AUTHORED_TS_TSX
ts_core_no_undef: OFF
ts_core_no_unused_vars: OFF
ts_extension_no_unused_vars: ERROR
javascript_core_rules: PRESERVED
telegram_declaration_false_findings: ZERO
parsing_errors: ZERO
unmatched_authored_typescript: ZERO
build_docs_findings: ZERO
remaining_real_source: <exact errors / warnings / paths / rule counts>
typecheck: PASS
focused_tests: 33 PASS
contracts_check: 110 PASS
prod_guard: PASS
git_diff_check: PASS
index: EMPTY
commit_push: NOT_PERFORMED
runtime_services: UNCHANGED
ports: 3003/8001/18092 ABSENT
architect_doc: UNCHANGED_134
```

Then stop for architect review. Do not begin source fixes.
