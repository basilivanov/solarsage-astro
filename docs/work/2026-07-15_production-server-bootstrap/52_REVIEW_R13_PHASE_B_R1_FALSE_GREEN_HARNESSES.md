# R13 Phase B R1 — REJECTED: harnesses дают ложный зелёный результат

## Статус

`51_REVIEW_R13_PHASE_B_HANDOFF.md` не принят. Независимый запуск четырёх новых harnesses действительно завершился `rc 0`, но текущие тесты не доказывают обязательный контракт из `50_TZ_R13_PHASE_B_ISOLATED_HARNESSES.md` и пропускают реальные дефекты production-конфигурации.

Независимый результат на текущем состоянии:

- `scripts/tests/test-prod-github-access.sh` — `rc 0`, покрытие неполное;
- `scripts/tests/test-prod-github-wrapper.sh` — `rc 0`, hostile-input проверки частично невалидны;
- `scripts/tests/test-prod-source-readiness-workflow.sh` — `rc 0`, хотя `.github/workflows/source-readiness.yml` не содержит обязательный `BatchMode=yes`;
- `scripts/tests/test-prod-deploy-source-loader.sh` — `rc 0`, основной запуск замаскирован `|| true`.

Phase B остаётся незавершённой. Production apply/deploy, commit и push запрещены.

## 1. Общие обязательные исправления для всех четырёх harnesses

1. Не использовать `eval` для запуска тестируемых команд. Передавать argv массивом или через helper вида `run_case EXPECTED_RC LABEL env NAME=value -- "$SCRIPT" args...`. Данные теста не должны повторно интерпретироваться shell.
2. Не использовать `|| true` на проверяемом запуске. Явно сохранить `rc` через `set +e`, вернуть `set -e`, затем сравнить точный ожидаемый код.
3. Все command mocks сделать fail-closed:
   - поддержать только явно ожидаемые команды и аргументы;
   - любой неизвестный subcommand/shape записать в audit и завершить non-zero;
   - никогда не делегировать неизвестный `git`, `curl`, `ssh`, `systemctl`, `pnpm`, Python/venv, DB-команду или сетевой вызов реальному бинарнику.
4. Разрешённые локальные инструменты (`/usr/bin/stat`, `/usr/bin/ssh-keygen`, `cmp`, `sha256sum`) могут работать только с путями внутри одного `$TEST_DIR`. Перед делегированием нормализовать путь и fail, если он вне sandbox.
5. Каждый negative case должен проверять не только `rc`, но и побочные эффекты:
   - production target mock не вызван;
   - запрещённая команда отсутствует в audit;
   - файлы, которые должны остаться неизменными, сравниваются через `cmp -s` с сохранённой копией либо по `sha256sum`;
   - временные файлы по canonical prefixes отсутствуют;
   - success message отсутствует.
6. Не хранить bytes в command substitution для byte-exact проверки: `value=$(cat file)` удаляет завершающие LF. Использовать `cp` + `cmp -s` либо sha256 файлов.
7. Каждый кейс должен стартовать из известного baseline. Сделать функции `reset_fixture`, `snapshot_state`, `assert_state_unchanged`, `assert_no_temp_files`, `reset_audits`; не позволять предыдущему кейсу менять смысл следующего.
8. `trap` должен очищать sandbox на `EXIT INT TERM HUP`. Не трогать реальные `/home/astro`, `/etc/solarsage`, `/usr/local/sbin`, `/opt/solarsage-astro`, Git index или сеть.
9. Не выводить в test output private keys, public-key base64, токены, `.env` values, API body и malformed remote output. Для диагностики печатать только label, rc и безопасное имя audit event.
10. Новые/существенно переписанные shell/YAML-файлы сохранить с GRACE `AI_HEADER`, `START_MODULE_CONTRACT`, `START_MODULE_MAP`; нетривиальные helper-функции — с function contracts по корневому `AGENTS.md`.

## 2. `test-prod-github-access.sh`: переписать как полноценную contract matrix

### 2.1 Небезопасные/ложнозелёные места текущей версии

- `assert_fail`/`assert_success` используют `eval`.
- Mock `git` после частичной обработки делает `/usr/bin/git "$@"`; неизвестная команда может уйти в реальный git с уже сдвинутыми аргументами.
- Known-hosts fixture вручную продублирован строками вместо byte-exact копирования canonical `infra/ssh/github.com.known_hosts`.
- Idempotence сравнивает command-substitution строки, а не реальные bytes.
- Один `MOCK_STAT_OWNER` одновременно подменяет ownership всех путей и не доказывает path-specific проверки.
- Единственный injected `mv` failure проверяет только существование config, но не его bytes, другие destinations, temp cleanup и фактическую частичную транзакцию.
- Матрица API/`ls-remote`, path types, Actions key, config и `authorized_keys` покрыта лишь фрагментарно.

