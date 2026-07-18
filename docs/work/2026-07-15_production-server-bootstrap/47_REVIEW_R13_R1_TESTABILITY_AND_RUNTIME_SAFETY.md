# R13 review R1 — blockers, исправления и безопасная тестовая модель

Статус: **R13 не принят**. Commit/push, SSH в production, изменение visibility репозитория и запуск приложения запрещены.

Кодер должен продолжить работу в `tmux astro:0.0` с моделью `cliproxy/gemini-3-flash-agent`. Этот файл — обязательный handoff: сначала прочитать его и `45_TZ_R13_PRIVATE_GITHUB_TRANSPORT_AND_SOURCE_READINESS.md`, затем исправлять текущий diff. Архитектор не принимает обходы проверок через переписывание production-кода в тесте.

## 1. Зафиксированные факты текущего diff

Независимая проверка от 2026-07-15:

- `bash -n` для новых shell-файлов проходит, но это не проверяет runtime-ошибки.
- `scripts/tests/test-prod-github-wrapper.sh` проходит, однако покрытие недостаточное.
- `scripts/tests/test-prod-github-access.sh` падает на ожидаемом владельце `root:root` для wrapper: тест заменяет production-проверки владельца и root-проверку через `sed -i`, поэтому такой тест нельзя считать доказательством.
- `scripts/tests/test-prod-source-readiness-workflow.sh` падает на `set -u`: используется несуществующая переменная `REPO_ROOT_DIR`.
- `scripts/tests/test-prod-deploy-source-loader.sh` не доходит до loader-проверки и принудительно проглатывает exit code (`|| true`); он уже дал ложный путь до `SOLARSAGE_EPHEMERIS_PATH`.
- В `scripts/prod-github-access.sh` `local` находится в top-level ветках `--apply`, `--preflight`, `--check`, то есть при реальном запуске после прохождения предыдущих проверок будет runtime-ошибка `local: can only be used in a function`.
- В `scripts/prod-deploy.sh` остался старый self-check, требующий строку `set -a`. Это противоречит R13 и должен быть удалён, а не удовлетворён комментарием.

## 2. Обязательные исправления production-кода

### 2.1 Структура shell-скрипта

1. Убрать все `local` из top-level. Вынести `apply_action`, `preflight_action`, `check_action` в функции либо использовать обычные top-level переменные. Внутри функций `local` допустим.
2. Оставить `set -euo pipefail`; ошибки `curl`, `git`, `mktemp`, `mv`, `chown`, `cmp` не должны превращаться в успешный результат.
3. До первой мутации выполнить полный validation phase. Нельзя сначала заменить `known_hosts`/`config`, а потом обнаружить конфликт `authorized_keys` или origin. При любой ошибке проверки production-файлы должны остаться byte-identical.
4. На временные файлы поставить traps для `EXIT`, `INT`, `TERM`, `HUP`; после успешного rename trap должен безопасно удалить только уже несуществующий temp. Не оставлять ключи/конфиги в `/tmp`.
5. В начале скрипта установить безопасный `umask 077` (или явно установить режим каждого temp до записи). Никаких секретов и содержимого ключей в stdout/stderr.

### 2.2 Безопасная общая валидация

Сделать одну функцию `validate_installed_state` и вызывать её перед `--preflight` и `--check` (для `--apply` — до первой записи). Она должна проверять:

