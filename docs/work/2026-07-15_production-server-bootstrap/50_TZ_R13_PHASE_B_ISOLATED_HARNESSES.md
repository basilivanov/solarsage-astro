# R13 Phase B — isolated harnesses без production bypass

Реализовать только тестовый слой из `45_TZ...` и `47_REVIEW...` после принятия Phase A. Production не запускать, реальные SSH/HTTP/GitHub/network/fetch/checkout/push не выполнять, commit/push не делать.

## 0. Небольшой production hardening перед тестами

В `scripts/prod-github-access.sh` заменить `for field in $line` на безопасный array parser (`read -r -a fields` или эквивалент без pathname expansion). Raw line для exact forced-command comparison не нормализовать. Это необходимо, чтобы hostile authorized_keys comment не мог влиять на glob expansion.

## 1. Общие правила harnesses

Каждый harness:

- создаёт один `TEST_DIR=$(mktemp -d /tmp/solarsage-r13-...XXXXXX)` и `trap` cleanup на `EXIT INT TERM HUP`;
- не пишет в `/home/astro`, `/etc/solarsage`, `/usr/local/sbin`, `/opt/solarsage-astro`, Git index или реальные SSH files;
- не меняет production script semantics. Допустима только замена canonical absolute paths на sandbox paths в копии тестируемого скрипта;
- запрещено `sed -i`, которое заменяет `id -u`, `stat` owner assignment, expected owners, root checks, validation branches, `if false`, `exit 0` до проверяемого этапа;
- все command mocks лежат в `$TEST_DIR/bin`, PATH передаётся только дочернему процессу;
- каждый mock пишет безопасный audit log (имя команды, subcommand, не секретные args). Unexpected network/fetch/checkout/push/systemctl/pnpm/python-venv возвращает non-zero;
- после каждого теста проверяются: отсутствие temp files, отсутствие внешних вызовов, исходные config/authorized_keys/known_hosts byte-identical при ожидаемом fail;
- не выводит private key, `.env.production`, token, API body или secret env values.

### 1.1 Path-aware mocks

Обязательные моки:

- `id`: configurable `MOCK_UID`/`MOCK_USER`; `-u` и `-un` возвращают только безопасные числовые/username значения;
- `stat`: для sandbox paths возвращает реальный mode через `/usr/bin/stat`, а owner map: user files `astro:astro`, wrapper/Actions pub `root:root`; прочие вызовы делегирует `/usr/bin/stat`;
- `chown`: no-op только для sandbox paths и пишет audit marker; попытка real path — fail;
- `mv`: real move внутри sandbox; `MOCK_MV_FAIL_ON` позволяет намеренно отказать на конкретной sandbox destination;
- `git`: поддерживает только нужные `remote get-url`, `remote set-url`, `ls-remote`; configurable origin/remote output/rc; `fetch`, `checkout`, `push` всегда fail и пишут marker;
- `curl`: никогда не выходит в сеть; `MOCK_CURL_RC`, `MOCK_CURL_STATUS` задают результат, body не создаётся;
- `timeout`: можно использовать системный `timeout` вокруг mock `git`, либо mock должен сохранять timeout semantics;
- `systemctl`, `pnpm`, `python3.12` venv calls, `pg_isready`, `sudo`: в deploy harness unexpected calls fail.

Для apply root-only сценария мок `id -u` возвращает 0; это не меняет production script. Отдельный negative case возвращает non-zero user и проверяет rc 1 до mutation.

## 2. `scripts/tests/test-prod-github-access.sh`

### 2.1 Fixture setup

В sandbox создать:

- `.ssh` mode 0700;
- реальную временную checkout ed25519 key без passphrase и её `.pub` mode 0600/0644;
- реальную временную Actions ed25519 key и public line mode 0644; private Actions key удалить сразу после генерации и не использовать далее;
- copied wrapper template и copied known_hosts template из репозитория;
- fake repo directory + fake `.git` directory; git mock owns origin state;
- copied production access script с path-only substitutions.

### 2.2 Contract matrix

Проверить и явно assert rc:

1. `--invalid`, no args, duplicate actions, missing SHA, uppercase/short/long SHA, SHA without `--check`, duplicate `--expected-sha` → rc 2, no stat/curl/git calls.
2. Non-root `--apply` → rc 1, no file mutation.
3. Missing/symlink/FIFO/directory/wrong mode/wrong owner for `.ssh`, checkout keys, Actions pub, wrapper, template → rc 1.
4. Checkout private/public mismatch and passphrase private key → rc 1; stdout/stderr do not contain key material.
5. Actions pub: valid one LF line passes; extra blank line, CRLF, two lines, options prefix, wrong key type, invalid base64, PEM/private material fail.
6. Wrapper content mismatch and changed known_hosts template fail before any mutation.
7. Config cases: absent first apply; existing unrelated bytes preserved; managed block inserted; second apply is byte-identical; duplicate begin/end/unmatched markers/host alias outside block/conflicting block fail without mutation. Existing non-empty file without final LF fails without mutation.
8. Authorized keys: unrelated lines with comments and CR-sensitive bytes preserved; first apply; second apply byte-identical; canonical quoted forced line passes; unquoted line, same key unrestricted, duplicate same key, duplicate canonical line, same canonical comment with another key fail. Existing non-empty file without final LF fails without mutation.
9. Origin: expected HTTPS/old SSH/alias forms normalize once; unknown owner/repo, credential URL, missing origin fail before first mutation. Git audit verifies no `remote set-url` on fail.
10. `--preflight`: mocked API 200 produces explicit PUBLIC warning and non-ready wording but only succeeds if SSH proof succeeds; API 404 + SSH success succeeds; API 403/429/5xx/invalid/timeout fails; ls-remote timeout/nonzero/empty/multiple/wrong-ref/uppercase SHA fails; valid exact ref succeeds. No write/fetch/checkout/push.
11. `--check`: only API 404 + exact SSH proof succeeds; API 200/403/429/5xx/timeout fails; expected SHA match succeeds and mismatch fails.
12. Atomic preparation: inject `mktemp`/write/`mv` failure at each stage; assert non-zero, no success message, temps cleaned. If implementation guarantees rollback, assert originals byte-identical; otherwise contract must say partial rename is possible and runbook must not promise all-file atomicity.
13. Output scan: reject output containing private key PEM, public key base64, Actions key comment, API body fixture, `.env` values or raw malformed remote output.

Do not call real `curl`, real `git` network, `ssh`, `ssh-add`, `systemctl`, or GitHub API.

## 3. `scripts/tests/test-prod-github-wrapper.sh`

Path-substitute only the two target script paths. Mock targets append invocation to an audit file. Test:

- empty command and positional args → rc 126, no target call;
- valid `deploy <40 lowercase hex>` and `source-check <40 lowercase hex>` exact args;
- uppercase/short/long SHA, extra spaces, tabs, newline, CR, semicolon, `$(...)`, backticks, pipe, `&&`, arbitrary command → rc 126, no target call;
- target non-zero status is propagated, not converted to success.

## 4. `scripts/tests/test-prod-source-readiness-workflow.sh`

Use repository-root-relative paths (`REPO_ROOT`, never unbound `REPO_ROOT_DIR`). Do not execute Actions or SSH. Static contract assertions must prove:

- only `workflow_dispatch`; no push/pull_request/schedule/repository_dispatch/workflow_call;
- readiness timeout <=10, environment production, `permissions: {}`, concurrency exact;
- private gate occurs before Configure SSH and before any SSH command;
- only `PROD_HOST`, `PROD_USER`, `PROD_SSH_PRIVATE_KEY`, `PROD_KNOWN_HOSTS` references;
- key files are ephemeral, strict modes, strict known_hosts, `BatchMode`, `IdentitiesOnly`, `ConnectTimeout`, `StrictHostKeyChecking`;
- exact `source-check $GITHUB_SHA` / deploy workflow exact `deploy $GITHUB_SHA`;
- cleanup has `if: always()` and removes both key and known_hosts;
- readiness has no checkout/build/deploy/systemctl/app restart and no secret echo/cat/printf;
- deploy private gate precedes Configure SSH.

## 5. `scripts/tests/test-prod-deploy-source-loader.sh`

Copy `prod-deploy.sh` and replace only canonical absolute paths. Do not patch owner/mode/root checks. Use mocks and a controlled early stop only after the exact stage under test; never insert bypass before that stage.

Assert:

- invalid args rc 2;
- env file missing/symlink/wrong mode/owner fails;
- loader missing/symlink fails; direct `.env.production` source/eval is absent by static scan;
- transport check audit entry precedes `git fetch`; transport failure means no fetch/build/restart;
- wrong origin fails and no `remote set-url` occurs;
- expected SHA mismatch fails before fetch/build;
- loader exports a valid sandbox `SOLARSAGE_EPHEMERIS_PATH`, and the script reaches the controlled stop without reading secret values;
- no real pnpm, Python venv, DB, systemctl, sudo or network calls.

## 6. Acceptance and handoff

After implementation run all four harnesses independently, then full R12 suite. Record rc, audit ordering, temp cleanup, and changed files in `docs/work/2026-07-15_production-server-bootstrap/51_REVIEW_R13_PHASE_B_HANDOFF.md`. Do not commit/push and do not run production apply/deploy.