### 2.2 Fixture и mocks

1. Копировать production script и менять в копии только canonical absolute path constants.
2. Копировать canonical wrapper и canonical known-hosts из текущего checkout через `cp`; не вставлять содержимое шаблонов вручную.
3. Сгенерировать:
   - checkout ed25519 key без passphrase;
   - отдельный checkout ed25519 key с passphrase для negative case;
   - Actions ed25519 key, сохранить только public line и сразу удалить private half.
4. Owner mock сделать path-map, например через case по normalized sandbox path. Отдельный env override должен портить только выбранный путь (`MOCK_BAD_OWNER_PATH`), а не все paths.
5. Mock `git` поддерживает ровно:
   - `git -C <sandbox-repo> remote get-url origin`;
   - `git -C <sandbox-repo> remote set-url origin <exact-alias-url>`;
   - `git -C <sandbox-repo> ls-remote --exit-code origin refs/heads/main`.
   Всё остальное — audit `git.unexpected` и non-zero. `fetch`, `checkout`, `push` имеют отдельные forbidden markers.
6. Mock `curl` не обращается в сеть и возвращает только настраиваемые `rc` и status. Он обязан проверить exact URL, `-o /dev/null`, connect/max timeout и отсутствие output body.
7. Для timeout case либо позволить системному `timeout` завершить специально зависающий mock `git` в коротком test-only окне, либо path-substitute timeout mock с детерминированным `124`. Не ждать production 15 секунд в каждом тесте.

### 2.3 Обязательная матрица, которая должна реально присутствовать в файле

#### CLI

Проверить `rc 2` и отсутствие `stat/curl/git/mv/chown` audit для:

- no args;
- unknown flag;
- две action-команды одновременно;
- `--expected-sha` без значения;
- `--expected-sha` без `--check`;
- duplicate `--expected-sha`;
- SHA short, long, uppercase, non-hex.

#### Path/type/owner/mode

Для каждого relevant path отдельно проверить missing, symlink, directory/FIFO вместо regular file, wrong mode и wrong owner там, где это применимо:

- `.ssh` directory;
- checkout private key;
- checkout public key;
- Actions public key;
- installed wrapper;
- repo known-hosts template;
- existing installed known-hosts/config/authorized_keys;
- repo directory и `.git` directory.

Каждый prevalidation fail обязан происходить до первого mutation audit.

#### Checkout key

- matching no-passphrase private/public pair проходит;
- public mismatch падает;
- passphrase-protected private key падает;
- malformed private/public files падают;
- output scan не содержит PEM, base64 или comments.

#### Actions public key

Проверить отдельными fixtures:

- ровно одна `ssh-ed25519` physical line с одним LF — проходит;
- empty;
- extra blank line;
- CRLF/любой CR;
- две physical lines;
- options prefix перед key type;
- wrong type (`ssh-rsa`/ecdsa);
- invalid base64;
- PEM/private-key material;
- no final LF.

Все invalid cases — `rc 1`, no mutation.

#### Wrapper и known-hosts

- exact copied wrapper/template проходят;
- changed installed wrapper падает;
- changed canonical copied template падает до mutation;
- changed installed known-hosts падает в installed-state check;
- symlink/type/mode/owner cases проверяются отдельно.

#### SSH config

Проверить bytes через `cp` + `cmp`, не shell variables:

- config отсутствует: first apply создаёт exact managed block;
- unrelated bytes до/после блока сохраняются;
- second apply byte-identical для config, authorized_keys и known_hosts;
- duplicate BEGIN;
- duplicate END;
- unmatched BEGIN/END;
- END до BEGIN;
- alias `Host github.com-solarsage-prod` вне managed block;
- conflicting/modified managed block;
- existing non-empty file без final LF.

Все malformed cases — fail до mutation и original byte-identical.

#### `authorized_keys`

- unrelated lines, включая spaces/comments и CR-sensitive bytes, сохраняются byte-for-byte;
- first apply добавляет ровно canonical quoted forced line;
- second apply byte-identical;
- canonical line ровно один раз проходит;
- unquoted command/options variant падает;
- same Actions key unrestricted падает;
- duplicate exact canonical line падает;
- same key в двух разных forms падает;
- тот же canonical comment с другим key падает;
- no-final-LF non-empty file падает без mutation.

Не реконструировать raw lines через shell splitting при assertions.

#### Origin

- expected HTTPS, old GitHub SSH и уже normalized alias forms принимаются и при apply приводятся к exact alias URL;
- normalization происходит не более одного раза;
- wrong owner/repo, credential-bearing URL, unknown host/scheme и missing origin падают до mutation;
- failure cases обязаны иметь ноль `remote set-url` audit.

#### `--preflight` и `--check`

Полная таблица:

- API `200`: preflight `rc 0` только вместе с valid SSH proof, вывод содержит explicit PUBLIC и `not production-ready`; check падает;
- API `404`: preflight/check могут пройти только с exact SSH proof;
- API `403`, `429`, `500`, `503`, invalid status, curl nonzero/timeout — fail;
- `ls-remote`: nonzero, timeout `124`, empty, two lines, wrong ref, spaces вместо TAB, uppercase SHA, short/long SHA — fail;
- exact `<40 lowercase hex><TAB>refs/heads/main` — pass;
- expected SHA match — pass, mismatch — fail.

Для read-only actions audit обязан доказать отсутствие writes, `remote set-url`, fetch, checkout и push.

#### Failure injection и фактическая atomicity

Инъецировать отказ:

- `mktemp` для каждого temp prefix;
- write/helper generation config;
- write/helper generation authorized_keys;
- каждый `mv` destination: known_hosts, config, authorized_keys;
- origin `remote set-url`.

Гарантия текущей реализации — temp+rename атомарны для отдельного файла, но три последовательных `mv` не являются общей all-file транзакцией. Тест и документация не должны утверждать общий rollback, если он не реализован. Для ранних failures originals должны быть byte-identical; для late rename failure зафиксировать фактическое допустимое partial state, но доказать:

- ни один destination не обрезан и является либо old, либо complete new file;
- все оставшиеся temp files удалены;
- success message отсутствует;
- повторный `--apply` из partial state восстанавливает exact canonical installed state.

Если вместо этого реализуется настоящий backup+rollback, тогда тестировать byte-identical rollback после каждого failure point. Не называть sequential moves «общей атомарной транзакцией».

## 3. `test-prod-github-wrapper.sh`: hostile strings должны быть реальными bytes

Текущие строки `"...\n"` и `"...\r"` содержат literal backslash symbols, а не newline/CR. Текущие mocks только печатают stdout и не дают доказать отсутствие target invocation.

Исправить:

1. Target mocks пишут exact argv в audit и возвращают configurable `MOCK_TARGET_RC`.
2. После каждого invalid case audit target должен быть пуст.
3. Использовать реальные bytes, например `$'deploy <sha>\n'`, `$'deploy <sha>\r'`, `$'deploy\t<sha>'`.
4. Матрица invalid commands для обоих verbs:
   - empty command;
   - positional args wrapper itself;
   - uppercase/short/long/non-hex SHA;
   - leading/trailing/double spaces;
   - tab;
   - actual LF и CR;
   - semicolon;
   - literal `$()` payload;
   - backticks;
   - pipe;
   - `&&`;
   - arbitrary command;
   - missing SHA и extra arg.
5. Valid cases должны доказать exact target и argv:
   - deploy target получает `--expected-sha <sha>`;
   - access target получает `--check --expected-sha <sha>`.
6. Target `rc 1`, `rc 42`, `rc 126` должны возвращаться wrapper без преобразования в успех.

## 4. `test-prod-source-readiness-workflow.sh`: presence-only grep заменить на structural/order assertions

Текущий файл проверяет только несколько подстрок и поэтому проходит при лишних triggers, неправильном порядке, отсутствующих SSH options и deploy/build steps.

Обязательные изменения:

1. Определять `REPO_ROOT` относительно расположения test script, не hardcode `/opt/solarsage-astro` и не использовать несуществующий `REPO_ROOT_DIR`.
2. Проверить не только наличие `workflow_dispatch`, но и отсутствие `push`, `pull_request`, `schedule`, `repository_dispatch`, `workflow_call` в `on` contract. Комментарии/GRACE metadata не должны создавать false positive.
3. Проверить exact concurrency, `cancel-in-progress: false`, `environment: production`, `permissions: {}`, readiness timeout `<= 10`.
4. Вычислить line/order positions и доказать для обоих workflows:
   - private repository gate раньше Configure SSH;
   - private gate раньше первого `ssh -T`;
   - cleanup после SSH и имеет `if: always()`.
5. Собрать все `${{ secrets.NAME }}` references и сравнить set exact с четырьмя разрешёнными именами: `PROD_HOST`, `PROD_USER`, `PROD_SSH_PRIVATE_KEY`, `PROD_KNOWN_HOSTS`. Никаких дополнительных secrets.
6. Для обоих SSH calls проверить `-T`, `-i`, `IdentitiesOnly=yes`, `BatchMode=yes`, `UserKnownHostsFile`, `StrictHostKeyChecking=yes`, `ConnectTimeout` и bounded keepalive.
7. Проверить exact quoted remote command без дополнительных shell fragments:
   - readiness: `source-check $GITHUB_SHA`;
   - deploy: `deploy $GITHUB_SHA`.