- `.ssh` — реальный каталог, не symlink, `astro:astro`, `0700`;
- private checkout key — regular, не symlink, `astro:astro`, `0600`, non-passphrase; public key — regular, `astro:astro`, `0644`, ровно одна строка;
- derived public key (`ssh-keygen -y -P ''`) совпадает с `.pub` по типу и base64; сравнение не печатает ключ;
- Actions public key — regular, не symlink, `root:root`, `0644`, ровно одна строка `ssh-ed25519 <base64> [optional canonical comment]`; проверить сам ключ через `ssh-keygen -lf`, а не только regex. Две строки, private-key PEM, options перед ключом, неизвестный тип и мусор должны отвергаться;
- forced wrapper — regular, не symlink, `root:root`, `0755`, и byte-exact `cmp` с `infra/production/solarsage-github-deploy` текущего checkout;
- installed `known_hosts.github` — regular, не symlink, `astro:astro`, `0600`, byte-exact `cmp` с `infra/ssh/github.com.known_hosts`;
- SSH config и authorized_keys — regular, не symlink, `astro:astro`, `0600` (если файл отсутствует до apply, это допустимо только на этапе pre-apply; после apply — ошибка);
- repo checkout и `.git` — real directories, не symlink; `origin` существует и ровно равен `git@github.com-solarsage-prod:basilivanov/solarsage-astro.git`. HTTPS, `github.com` без alias, другой owner/repo, credential URL и отсутствующий origin — fail closed;
- managed SSH block: ровно ноль или ровно один begin/end pair, маркеры не пересекаются, нет unmatched marker, нет `Host github.com-solarsage-prod` вне managed block; содержимое блока должно совпадать с каноническим контрактом. Дубликат или конфликт — ошибка;
- managed authorized key: ровно одна строка с canonical comment `solarsage-github-actions-prod` и exact forced command; тот же key без exact options, тот же comment с другим key, duplicate comment или duplicate key — ошибка. Unrelated lines сохраняются.

Проверки владельца должны использовать `stat` и быть настоящими в production. Нельзя добавлять `TEST_MODE`, доверять пользовательским env-переопределениям путей или ослаблять root/owner checks при обычном запуске.

### 2.3 `--apply`: двухфазная и идемпотентная запись

Фаза A — только чтение: разобрать Actions key, проверить wrapper/template, весь config, authorized_keys, origin и parent directories. Если что-либо не проходит — не менять ни одного production-файла и не менять origin.

Фаза B:

1. Сформировать все новые содержимые файлы в temp-файлах в тех же каталогах (`0600`, затем `chown`), с cleanup traps.
2. Для config и authorized_keys использовать byte-preserving обработку. Нельзя `awk`/`while read`-алгоритмом молча добавлять newline или менять unrelated bytes. Допустим безопасный Python 3.12 helper в режиме binary input/output либо отказ на malformed no-final-newline. Не использовать `sed -i`.
3. Atomic rename только после успешной полной подготовки temp-файлов. Не удалять unrelated authorized keys.
4. Нормализовать origin последним и только после всех предшествующих валидаций; если `git remote set-url` не удался, вернуть ошибку и явно указать, что deployment readiness не подтверждён.
5. Не reload/restart sshd, systemd или приложение.
6. Повторный `--apply` на уже применённом состоянии должен быть byte-idempotent: второй запуск не меняет config/authorized_keys и не создаёт дубликаты.

### 2.4 `--preflight` и `--check`

`--preflight` и `--check` read-only; они не делают fetch, checkout, push, `remote set-url`, запись файлов или restart.

- Перед `ls-remote` проверить exact origin и pinned SSH config.
- Вызвать `timeout 15s git -C /opt/solarsage-astro ls-remote --exit-code origin refs/heads/main`. Обработать timeout/non-zero/empty/multiple lines. Принимать ровно одну строку `<40 lowercase hex>\trefs/heads/main`.
- `--preflight` может вывести предупреждение, если anonymous GitHub API возвращает 200 (repo public), но не называть это production-ready. Не считать 403/5xx/timeout успешной visibility-проверкой; вывести безопасный статус и вернуть ошибку, если readiness невозможно доказать.
- `--check`: anonymous API с body suppressed и bounded timeout: 200 → fail с `repository is public`; 404 + успешный exact `ls-remote` → private proof; 403/5xx/000/прочие → fail. Проверять HTTP status как непустой трёхзначный код, не сравнивать пустую строку арифметически.
- При `--expected-sha` сравнивать exact remote SHA; SHA из вывода не должен приниматься, если refs path не равен `refs/heads/main`.
- `--check` должен передавать только безопасные статусы, SHA, fingerprint и пути; не body API, не key material, не `.env`.
- Для `--preflight`/`--check` допускается только пользователь `astro`; root должен получить понятную ошибку (кроме `--apply`, который root-only). Некорректные args по-прежнему возвращают rc 2 до privilege check.

