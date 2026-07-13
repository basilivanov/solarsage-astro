# Stage 2.W2B-1 — architect acceptance, exact commit and push

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`84014495095a19286f0c2edf33531be5052fd5fa`
Accepted implementation:

- `134_STAGE_2_W2B1_TYPESCRIPT_AWARE_ESLINT_RULE_SEMANTICS_TZ.md`;
- `135_STAGE_2_W2B1_ARCH_REVIEW_R1_CONFIG_COMMENT_FIDELITY_TZ.md`.

Статус: **ARCHITECT ACCEPTED — AUTHORIZED EXACT COMMIT/PUSH ONLY**

## 1. Accepted evidence

Architect independently accepts:

```text
tracked implementation scope          eslint.config.mjs, package.json, pnpm-lock.yaml
plugin/parser resolved versions       8.60.0 / 8.60.0
plugin package spec                    exact 8.60.0
unrelated dependency movement         zero
frozen install                         PASS
all authored TS/TSX parser coverage   PASS
TS core no-undef                       off
TS core no-unused-vars                 off
TS extension no-unused-vars            error
ordinary JS core rules                preserved
GRACE TS extension rule               active
telegram declaration false findings   zero
parsing/unmatched/build-doc findings   zero
fresh honest remainder                33 errors / 6 warnings / 28 paths
typecheck                              PASS
focused Vitest                         33 PASS
contracts check                       110 PASS
production guard                      PASS
working diff check                    PASS
runtime/services                      unchanged
ports 3003/8001/18092                 absent
```

The exact remainder now consists of:

```text
@typescript-eslint/no-unused-vars     27 errors
no-empty                                5 errors
require-yield                           1 error
react-hooks/exhaustive-deps             5 warnings
unused eslint-disable directive         1 warning
```

No further edit is authorized in this acceptance wave.

## 2. Mandatory preflight

Before staging:

1. read this document completely;
2. fetch origin without merge or rebase;
3. prove branch, local HEAD, tracking ref and remote feature remain exactly at
   the base SHA above;
4. prove `main` and `origin/main` remain
   `c9bc36bd9a947566eddb1ffcf5617967c7412676` and are an ancestor of feature;
5. prove index empty;
6. prove the only tracked diff is the accepted exact three-path implementation;
7. prove architect docs 134, 135 and 136 are the only task docs untracked;
8. prove the only other untracked paths are the five frozen paths;
9. prove runtime/services unchanged and 3003/8001/18092 absent.

Stop before staging on any mismatch. No reset, rebase, force push, source edit,
runtime operation or dependency update.

## 3. Exact staging

Stage only these six explicit paths:

```text
eslint.config.mjs
package.json
pnpm-lock.yaml
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/134_STAGE_2_W2B1_TYPESCRIPT_AWARE_ESLINT_RULE_SEMANTICS_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/135_STAGE_2_W2B1_ARCH_REVIEW_R1_CONFIG_COMMENT_FIDELITY_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/136_STAGE_2_W2B1_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md
```

Use explicit paths only. Never `git add .` or `git add -A`.

Before commit require:

```text
staged path count           exactly 6
staged path set             exact list above
unstaged tracked diff       empty
frozen paths in index       none
git diff --cached --check   PASS
```

If an architect-doc EOF issue appears, stop rather than editing it.

## 4. Commit and post-commit gates

Create exactly one commit:

```text
chore(frontend): use typescript-aware lint rules
```

After commit and before push run:

```bash
node --check eslint.config.mjs
pnpm install --frozen-lockfile
pnpm typecheck
npx vitest run __tests__/guardrails/preview-isolation.test.ts \
  __tests__/scripts/preview-v2-real.test.ts
pnpm contracts:check
pnpm guardrails:prod
git diff --check origin/main...HEAD
```

Run aggregate ESLint as expected-nonzero JSON:

```bash
pnpm exec eslint . -f json > /tmp/stage2-w2b1-accepted-eslint.json
```

Require exact stable result:

```text
33 errors / 6 warnings / 28 paths
27 extension unused errors
5 no-empty errors
1 require-yield error
5 hook warnings
1 unused-directive warning
zero parsing/fatal/unmatched/build-doc findings
```

Also prove calculated config on ordinary TS and GRACE TS retains core unused
off and extension unused error. Do not correct any source finding here.

## 5. Push and final equality

Push normally to the existing feature branch, never force. Then prove:

```text
local HEAD = tracking ref = remote feature SHA
tracked worktree clean
index empty
only five frozen unrelated untracked paths remain
main untouched
runtime/env/systemd untouched
3003/8001/18092 absent
```

Do not begin W2B-2 in this wave.

## 6. Callback

```text
PUSHED_STAGE_2_W2B1_TYPESCRIPT_AWARE_LINT
commit: <sha> chore(frontend): use typescript-aware lint rules
staged_scope: EXACT_6
plugin_parser_versions: 8.60.0_EQUAL
frozen_install: PASS
typescript_parser_coverage: PASS_ALL_AUTHORED_TS_TSX
ordinary_ts_extension_rule: ERROR
grace_ts_extension_rule: ERROR
remaining_real_source: 33 errors / 6 warnings / 28 paths
typecheck: PASS
focused_tests: 33 PASS
contracts_check: 110 PASS
prod_guard: PASS
feature_diff_check: PASS_ZERO
head_tracking_remote: EQUAL
tracked_index: CLEAN_EMPTY
runtime_services: UNCHANGED
ports: 3003/8001/18092 ABSENT
main_deploy: NOT_STARTED
```

Then stop.
