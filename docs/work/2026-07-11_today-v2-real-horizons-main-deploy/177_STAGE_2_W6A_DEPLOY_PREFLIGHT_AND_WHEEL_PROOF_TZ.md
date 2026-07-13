# Stage 2.W6A — production deploy preflight and isolated shared-wheel proof

Дата: `2026-07-13`

Accepted main:
`24b453e95bd244e9628cd66a74caee24b9d70e8c`.

Accepted merge:
`57230b7b8eedb772a936726f6abf97427bc37f6a`.

Parent master:
`127_STAGE_2_CORRECTIVE_RELEASE_MAIN_DEPLOY_WAVE_MASTER.md`.

Статус: **AUTHORIZED READ-ONLY/TEMP PREFLIGHT — NO VENV/ENV/BUILD/SERVICE MUTATION**

Работай лично в `tmux astro:0.0`, без subagents/delegation/background coding.

## 1. Goal

Before any production mutation, prove the exact accepted `main` can be deployed
with the current canonical systemd topology and define a closed rollback plan.

This wave must:

1. audit refs, units, canonical ports, database, env structure, ownership and
   disk without printing secrets;
2. prove non-interactive sudo and nginx configuration readiness;
3. inventory the current editable shared-contract installs in both venvs;
4. build one test wheel from an exact `git archive HEAD` copy under `/tmp`,
   validate its contents/imports/hash and prove both venvs can accept it through
   `pip --dry-run`;
5. prove the production frontend dist and future candidate/rollback paths share
   one filesystem and have sufficient space;
6. produce exact W6B inputs and rollback commands.

No repository, venv, env, build or service state may change.

## 2. Absolute restrictions

- no tracked/untracked repo edit by coder;
- do not edit document 177;
- no git add/commit/push/switch/merge/rebase/pull/stash;
- no dependency install/uninstall, including editable/wheel install;
- no `pnpm install`;
- no `.env` or `.env.production` backup/edit yet;
- no frontend build/candidate/swap;
- no service restart/reload/stop;
- no systemd/nginx/Docker/DB mutation;
- no manual uvicorn/Next server;
- no port 3003/3010/8001/18092;
- no raw env value, bot token, DB URL, cookie, initData, profile or personal
  payload output;
- no broad cleanup of frozen/ignored paths.

Allowed writes are only unique `/tmp/stage2-w6a-*` directories/logs created by
this proof and deleted before callback.

## 3. Entry gate

Run:

```bash
git fetch origin --prune
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git ls-remote --heads origin refs/heads/main
git rev-parse HEAD^1
git log -1 --format=%s
git diff --quiet
git diff --cached --quiet
git diff --check
git status --short --branch
id -un
```

Require:

```text
branch/local/origin/remote main  main / 24b453e95bd244e9628cd66a74caee24b9d70e8c
parent                           57230b7b8eedb772a936726f6abf97427bc37f6a
subject                          docs(release): accept v2 main integration
tracked worktree/index           clean / empty
untracked                        frozen five + doc 177
user                             astro
```

Stop if remote main moved.

## 4. Canonical runtime and database audit

Record:

```bash
systemctl cat \
  solarsage-sidecar.service \
  solarsage-api.service \
  solarsage-frontend.service --no-pager

systemctl show \
  solarsage-sidecar.service \
  solarsage-api.service \
  solarsage-frontend.service \
  nginx.service \
  --property=Id,ActiveState,SubState,MainPID,ExecMainStartTimestamp,User,Group,WorkingDirectory,ExecStart --no-pager

ss -ltnp 'sport = :3002 or sport = :3003 or sport = :3010 or sport = :5433 or sport = :8000 or sport = :8001 or sport = :18091 or sport = :18092'

curl -fsS --max-time 5 -o /dev/null -w 'frontend=%{http_code}\n' http://127.0.0.1:3002/
curl -fsS --max-time 5 -o /dev/null -w 'api=%{http_code}\n' http://127.0.0.1:8000/api/health
curl -fsS --max-time 5 -o /dev/null -w 'sidecar=%{http_code}\n' http://127.0.0.1:18091/v1/health

docker inspect -f '{{.Name}} {{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' solarsage-db
pg_isready -h 127.0.0.1 -p 5433
```

Require exact existing service witnesses:

```text
sidecar   3582982 / Sun 2026-07-12 22:02:52 MSK / astro:astro / 18091
API       3940721 / Mon 2026-07-13 06:54:31 MSK / astro:astro / 8000
frontend  916433  / Thu 2026-07-09 11:30:03 MSK / astro / 3002
nginx     1048    / Wed 2026-07-01 15:36:15 MSK
DB        solarsage-db running / 5433 accepting connections
```

Required absent: 3003/3010/8001/18092.

Confirm unit contract:

```text
sidecar ExecStart  apps/solarsage/venv/bin/uvicorn ... --port 18091
API EnvironmentFile /opt/solarsage-astro/.env
API ExecStart      apps/api/.venv/bin/uvicorn ... --port 8000
frontend NODE_ENV  production
frontend PORT      3002
frontend ExecStart /usr/bin/npm run start
```

Do not change units or daemon-reload.

## 5. Sudo/nginx and filesystem proof

Run:

```bash
sudo -n true
sudo -n nginx -t
stat -c '%n %d %s %a %U:%G' \
  /opt/solarsage-astro \
  .next-prod \
  .next-prod/BUILD_ID \
  .env .env.production
du -sk .next-prod .next-v2-real-preview 2>/dev/null || true
df -Pk .
```

Require sudo noninteractive PASS and nginx syntax PASS. Existing unrelated
nginx protocol-option warnings are recorded but are not changed in this release.

Require repository, `.next-prod` and future sibling release/rollback dirs are
on the same device. Available space must exceed four times current `.next-prod`
size and one GiB; record exact KiB.

Current accepted ownership/modes:

```text
.env              664 astro:astro
.env.production   664 astro:astro
.next-prod        775 astro:astro
.next-prod/BUILD_ID 664 astro:astro
```

## 6. Safe env structure and settings proof

Using a parser that prints only line number, key name, occurrence count and
closed boolean state, inspect:

```text
.env
.env.production
```

Keys:

```text
APP_ENV
DEV_MODE
SOLARSAGE_V2_ENABLED
SOLARSAGE_V2_FRONTEND_ENABLED
SOLARSAGE_V2_DUAL_RUN
```

Never print raw values. Require:

```text
.env SOLARSAGE_V2_ENABLED           UNSET / zero occurrences
.env SOLARSAGE_V2_FRONTEND_ENABLED  UNSET / zero occurrences
.env SOLARSAGE_V2_DUAL_RUN          UNSET / zero occurrences
.env.production same three          UNSET / zero occurrences
```

Architectural decision for W6B:

- edit only canonical `.env`, because only API systemd consumes it;
- leave `.env.production` byte-identical;
- add exactly one occurrence each of `SOLARSAGE_V2_ENABLED=true` and
  `SOLARSAGE_V2_FRONTEND_ENABLED=true` through `apply_patch`;
- default dual-run state is not changed;
- validate via `app.core.config.Settings` and print booleans only.

Prove the application parser accepts the intended override without editing a
file:

```bash
cd apps/api
SOLARSAGE_V2_ENABLED=true \
SOLARSAGE_V2_FRONTEND_ENABLED=true \
./.venv/bin/python - <<'PY'
from app.core.config import Settings
s = Settings()
print('v2_enabled', s.solarsage_v2_enabled)
print('v2_frontend_enabled', s.solarsage_v2_frontend_enabled)
PY
cd /opt/solarsage-astro
```

Require both `True`, with no other settings output.

## 7. Dependency-change and current install inventory

Run:

```bash
git diff --name-only c9bc36bd9a947566eddb1ffcf5617967c7412676..HEAD -- \
  packages/py-contracts \
  apps/api/pyproject.toml \
  apps/solarsage/pyproject.toml \
  package.json pnpm-lock.yaml

apps/api/.venv/bin/python -m pip show solarsage-contracts
apps/solarsage/venv/bin/python -m pip show solarsage-contracts
apps/api/.venv/bin/python -m pip freeze | rg '^(-e .*#egg=solarsage-contracts|solarsage-contracts)'
apps/solarsage/venv/bin/python -m pip freeze | rg '^(-e .*#egg=solarsage-contracts|solarsage-contracts)'
```

Require dependency/runtime manifests changed and both current installs are
version `0.1.0` editable from:

```text
/opt/solarsage-astro/packages/py-contracts
```

Do not uninstall them in W6A. Record this exact rollback command for W6B only
if wheel installation itself causes a deploy failure:

```bash
apps/api/.venv/bin/python -m pip install --no-deps --force-reinstall -e /opt/solarsage-astro/packages/py-contracts
apps/solarsage/venv/bin/python -m pip install --no-deps --force-reinstall -e /opt/solarsage-astro/packages/py-contracts
```

The normal feature rollback remains flags false plus old frontend dist; new
code is fail-closed when flags are disabled.

## 8. Isolated wheel build proof from exact Git tree

Do not build in the repository source directory. Use unique temp roots:

```bash
SRC_ROOT=$(mktemp -d /tmp/stage2-w6a-src.XXXXXX)
WHEEL_DIR=$(mktemp -d /tmp/stage2-w6a-wheel.XXXXXX)
TARGET_DIR=$(mktemp -d /tmp/stage2-w6a-target.XXXXXX)

git archive HEAD packages/py-contracts | tar -x -C "$SRC_ROOT"

apps/solarsage/venv/bin/python -m pip wheel \
  --no-deps \
  --no-build-isolation \
  --wheel-dir "$WHEEL_DIR" \
  "$SRC_ROOT/packages/py-contracts"
```

