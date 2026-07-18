# R13 Phase B6 — deploy/source-loader harness and fingerprint/origin hardening

## Scope and ordering

Выполнять после принятия workflow Phase B5. Эта задача закрывает текущий R13 deploy-loader contract без внедрения большого env-profile redesign из `70_TZ...`.

Разрешено менять:

- `scripts/tests/test-prod-deploy-source-loader.sh`;
- `scripts/prod-deploy.sh` только для двух доказанных production defects: strict fingerprint record/file contract и secret-safe origin diagnostic;
- coder handoff/review doc текущего этапа.

Не добавлять production test env overrides/seams (соблюдать `54_REVIEW...`). Production/network/DB/SSH/systemd/deploy, commit и push запрещены.

## 1. Production hardening

### 1.1 Origin diagnostic

Current wrong-origin branch печатает raw `current_origin`. Credential URL, token или hostile multiline origin попадёт в stderr.

Исправить:

- сравнивать exact canonical origin;
- при mismatch выводить generic message без raw value;
- не делать `remote set-url` внутри deploy;
- no fetch/access/build after mismatch;
- no secret/remote canary in stdout/stderr.

### 1.2 Fingerprint exact file/record contract

Deploy-side gate должен соответствовать R9:

- `/etc/solarsage/infra-fingerprint` — existing regular non-symlink readable file;
- owner/mode exact `root:root:644`;
- exact one physical LF-terminated line;
- line exact `^[0-9a-f]{64}$`;
- extra blank line, no-final-LF, CRLF, two lines, spaces, uppercase, short/long fail;
- repository fingerprint command succeeds и сам выдаёт exact one LF line `64 lowercase hex`;
- applied/repository values exact match;
- failures before env loader/install/build/backup/migration/restart;
- diagnostics не выводят fingerprint value.

Не использовать command substitution как единственное record validation: trailing newlines исчезают. Захватывать output в sandbox/private temp либо через строгий reader с проверкой physical bytes. Temps cleanup on all exits/signals.

## 2. Harness architecture

Полностью переписать `test-prod-deploy-source-loader.sh` как isolated fail-closed matrix:

- один `TEST_DIR=/tmp/solarsage-deploy-source-loader-test.XXXXXX`, trap `EXIT INT TERM HUP`;
- свежая baseline copy `prod-deploy.sh` для каждого mutation/case либо byte-exact reset;
- exact path substitution counts before/after;
- никаких real `/tmp/solarsage-deploy.lock`, `/etc/solarsage`, checkout `.env.production`, app root writes;
- child-only `PATH="$MOCK_BIN:<trusted-system-path>"`;
- command mocks reject any unknown argv/path;
- per-case audit append in `%q`/NUL-safe records, compare as written, never sort;
- safe diagnostics: paths/case IDs only, no raw output/audit/env/remote;
- exact case/self-test manifests.

## 3. Fail-closed sandbox substitutions

В копии production script заменить только exact canonical runtime occurrences:

- app root `/opt/solarsage-astro` → sandbox repo;
- lockfile `/tmp/solarsage-deploy.lock` → sandbox lock;
- `.env.production` location follows sandbox app root;
- `scripts/lib/prod-env-loader.sh` → sandbox loader mock;
- `/opt/solarsage-astro/scripts/prod-github-access.sh` → sandbox access mock;
- `scripts/prod-infra-fingerprint.sh` → sandbox fingerprint mock;
- `/etc/solarsage/infra-fingerprint` → sandbox fingerprint file;
- default ephemeris path → guaranteed nonexistent sentinel, чтобы success зависел от loader export;
- controlled stop вставляется ровно один раз после successful ephemeris validation и до install/build anchor.

Pre/post assertions:

- exact source occurrence count expected;
- each replacement exactly once/expected count;
- no executable/mutable canonical path remains;
- early-stop anchor found exactly once, marker inserted exactly once;
- any source formatting drift makes harness fail before cases.

## 4. Exact mocks

### `stat`

Разрешить только sandbox paths and exact formats. Owner/mode override path-specific, not global. Outside sandbox fails, не делегируется real stat.

### `mktemp`

Разрешить только exact shapes, создавать files внутри `$TEST_DIR`, audit call. Пер-case проверять отсутствие `untracked.*`, fingerprint/output temps и иных leftovers до final trap.

### `git`

Разрешить только exact argv, отдельно configurable rc/output:

- `git diff --quiet`;
- `git diff --cached --quiet`;
- diagnostic name-status shapes only if failure case explicitly tests them;
- `git ls-files --others --exclude-standard -z`;
- `git rev-parse HEAD`;
- `git remote get-url origin`;
- `git fetch --prune origin main`;
- `git rev-parse origin/main`;
- `git checkout --detach <exact-target-sha>`;
- `git restore ... next-env.d.ts` только если reachable before controlled stop (обычно нет).

Unknown subcommand/ref/extra arg and every `remote set-url`, push/network shape fail and write safe command marker. HEAD and origin/main outputs/rc configured separately.

### Access mock

Accept only:

```text
--check --expected-sha <same exact SHA>
```

Record exact argv and configurable rc. No network.