### 2.5 `prod-deploy.sh`

1. Полностью удалить старый блок grep/self-validation про `set -a`; не оставлять его в комментарии.
2. Перед loader проверить `.env.production`: regular, не symlink, `astro:astro`, mode 0600 или 0640. Loader также должен оставаться regular/non-symlink.
3. Использовать только `source scripts/lib/prod-env-loader.sh` + `prod_env_load`; `.env.production` никогда не source/eval напрямую.
4. В expected-SHA режиме вызвать `prod-github-access.sh --check --expected-sha` до fetch и до любой записи в git config. После check снова проверить exact origin; не делать безусловный `git remote set-url` как способ скрыть неправильный origin.
5. Перед fetch проверять clean worktree; после fetch проверять exact remote SHA; не выводить secret env values.
6. Тестовый harness должен реально остановиться сразу после loader/transport этапа с корректным mock `SOLARSAGE_EPHEMERIS_PATH`; запрещены `|| true` вокруг основного запуска и `sed`-подмена owner/root semantics.

## 3. Требования к тестам без ложного зелёного результата

Тесты могут копировать production script и заменять только абсолютные sandbox paths. Нельзя менять `if id -u`, `stat` assignment, expected owners или validation branches в копии.

Использовать path-aware mocks в `$TEST_DIR/bin`, добавленных в `PATH`:

- `id`: `-u` возвращает `0` только для теста apply, `-un` возвращает `astro`; отдельный negative case запускает non-root сценарий и ожидает отказ;
- `stat`: для каждого sandbox path возвращает реальный mode, а owner map возвращает `astro:astro` для user files и `root:root` для wrapper/Actions key; любые прочие вызовы делегирует `/usr/bin/stat`;
- `chown`: no-op только в sandbox либо записывает marker, не трогая реальные пути;
- `git`: реализует только ожидаемые `remote get-url`, `remote set-url`, `ls-remote` и пишет audit-log вызовов; неожиданный fetch/checkout/push возвращает ошибку;
- `curl`: по `MOCK_CURL_STATUS` возвращает status без сети и записывает URL/flags;
- `ssh-keygen`: для реальных временных ed25519 keys использовать системный бинарник; нельзя подсовывать production key;
- `timeout`: короткий mock/реальный timeout, без внешнего SSH.

### 3.1 Обязательная матрица `test-prod-github-access.sh`

Проверить минимум:

1. invalid args, duplicate actions, missing/uppercase/40+ SHA — rc 2;
2. private/public key mismatch, passphrase key, symlink/FIFO/dir, wrong mode/owner — fail;
3. invalid Actions key (two lines, options, wrong type, invalid base64) — fail;
4. wrapper content mismatch — fail;
5. changed known_hosts template and installed known_hosts — fail; exact official template passes;
6. config: first apply, second apply byte-identical, unrelated bytes preserved, duplicate begin/end/unmatched marker/host conflict — fail;
7. authorized_keys: unrelated lines preserved byte-for-byte, first apply, second apply byte-identical, duplicate exact line, same key unrestricted, same comment with other key — fail;
8. invalid origin leaves all files and git audit unchanged; valid HTTPS/old SSH origin normalizes exactly once;
9. preflight mocked API 200 warning + SSH success, API 403/5xx/timeout failure, ls-remote timeout/non-zero/empty/multiple-line failure;
10. check mocked API 200/404/403/5xx/timeout; only 404 + successful SSH is green; expected SHA match/mismatch;
11. forced failure during temp write/rename leaves original files unchanged and no temp leak;
12. assert no real network/SSH/fetch/checkout/push and no temp directories remain after test.