Use sidecar venv only as the build tool because it already owns setuptools
`82.0.1`; do not install `build`/setuptools into API venv.

Require exactly one wheel:

```text
solarsage_contracts-0.1.0-py3-none-any.whl
```

Record SHA-256 and size. Inspect ZIP names and METADATA without extraction to
repo. Require package modules, `py.typed`, version `0.1.0`, dependency
`pydantic>=2.9,<3`, no tests, no `.pyc`, no secrets.

Install only into the temp target:

```bash
apps/api/.venv/bin/python -m pip install \
  --no-deps \
  --target "$TARGET_DIR" \
  "$WHEEL_DIR"/*.whl
```

Then import with `PYTHONPATH="$TARGET_DIR"` using API Python. Require:

- module path resolves inside TARGET_DIR, not repository editable source;
- package metadata version `0.1.0`;
- activation/versions public imports succeed;
- existing 44 py-contract tests still pass against repository source.

Dry-run exact future install in both venvs:

```bash
apps/api/.venv/bin/python -m pip install \
  --dry-run --no-deps --force-reinstall "$WHEEL_DIR"/*.whl
apps/solarsage/venv/bin/python -m pip install \
  --dry-run --no-deps --force-reinstall "$WHEEL_DIR"/*.whl
```

Require both propose only `solarsage-contracts-0.1.0`; no dependency change.

Delete only the three temp roots after recording safe evidence. Prove they are
absent and repository status unchanged.

## 9. Closed W6B artifact and rollback plan

Produce safe callback values for the future deploy:

```text
ACCEPTED_MAIN_SHA  24b453e95bd244e9628cd66a74caee24b9d70e8c
MERGE_SHA          57230b7b8eedb772a936726f6abf97427bc37f6a
STAMP              generated once in W6B UTC
WHEEL_DIR          /opt/solarsage-astro/.release/wheels/<STAMP>
RC_DIST            .next-release-<STAMP>
ROLLBACK_DIST      .next-prod.rollback-<old-BUILD_ID-prefix>-<STAMP>
ENV_BACKUP         .env.rollback-<STAMP>
```

W6B must create `.release/wheels/<STAMP>` with mode `700` owned `astro:astro`,
build one exact wheel there from `git archive HEAD`, record hash, and keep it
through production acceptance.

W6B env backup must be root-owned mode `600`; original `.env` remains
`astro:astro 664` after scoped patch.

Closed rollback commands:

1. stop only frontend if build swap has happened;
2. preserve failed `.next-prod` as `.next-prod.failed-<STAMP>`;
3. rename rollback dist back to `.next-prod` on same filesystem;
4. restore `.env` from root-owned backup with original `astro:astro 664`;
5. reinstall editable contracts only if wheel install is the failure source;
6. restart sidecar, API, frontend in dependency order;
7. verify previous health and flags false/unset;
8. never reset/force-push published main.

No rollback action is executed in W6A.

## 10. Final integrity

Require at callback:

```text
main local/origin/remote       24b453e... equal
tracked worktree/index         clean / empty
untracked                      frozen five + doc 177 only
temporary W6A dirs             absent
API/sidecar installs           still editable and unchanged
.env/.env.production           byte/mode/owner unchanged
.next-prod/BUILD_ID            unchanged
services/PIDs/listeners        unchanged
3003/3010/8001/18092           absent
commit/push/deploy             not performed
```

## 11. Callback and stop

```text
READY_STAGE_2_W6A_DEPLOY_PREFLIGHT_REVIEW
main_sha: 24b453e95bd244e9628cd66a74caee24b9d70e8c
merge_sha: 57230b7b8eedb772a936726f6abf97427bc37f6a
runtime_units: CANONICAL_CONFIRMED
database: RUNNING_ACCEPTING_5433
sudo_noninteractive: PASS
nginx_test: PASS_WITH_KNOWN_UNRELATED_WARNINGS
same_filesystem: PASS
disk_available_kib: <exact>
env_flags_before: ENABLED_UNSET_FRONTEND_UNSET_DUAL_UNSET
env_edit_target: DOT_ENV_ONLY
settings_override_parse: TRUE_TRUE
current_contract_installs: API_EDITABLE_SIDECAR_EDITABLE_0_1_0
wheel_build_tool: SIDECAR_VENV_PIP_NO_BUILD_ISOLATION
wheel_name: solarsage_contracts-0.1.0-py3-none-any.whl
wheel_sha256: <sha256>
wheel_size: <bytes>
wheel_contents_metadata: PASS
wheel_temp_import: PASS_FROM_TARGET
wheel_install_dry_run: API_PASS_SIDECAR_PASS
temp_artifacts: REMOVED
tracked_worktree: CLEAN
index: EMPTY
frozen_untracked: PRESERVED
env_build_runtime: UNCHANGED
ports: 3003_3010_8001_18092_ABSENT
production_deploy: NOT_STARTED
```

Then stop for architect review. Do not start W6B.