### Env loader mock

Скрипт может быть sourced only. `prod_env_load`:

- accepts exact sandbox `.env.production` path and exact domain;
- records safe names/paths, not values;
- exports `SOLARSAGE_EPHEMERIS_PATH` exact configured sandbox directory;
- optionally configured failure/no-export/wrong-path;
- does not export secret canary.

### Fingerprint mock

Accept no args, configurable rc and exact output fixture, audit invocation. Unknown args fail.

### Forbidden mocks

`pnpm`, npm, python venv/pip, alembic, pg tools, backup script boundary if reached, systemctl, sudo, docker, curl, ssh/network commands fail and create safe marker. Harness fails if marker exists.

## 5. CLI/mode matrix

Assert exact rc and no forbidden calls:

### Invalid rc 2 before env/stat/git

- unknown one arg;
- `--expected-sha` missing value;
- nonhex exact 40, short, long, uppercase;
- extra arg;
- duplicate/mixed `--current --expected-sha`;
- three+ args and duplicate flags.

### Valid modes

- no args: accepted legacy git mode; no access call because SHA unpinned, exact fetch/checkout flow;
- `--current`: no origin/access/fetch/checkout, current HEAD path only;
- `--expected-sha <lowercase40>`: pinned access before fetch, exact post-fetch SHA and checkout.

Acceptance of no-arg is current R8 contract, not recommendation for launch. Runbook pinned workflow remains preferred.

## 6. Env and loader file matrix

`.env.production`:

- missing, symlink, directory, FIFO fail;
- mode 600 succeeds;
- mode 640 succeeds;
- 644/777/other fail;
- wrong owner/group fails;
- failure occurs before loader/build.

Loader path:

- missing, symlink, directory, FIFO/non-regular fail;
- valid regular path reaches exact source call;
- static structural scan/mutations reject direct `.env.production` source, dot-source, `eval`, `set -a` bypass or variable-indirect source;
- loader exact args verified.

Здесь не доказывается полный allowlist/process-control safety — это отдельный P0 task `70_TZ...`.

## 7. Source transport/order matrix

Pinned success audit exact order, without sorting:

```text
clean-source-before
origin-get-url
access-check exact SHA
fetch --prune origin main
clean-source-after
rev-parse origin/main
checkout --detach exact SHA
fingerprint command
load-env exact args
ephemeris exact exported path
controlled-stop
```

Test:

- access rc/mismatch failure → no fetch/checkout/fingerprint/loader/build;
- wrong/empty/credential/multiline origin → no access/fetch/set-url and no raw canary output;
- post-fetch origin/main mismatch → fetch allowed, no checkout/fingerprint/loader/build;
- fetch failure → no later stage;
- wrong fetch/checkout/ref argv rejected;
- current mode no transport calls;
- no-arg mode does not falsely claim pinned access proof.

## 8. Fingerprint matrix

- missing, symlink, directory, FIFO, unreadable;
- wrong owner/mode;
- empty, short/long, uppercase, nonhex;
- no-final-LF, CRLF, extra blank line, two lines, spaces;
- repository fingerprint command rc nonzero;
- command empty/malformed/multiline/extra-LF;
- applied/repo mismatch;
- exact valid record reaches loader;
- every failure: no loader/build and no fingerprint bytes in output.

## 9. Ephemeris/export proof

- valid loader export points to existing readable/traversable sandbox directory and reaches controlled stop;
- no export cannot use real `/opt/sweph/ephe` fallback because substituted default is nonexistent;
- wrong path, file instead of dir, non-readable/non-traversable (where test user semantics allow) fail;
- audit proves deploy tested exact exported path;
- remove ephemeris validation mutation must make self-test fail.

## 10. Lock/temp/output safety

- exact lock path substituted; no real `/tmp/solarsage-deploy.lock` touched;
- lock contention case fails before mutation;
- per-case child descriptors release;
- no sandbox temp leftovers after success/failure;
- synthetic origin/env/fingerprint secret canaries absent from stdout/stderr/audit;
- assertion failure never cats raw logs.

Production lockfile redesign/global lock is deferred to maintenance-state task; harness only proves isolation of current contract.

## 11. Mutation self-proof

Sandbox copies must make the same validator/harness red for at least:

- remove access-before-fetch call;
- remove origin gate;
- allow `remote set-url`;
- disable post-fetch SHA comparison;
- accept wrong fetch/ref/checkout argv;
- bypass strict fingerprint one-record check;
- bypass loader export and use default ephemeris;
- delete ephemeris validation;
- break lock path substitution;
- leave temp file;
- print raw credential-origin canary.

Mutation helper requires exact one anchor match; accidental parse/mutation failure is not semantic PASS.

## 12. Verification and handoff

Coder runs after last edit:

```bash
bash -n scripts/prod-deploy.sh scripts/tests/test-prod-deploy-source-loader.sh
timeout 180 bash scripts/tests/test-prod-deploy-source-loader.sh
timeout 180 bash scripts/tests/test-prod-deploy-source-loader.sh
git diff --check
```

No production/real network/DB/SSH/systemd. Report exact manifests/rc and stop. Independent acceptance is only by architect.