8. Cleanup обязан удалять оба ephemeral файла: private key и known_hosts.
9. Readiness workflow не должен содержать checkout, build, pnpm/npm, deploy invocation, systemctl, Docker/app restart, migrations.
10. Secret-safety assertion должна запрещать вывод secret value в stdout/log. Разрешён только controlled `printf` с redirect в ephemeral file; нельзя запрещать слово `printf` глобальным grep, но нужно доказать, что destination — key/known_hosts file и команда не пишет secret в stdout.
11. `.github/workflows/source-readiness.yml` сейчас реально не содержит `BatchMode=yes`. Добавить option в production workflow и сделать тест, который до этого изменения падает.
12. Новый `source-readiness.yml` дополнить GRACE module header/contract/map по `AGENTS.md`; его contract должен явно фиксировать manual-only, private gate, no deploy, strict SSH и cleanup.

## 5. `test-prod-deploy-source-loader.sh`: создать настоящую последовательностную проверку

Текущая версия неприемлема по следующим причинам:

- основной запуск заканчивается `|| true`;
- mock `git` возвращает `0` для любой неизвестной команды;
- нет audit order, поэтому не доказано, что transport check происходит перед fetch;
- stat mock всегда возвращает `600` и не доказывает path-specific type/mode/owner failures;
- не проверяются wrong origin, access failure, SHA mismatch, missing/symlink env/loader;
- не доказано отсутствие real build/DB/systemctl/network calls.

Переписать так:

1. Копировать `prod-deploy.sh`; path-substitute только canonical repo/env-loader/access/fingerprint paths. Controlled early stop допустим только непосредственно после проверяемой loader/source stage и до dependency/build stage.
2. Все mocks пишут monotonic audit lines, например:
   - `01 access --check --expected-sha ...`;
   - `02 git remote get-url origin`;
   - `03 git fetch ...`.
   Не подставлять номера вручную: helper увеличивает counter либо assertions сравнивают реальные line numbers в одном audit.
3. Unknown git/tool call — non-zero. Создать forbidden mocks для `pnpm`, `npm`, `python3.12`/venv, `alembic`, `pg_isready`, `systemctl`, `sudo`, `docker`, `curl`, `ssh`; любой вызов до controlled stop должен валить тест.
4. Запускать без `|| true`, сохранять exact rc.
5. Проверить:
   - invalid/no-value/duplicate/bad SHA args → `rc 2`;
   - env missing, symlink, directory/FIFO, wrong mode, wrong owner → fail;
   - loader missing, symlink, non-regular → fail;
   - static scan production script: нет direct `. "$ENV_FILE"`, `source .env.production`, `eval` или `set -a` loading;
   - access transport audit обязательно раньше fetch;
   - access nonzero → no fetch/build/restart;
   - wrong origin → fail и no `remote set-url`;
   - expected SHA mismatch → fail before fetch/build;
   - valid loader exports sandbox `SOLARSAGE_EPHEMERIS_PATH`, script достигает controlled stop с `rc 0`;
   - test не читает и не печатает secret values.
6. Для assertions проверять exact command shapes, а не только marker substring.

## 6. Production-файл, который обязан измениться вместе с тестом

`.github/workflows/source-readiness.yml`:

- добавить `-o BatchMode=yes` в SSH invocation;
- добавить GRACE header/module contract/module map;
- не добавлять автоматические triggers, checkout/build/deploy/restart steps;
- не менять production auth/API/app runtime.

Иные production-файлы менять только если новый корректный harness действительно воспроизводит дефект контракта. Тогда сначала зафиксировать failing case, затем минимальный fix, затем green.

## 7. Новый handoff и acceptance evidence

После исправлений заменить содержимое `51_REVIEW_R13_PHASE_B_HANDOFF.md`; текущие заявления удалить как недоказанные.

Handoff должен содержать:

1. Exact список изменённых файлов.
2. `bash -n` с exact command и `rc`.
3. Для каждого из четырёх harnesses:
   - exact command;
   - `rc`;
   - число выполненных cases;
   - доказательство forbidden-call audit = empty;
   - temp cleanup result.
4. Full R12 suite: exact список, command и отдельный rc каждого файла; не писать только «все прошли».
5. `git diff --check` rc.
6. `scripts/prod-infra-fingerprint.sh` output на repository state на момент handoff. Называть это **repository fingerprint**, а не «current applied fingerprint», пока live `/etc/solarsage/infra-fingerprint` не сравнивался.
7. Явно указать: production apply/deploy, commit и push не выполнялись.

## 8. Граница задачи

Не трогать и не stage:

- `.grace/`;
- `artifacts/design/`;
- `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`;
- `grace.db`;
- `skills/`.

Не запускать production app, real SSH/GitHub API/fetch/checkout/push, systemctl mutation или deployment. После реализации остановиться на handoff и ждать архитектурного review.
