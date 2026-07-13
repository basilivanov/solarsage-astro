# Stage 2 corrective master — release hardening, main integration and production deploy

Дата: `2026-07-13`
Feature branch: `preview/solarsage-v2-human-first-navigator-ux`
Accepted Stage 1 SHA: `7179818b6504be725afa48b513bc1f0a7852e387`
Current main/origin-main: `c9bc36bd9a947566eddb1ffcf5617967c7412676`
Evidence source: `126_STAGE_2_W0_RELEASE_CANDIDATE_GATE_INVENTORY_TZ.md`

Статус: **STAGE 2 EXECUTION MASTER — ONE AUTHORIZED WAVE AT A TIME**

## 1. Final completion contract

The program is complete only when all are simultaneously true:

1. feature branch release gates are green and pushed;
2. `main` contains the accepted feature through an audited merge commit;
3. local `main`, tracking `origin/main` and remote main are identical;
4. shared Python contract dependency is built once from accepted main and the
   exact same wheel is installed in API and sidecar venvs;
5. canonical production flags are enabled exactly once during deploy;
6. production frontend is built from accepted main and atomically swapped into
   `.next-prod` with a preserved rollback dist;
7. sidecar/API/frontend are restarted in dependency-safe order and healthy;
8. production Telegram HMAC flow returns and renders real V2, not dev auth;
9. desktop/mobile real-browser proof shows long/medium/fast, actions,
   disclosures and 12-sphere navigation without fixture/interception;
10. logs/privacy/security/rollback evidence is clean;
11. all canonical tests and release guardrails pass from deployed main.

Stage 1 local preview success is necessary evidence but not final completion.

## 2. W0 evidence summary

Already green:

```text
contracts generate/check/compat/fixture
Vitest 1067
typecheck
prod/contracts guards
API pytest 1405 passed / 4 skipped
sidecar pytest 201 passed
preview security 163 passed
API/sidecar pip check
isolated Next production build
production-import isolation
```

Release blockers discovered:

```text
feature diff hygiene: 72 issues / 18 historical docs
secrets guard: 2 tracked baseline literals
ignored empty py-contract egg-info masks metadata test
tracked source ESLint: 64 errors / 5 warnings / 27 paths
feature-added ESLint: 24 errors / 1 warning / 9 paths
active GRACE slice: 49 violations / 41 paths
feature-added API Ruff: 97 errors / 19 paths
feature-added API MyPy: 70 errors / 19 paths
sidecar Ruff tool absent in sidecar venv; API venv Ruff is available
aggregate ESLint incorrectly traverses three ignored Next build trees
```

The full repository also has older Ruff/MyPy debt outside feature-added lines.
The release standard is:

- all canonical release commands from Stage 2 master green;
- no new Ruff/MyPy issue on feature-added Python lines;
- changed API/sidecar modules pass scoped Ruff/MyPy where applicable;
- legacy static debt outside the feature is documented and must not be made
  worse, but is not substituted for the canonical test/guardrail matrix.

## 3. Wave decomposition

### S2.W1 — mechanical release hygiene

Owns only:

- 18 exact historical markdown files reported by `git diff --check`;
- `DEPLOYMENT_GUIDE.md` and `scripts/alert.sh` secret-like example literals;
- removal of one exact empty ignored egg-info directory;
- inventory/master/implementation docs 126–128.

Exit:

```text
git diff --check origin/main...feature = PASS
guardrails:secrets = PASS
py-contracts tests = 44 PASS
commit/push
```

### S2.W2A — ESLint perimeter and build-output isolation

Architecturally correct the lint perimeter before source fixes:

- ESLint ignores `.next-prod`, `.next-v2-preview`, `.next-v2-real-preview` and
  release-candidate `.next-stage*` output;
- historical docs capture scripts are outside runtime lint perimeter;
- browser/test/Node globals are declared by exact file-class config, not global
  blanket suppression;
- no rule is disabled merely to hide source errors.

Exit: aggregate build-output noise zero; remaining errors are tracked sources
only and deterministically enumerated.

### S2.W2B — frontend tracked-source lint and hooks correctness

Own the exact tracked source/test path list from W0. Fix:

- unused parameters/imports through removal or `_` naming where API-compatible;
- real missing globals through correct ESLint environments;
- hooks dependencies through stable memoization/callback semantics, never
  blanket disable comments;
- no conditional assignment ambiguity.

All frontend tests, typecheck, full `guardrails:frontend` and build must pass.

### S2.W2C — active GRACE slice migration

Add truthful `AI_HEADER`, module contract and module map to the exact 41 active
slice paths. No runtime behavior rewrite. Preserve public test selectors and
module APIs. The repaired linter, marker gate and negative tests must all pass.

### S2.W3A — feature Python Ruff correction

Fix only the 19 feature-added API path group first. Mechanical auto-fixes may be
used only when review proves semantic equivalence. Remove dead imports, split
multi-statements, replace invalid aliases, and retain GRACE contracts.

Required: scoped Ruff zero, full API pytest green, contracts green.

### S2.W3B — feature Python MyPy correction

Fix the exact 19 feature-added typed path group. No `Any` blanket, file-wide
ignore, cast-only masking or schema weakening. Prefer precise shared contract
types, narrowing and typed builders.

Required: scoped MyPy zero on owned paths, Ruff remains zero, API full green.

### S2.W3C — sidecar changed-path static proof

Use the existing API venv Ruff executable against changed sidecar paths; do not
install test tools into production sidecar venv merely for lint. Fix only
feature-added sidecar issues, run 201 sidecar tests and pip check.

### S2.W4 — final release candidate

From clean pushed feature:

- all contracts commands and shared package tests;
- full Vitest/typecheck/frontend/prod/contracts/secrets/GRACE guards;
- full API and sidecar pytest;
- scoped changed-path Ruff/MyPy;
- isolated build and candidate smoke;
- strict 3003 real V2 E2E again;
- production-dead preview security proof;
- real Telegram HMAC authentication transport smoke without enabling global V2;
- final branch audit and rollback-space proof.

Exit:

```text
READY_STAGE_2_RELEASE_CANDIDATE_FOR_MAIN
```

### S2.W5 — main merge and push

Execute a dedicated amended main-integration TZ:

- fetch and prove main unchanged/direct ancestor;
- switch main and fast-forward local main to origin;
- merge `--no-ff` with exact message;
- post-merge contracts/typecheck/tests/diff proof before push;
- normal push; no force;
- local/tracking/remote main equality.

No runtime deploy in the merge wave.

### S2.W6 — controlled production deploy

Dedicated runtime wave:

1. backup env/build and record rollback commands;
2. build one shared-contract wheel from accepted main;
3. install same wheel into both venvs, `pip check`, version parity;
4. build isolated production frontend candidate;
5. candidate smoke on managed loopback 3010;
6. atomically preserve old `.next-prod` and swap candidate;
7. set only the two V2 flags true in canonical env;
8. restart sidecar, API, frontend in order; nginx unchanged;
9. stop and rollback on any failed health gate.

### S2.W7 — production acceptance

Prove from deployed main:

- canonical health/listeners/PIDs;
- exact deployed SHA;
- real production V2 payload/horizons/actions/provenance;
- Telegram HMAC desktop/mobile UI with no `/api/auth/dev`;
- no fixture/mock/interception/3003 dependency;
- screenshots/redacted network artifacts;
- logs/privacy/security clean;
- rollback dist/env/wheel available and commands validated;
- all final canonical tests/guards green.

Only then may the architect mark the overall goal complete.

## 4. Global protocol

- Architect/reviewer writes detailed TZ under this directory.
- Coder executes only in interactive `tmux astro:0.0`.
- No subagents.
- If coder is running, next pane check only after a full 3 minutes.
- Each material wave receives independent architect review before commit/push.
- Main, env, systemd and production build mutations require dedicated waves.
- Frozen unrelated paths are never touched/staged:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

- No manual uvicorn, API 8001, runtime fixtures, force push, checkout/reset,
  broad process killing or secret/personal-data output.

## 5. Current authorized next wave

Only `128_STAGE_2_W1_MECHANICAL_RELEASE_HYGIENE_TZ.md` is authorized next.
No frontend/Python/main/runtime work begins until its architect acceptance.
