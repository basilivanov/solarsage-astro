# Stage 2 master — approved real preview to main and production deployment

Дата: 2026-07-13
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Parent plan: `101_TWO_STAGE_COMPLETION_MASTER_PLAN.md`
Prerequisite: accepted Stage 1 strict real V2 preview
Статус: **RELEASE STAGE MASTER — NOT YET AUTHORIZED FOR EXECUTION**

## 1. Stage outcome

Move the user-approved real V2 implementation from feature preview into the
canonical production stack:

~~~text
accepted feature branch
  -> full release candidate gates
  -> main merge/push
  -> shared contract dependency convergence
  -> V2 flags enabled
  -> sidecar/API/frontend safe restart/build swap
  -> production Telegram HMAC + real browser proof
  -> rollback-ready accepted deployment
~~~

No release operation starts merely because local 3003 looks correct.

## 2. Preconditions

Required before any main/runtime operation:

- user explicitly approves Stage 1 UI on 3003;
- strict real API E2E passed desktop/mobile;
- feature branch tracked clean/index empty/local=origin;
- all W3/Stage 1 docs committed;
- no open review finding;
- origin/main is ancestor of feature branch;
- no unrelated/frozen path in branch diff;
- no generated contract drift;
- rollback storage space and service permissions confirmed.

If main moved, stop and review; no automatic rebase/merge conflict resolution.

## 3. Wave decomposition

### S2.W1 — visual approval corrections

Run only if user asks for changes after viewing 3003.

Rules:

- real backend path remains mandatory;
- frontend never derives astrology/advice;
- backend copy/provenance/timing remain source;
- each correction gets exact ТЗ, tests, architect review, commit/push;
- rerun desktop/mobile screenshots;
- no main/deploy.

### S2.W2 — B5 release-candidate hardening

#### Contracts

~~~bash
pnpm contracts:generate
pnpm contracts:check
pnpm contracts:compat
pnpm contracts:fixture:check
~~~

Generation must leave no diff.

#### Frontend

~~~bash
npx vitest run
pnpm typecheck
pnpm guardrails:prod
pnpm guardrails:contracts
pnpm guardrails:frontend
NEXT_DIST_DIR=.next-stage2-rc pnpm build
~~~

#### Backend

~~~bash
apps/api/.venv/bin/python -m pytest apps/api/tests/ -q
apps/solarsage/venv/bin/python -m pytest apps/solarsage/tests/ -q
~~~

#### Real E2E

- local dev-auth strict V2 on 3003;
- Telegram HMAC release-candidate flow without route interception;
- ordinary/public preview override denial;
- fixture/mock network absence;
- mobile/desktop/dark/390px;
- error/locked/unavailable paths remain honest.

#### Security release proof

Preview marker boundary:

~~~text
APP_ENV=production -> false
public host -> false
ordinary Telegram user -> false
wrong/missing header -> false
global V2 flags remain sole production selector
~~~

Decide before main:

- keep development-only boundary with exhaustive production-dead proof; or
- remove it and adjust local preview strategy.

Default recommendation: keep it only if dead-code/security proof is strong and
it materially preserves one-command local diagnosis after deploy.

S2.W2 exit:

~~~text
READY_STAGE_B_FOR_MAIN_RELEASE
~~~

### S2.W3 — final branch audit and main merge

Amend and execute `90_MAIN_RELEASE_DEPLOY_TZ.md` only after architect acceptance.

#### Preflight

~~~bash
git fetch origin --prune
git status --short --branch
git rev-parse preview/solarsage-v2-human-first-navigator-ux
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git rev-parse main
git rev-parse origin/main
git merge-base --is-ancestor origin/main preview/solarsage-v2-human-first-navigator-ux
git diff --check origin/main...preview/solarsage-v2-human-first-navigator-ux
git diff --name-only origin/main...preview/solarsage-v2-human-first-navigator-ux
~~~

#### Merge

~~~bash
git switch main
git pull --ff-only origin main
git merge --no-ff preview/solarsage-v2-human-first-navigator-ux \
  -m "feat(today): ship real personal horizons v2"
~~~

Post-merge before push:

- contracts check;
- typecheck;
- diff check;
- merge tree clean;
- exact merge parent proof.

Then normal push, never force.

### S2.W4 — production deployment

#### 4.1 Runtime audit and backup

Record without secrets:

- accepted main SHA;
- current service PIDs/start timestamps;
- current `.next-prod` location/hash/size;
- current env flag boolean states;
- current shared wheel version/hash;
- disk space;
- nginx config test;
- backup timestamp.

Create:

- root-readable env backup preserving mode/owner;
- atomic frontend rollback dist path;
- rollback SHA document.

#### 4.2 Shared Python contracts

If `packages/py-contracts/**` differs from previous main:

1. build one wheel from accepted main SHA;
2. compute SHA-256;
3. install exact same wheel into:

~~~text
apps/solarsage/venv
apps/api/.venv
~~~

4. `pip check` both;
5. import/version parity proof.

No global Python and no `/opt/astro-project` changes.

#### 4.3 Frontend release build

Build isolated:

~~~text
.next-release-<timestamp>
~~~

Run smoke against build before swap where possible. Do not touch `.next-prod`
until build fully succeeds.

Atomic swap:

~~~text
.next-prod -> rollback path
release dist -> .next-prod
~~~

Never delete rollback before production acceptance.

#### 4.4 Env flags

Only now set exact booleans if missing/false:

~~~text
SOLARSAGE_V2_ENABLED=true
SOLARSAGE_V2_FRONTEND_ENABLED=true
~~~

No duplicate keys, no other env changes, values never dumped. Validate through
application settings import and report booleans only.

#### 4.5 Restart order

Conditional safe order:

1. sidecar — only if shared dependency/runtime changed;
2. API — after sidecar healthy and flags/dependencies ready;
3. frontend — after `.next-prod` atomic swap;
4. nginx is not restarted unless config actually changed (not expected).

For each service:

- exactly one restart;
- wait active/health;
- record old/new PID/start;
- no manual uvicorn/next start;
- on failure stop sequence and rollback.

### S2.W5 — production proof

#### HTTP/service

~~~text
sidecar 18091 health 200
API 8000 health 200
frontend 3002 responds
nginx 80/443 responds
all systemd active
one listener per canonical port
no 8001 API / 18092 mock / 3003 acceptance dependency
~~~

#### Payload

Real authenticated production response:

~~~text
today.v2.1 / 3 / 10
long / medium / fast
timing windows/peaks/states
actions/avoid/likely spheres
provenance cross-references valid
fixture dependency false
~~~

#### Browser

- real Telegram HMAC;
- zero page.route/HAR/mock;
- `data-source=backend-horizons`;
- open all technical disclosures;
- sphere exact target/focus/status;
- mobile/desktop screenshots;
- no error boundary/hydration/console error;
- no fixture/dev auth request in production.

#### Logs/privacy

Inspect bounded service logs for:

- startup errors;
- schema/cache mismatch;
- horizon pipeline failure;
- secrets/raw personal data;
- preview marker leakage.

Do not paste full journals into docs/callback.

## 4. Rollback policy

Rollback triggers:

- service fails active/health;
- production response not current V2;
- frontend contract/render error;
- Telegram HMAC flow fails;
- elevated 5xx/401 unrelated to auth test;
- privacy/security issue;
- cache identity mismatch.

Rollback order:

1. stop further deploy actions;
2. restore previous env backup;
3. restore previous `.next-prod` atomically;
4. restore previous Python wheel only if dependency caused failure;
5. restart affected services in dependency order;
6. verify previous production health;
7. do not rewrite git history or force-push main;
8. document closed reason and exact SHA/artifact paths.

## 5. Final acceptance callback

Must report structural evidence only:

~~~text
feature_sha/origin_feature_sha
main_sha/origin_main_sha
merge commit + parents
wheel path/hash or NOT_REQUIRED
frontend release/rollback dist paths
env flag booleans
service PID/start transitions
full test counts
production payload versions/horizon order
Telegram HMAC E2E result
desktop/mobile screenshot paths
fixture/mock absence
privacy audit
rollback readiness
tracked/index clean
~~~

Final task is not complete until this report is independently verified by the
architect against current runtime state.