### 3.2 Wrapper test

Keep path substitution only for two target executable paths. Test empty command, `deploy`/`source-check` valid dispatch, uppercase SHA, short/long SHA, extra spaces/tabs/newline, shell metacharacters, command injection, positional args; every invalid case must return 126 and mocks must show no target invocation.

### 3.3 Workflow test

Исправить `REPO_ROOT_DIR` bug. Test both workflow files from repository root. Static assertions must prove:

- only `workflow_dispatch`, no push/pull_request/schedule/repository_dispatch/workflow_call;
- job `permissions: {}`, production environment, concurrency and timeout ≤10 for readiness;
- private gate appears before SSH configuration and before any SSH command;
- exact `source-check $GITHUB_SHA` / `deploy $GITHUB_SHA` command, strict host-key options, BatchMode, bounded connect settings;
- only existing `PROD_*` secrets are referenced;
- cleanup uses `if: always()` and removes both ephemeral key and known_hosts;
- readiness workflow has no checkout/build/deploy/systemctl/app restart;
- no `echo`/`cat`/`printf` of secret values.

### 3.4 Deploy-loader test

Не патчить owner/mode expressions. Подменить только command binaries and sandbox paths. Mock loader must export a valid `SOLARSAGE_EPHEMERIS_PATH` pointing to an existing sandbox directory. Assert:

- direct `.env.production` `source`/`eval` is absent;
- missing/symlink loader/env fails;
- transport check is called before `git fetch` (audit-log ordering);
- wrong origin is rejected and no `remote set-url` occurs;
- expected SHA mismatch stops before build/install/restart;
- no real `pnpm`, Python venv, DB, systemctl or curl network calls.

## 4. Inventory/fingerprint/runbook

- Add `infra/ssh/github.com.known_hosts` to host inventory and regular-file validation.
- Add R13 production scripts and wrapper to shell syntax checks and runtime fingerprint. Do not put test fixtures or test-only binaries into the applied host fingerprint: changing a test must not force a production host re-apply. Workflows are CI contract files; validate them in the workflow harness, not as installed host files.
- If the implementation adds any runtime file used by `prod-github-access.sh`, include it in both inventory and fingerprint, with an explicit reason in the handoff.
- Ensure `46_REVIEW_R13_OPERATOR_INPUTS.md` exists and lists names/locations only, never values: read-only checkout public key registration, Actions public key installation, GitHub environment secrets, repository-private transition, legacy write-key operator review, and external connectivity blocker.
- Runbook must state that `--apply` is performed only after operator has supplied the Actions public key file, that no key is generated/printed/revoked automatically, and that source-readiness is a separate manual gate before deploy.

## 5. Acceptance gate for R13

Кодер обязан остановиться и передать handoff только после:

```bash
bash -n scripts/prod-github-access.sh \
  infra/production/solarsage-github-deploy \
  scripts/tests/test-prod-github-access.sh \
  scripts/tests/test-prod-github-wrapper.sh \
  scripts/tests/test-prod-source-readiness-workflow.sh \
  scripts/tests/test-prod-deploy-source-loader.sh
scripts/tests/test-prod-github-access.sh
scripts/tests/test-prod-github-wrapper.sh
scripts/tests/test-prod-source-readiness-workflow.sh
scripts/tests/test-prod-deploy-source-loader.sh
scripts/prod-infra-fingerprint.sh
git diff --check
```

Дополнительно повторить полный R12 harness suite, потому что R13 меняет `prod-deploy.sh`, `prod-host-prepare.sh` и fingerprint. Зафиксировать exit codes, порядок mock-вызовов, отсутствие temp leaks и список изменённых файлов. Commit/push не выполнять.
