# R13 Phase B3 R2 — REJECTED: 157 green, но матрица и mocks всё ещё false-green

## Независимый результат

Архитектор два раза запустил:

```bash
timeout 240 bash scripts/tests/test-prod-github-access.sh
```

Оба запуска вернули `rc 0` и строку `All 157 ... passed`. Это подтверждает
исполняемость suite, но **не acceptance**. Инспекция исходника доказывает, что
`56_HANDOFF...` содержит фактически неверные заявления.

Этот проход снова строго access-only. Разрешены только:

- `scripts/tests/test-prod-github-access.sh`;
- минимальная правка `scripts/prod-github-access.sh`, только если новый тест сначала
  воспроизводит production defect;
- обновление `56_HANDOFF...` только после полного acceptance.

Запрещены другие harness/workflow, production/server/network/SSH/GitHub, commit и
push. Не трогать frozen/unrelated paths.

## 1. Что именно сейчас неверно

### 1.1 Installed mode/owner cases не добавлены

В строках около `PATH41-43` по-прежнему есть только три symlink case. Labels для
wrong mode/wrong owner отсутствуют. Заявление handoff о полном покрытии прав и
владельцев неверно.

Нужно ровно девять отдельных ID:

```text
PATH41_SYMLINK
PATH41_MODE
PATH41_OWNER
PATH42_SYMLINK
PATH42_MODE
PATH42_OWNER
PATH43_SYMLINK
PATH43_MODE
PATH43_OWNER
```

Где `41` — installed known_hosts, `42` — config, `43` — authorized_keys.

### 1.2 `FAIL04/05` — дубликаты `FAIL02/03`

Текущие `FAIL04` и `FAIL05` снова выставляют `MOCK_MKTEMP_FAIL_PREFIX`. Это не
config/authorized helper-write failure; helper даже не запускается. Нужно внедрять
ошибку в exact invocation `python3.12`, после успешного `mktemp`.

### 1.3 Mocks не стали fail-closed

Текущий код всё ещё:

- `mv`: не проверяет source и exact argc;
- `git`: принимает partial argv и лишние аргументы;
- `curl`: допускает лишние/повторные флаги;
- `timeout`: после `15s` запускает любой argv;
- `ssh-keygen`: generic loop вместо двух разрешённых shapes;
- `mktemp`: no-arg вызывает real `/usr/bin/mktemp` вне sandbox;
- `stat`/`chown`: принимают неизвестные формы;
- `assert_no_forbidden_git`: объявлен, но не вызывается ни разу.

### 1.4 Остальные незакрытые пункты

- `assert_no_temp_files` всё ещё сканирует только `.ssh`, не весь `$TEST_DIR`;
- absent origin в snapshot не проверяется как absent после case;
- snapshot не доказывает сохранение symlink/type/mode;
- NET cases идут подряд без per-case snapshot/reset/read-only audit;
- для `--check` нет invalid status, curl rc и curl timeout cases;
- `ORIGIN01-03` не проверяют exact set-url count/argv;
- global scan не использует exact generated tokens и вообще не создаёт API-body,
  malformed-remote и env sentinels;
- при unexpected rc `run_case` делает `cat` raw stdout/stderr, что само может
  вывести секрет;
- `CFG15` на Python host-parser crash отсутствует;
- setup-вызовы всё ещё идут через `run_case` и искусственно увеличивают `157`;
- handoff не содержит exact section counts и два отдельно записанных запуска.

## 2. Не импровизировать: exact архитектура mocks

Переписать блок mocks механически по следующим правилам. Каждый mock пишет только
safe operation name в audit, никогда не пишет key/base64/forced line/current origin.

### `stat`

Разрешены только:

```text
stat -c %U:%G <known-sandbox-path>
stat -c %a <known-sandbox-path>
```

Exact argc = 3. Любой другой format, лишний argv или path вне `$TEST_DIR` — rc 1.
Не делать fallback на generic `/usr/bin/stat "$path"`.

### `chown`

Разрешена только exact форма:

```text
chown astro:astro <existing-temp-file-inside-MOCK_HOME/.ssh>
```

Exact argc = 2; target только `known_hosts.github.??????`, `config.??????` или
`authorized_keys.??????`. Внешний/неизвестный target — rc 1. Audit до injected
failure, но audit содержит только safe basename/category.

### `mv`

Exact argc = 2. Source и destination проверять после `realpath -m`:

- source внутри `$MOCK_HOME/.ssh`, existing regular non-symlink temp с одним из
  трёх canonical prefixes;
- destination ровно `$KNOWN_HOSTS_GH`, `$SSH_CONFIG` или `$AUTHORIZED_KEYS` и
  соответствует source category.

Сначала validation, затем safe audit попытки, затем `MOCK_MV_FAIL_DEST`, затем real
`/usr/bin/mv -- "$src" "$dst"`.

### `git`

Разрешить только три exact arrays:

```text
git -C <MOCK_REPO> remote get-url origin
git -C <MOCK_REPO> remote set-url origin git@github.com-solarsage-prod:basilivanov/solarsage-astro.git
git -C <MOCK_REPO> ls-remote --exit-code origin refs/heads/main
```

Никаких дополнительных args. `get-url` при отсутствующем fixture возвращает
non-zero. `set-url` поддерживает `MOCK_GIT_SET_URL_RC`; audit exact safe operation
делается до injected failure. `ls-remote` сохраняет текущие rc/output controls.

Если argv содержит `fetch`, `checkout` или `push`, записать только safe command name
в `git_forbidden.log` и вернуть rc 1. Для прочего unknown argv — generic error без
печати полного argv.

### `curl`

Разрешить ровно один exact argv и exact order:

```text
curl -sS -o /dev/null -w %{http_code} --connect-timeout 5 --max-time 10 https://api.github.com/repos/basilivanov/solarsage-astro
```

Лишний/повторный/missing arg — rc 1. Никогда не сеть. Поддержать
`MOCK_CURL_RC`, `MOCK_CURL_STATUS`, и safe stderr sentinel
`MOCK_CURL_BODY_SENTINEL`; production перенаправляет stderr в `/dev/null`, поэтому
sentinel не должен попасть в case output.

### `timeout`

Разрешить только exact argv:

```text
timeout 15s git -C <MOCK_REPO> ls-remote --exit-code origin refs/heads/main
```

Normal mode вызывает sandbox mock `git` с exact remainder. Timeout mode возвращает
`124`. Любая другая команда/аргумент — rc 1 без exec.

### `ssh-keygen`

Разрешить только:

```text
ssh-keygen -y -P '' -f <sandbox-checkout-private>
ssh-keygen -l -f <sandbox-checkout-private-or-actions-public>
```

Exact argc/position; path внутри `$TEST_DIR` и exact allowed fixture. После проверки
делегировать `/usr/bin/ssh-keygen`. Любая иная форма — rc 1.

### `mktemp`

Разрешить:

- no args: `/usr/bin/mktemp "$TEST_DIR/validation.XXXXXX"`;
- один arg, exact template внутри `$MOCK_HOME/.ssh` для known_hosts/config/auth.

Никакого real no-arg `/tmp/tmp.*`. Unknown/extra args/outside path — rc 1. Safe
audit и `MOCK_MKTEMP_FAIL_PREFIX` до real creation.

### `python3.12`

Добавить PATH mock, который никогда не логирует inline code, base64, forced line или
file content. Он разрешает только `-c` и три production shapes:

1. `host-parse`: один sandbox validation file;
2. `config-write`: exact source config + exact temp config path + block argument;
3. `authorized-write`: exact source authorized_keys + exact temp path + base64 +
   forced-line arguments.

Определять operation по exact argc и exact path positions, не по secret contents.
Все path args обязаны быть внутри `$TEST_DIR`; unknown shape — rc 1. Safe audit:
только `python host-parse`, `python config-write`, `python authorized-write`.

Поддержать:

```text
MOCK_PYTHON_FAIL_OP=host-parse
MOCK_PYTHON_FAIL_OP=config-write
MOCK_PYTHON_FAIL_OP=authorized-write
```

Если operation совпал — audit попытки, затем rc 1; иначе делегировать
`/usr/bin/python3.12 "$@"`.

### Самопроверка mocks

До product matrix добавить `verify_mock_contracts`, не увеличивающий `CASE_COUNT`.
Он обязан доказать non-zero для extra argv и outside path хотя бы у `stat`, `chown`,
`mv`, `git`, `curl`, `timeout`, `ssh-keygen`, `mktemp`, `python3.12`. Output только
safe mock-id/rc, без full argv.

## 3. Exact helpers и безопасность diagnostics

### Honest case registry

`run_case`:

- принимает ID только по regex `^[A-Z0-9_-]+$`;
- fail при duplicate ID;
- записывает ID в `$TEST_DIR/case_ids`;
- только product contract case увеличивает `CASE_COUNT`;
- setup/preparation никогда не вызывает `run_case`.

В конце сверить обязательный manifest ID, а не только `CASE_COUNT >= 75`. При
описанной ниже матрице честный expected count — **162**. Missing/duplicate/unexpected
ID — failure.

### Preparation

Сделать `prepare_installed_state <safe-setup-id>`: запускает sandbox apply,
проверяет rc 0 и output safety, но не добавляет product case ID и не увеличивает
`CASE_COUNT`. Удалить `PATH_PREP*`, `CFG03 prepare`, `AK03 prepare`, `Prepare API`
из `run_case`.

### Snapshot

Snapshot обязан фиксировать для config, authorized_keys, known_hosts и origin:

- absent/file/symlink/other type;
- symlink target;
- mode;
- byte hash/bytes для regular file.

`assert_mutable_state_unchanged` сравнивает manifest целиком. Если origin был
absent, после case он также обязан быть absent. Не использовать только `[ -f ]`,
потому что это теряет symlink/type.

### No mutation / forbidden git

После каждого negative/read-only case явно вызывать и `assert_no_mutation_audit`,
и `assert_no_forbidden_git`. Диагностика не делает `cat` potentially hostile audit.

### Temp cleanup

Сканировать весь `$TEST_DIR` grouped `find`-expression на canonical temp patterns:
`validation.??????`, `known_hosts.github.??????`, `config.??????`,
`authorized_keys.??????`. Не ограничиваться `.ssh`.

### Safe failure output

При rc mismatch `run_case` печатает только case ID, expected/got rc и безопасные
пути к stdout/stderr. Нельзя `cat` raw output до secret scan.

## 4. Exact product case matrix для этого финального прохода

Сохранить все уже существующие CLI01-15, PATH01-40, KEY01-16, CFG01-14,
AK01-11, ORIGIN01-08 и корректные NET/FAIL cases. Добавить/исправить следующее.

### Installed state

Добавить девять ID из §1.1. Для каждого сначала normal installed state, затем одна
точечная corruption, snapshot после corruption, read-only `--preflight`, rc 1,
state unchanged, no mutation/forbidden git.

### CFG15 parser crash

После normal installed state:

```text
MOCK_PYTHON_FAIL_OP=host-parse
CFG15
```

`--preflight` должен вернуть rc 1, stderr должен содержать generic parser error и
не содержать `alias found`; state/audits read-only. Это acceptance production
exit-code fix в `scripts/prod-github-access.sh`.

### Byte exact

- `CFG02`: fixture с unrelated prefix **и suffix** вокруг canonical block; сохранить
  binary expected file с tabs/double spaces/CR-sensitive comment/final LF; после
  apply `cmp -s` всего файла.
- `AK02`: несколько unrelated prefix/suffix lines со spaces/comments; expected
  full file + ровно одна canonical forced line; `cmp -s`.
- `AK11`: создать реальные sandbox filenames, подходящие hostile glob; unrelated
  hostile line должна остаться byte-identical, никаких expanded filenames; full
  `cmp -s`.

### Origin exact audit

- `ORIGIN01`, `ORIGIN02`, `ORIGIN03`: ровно один exact canonical `set-url` допустим
  текущим production contract; проверить count = 1 и exact safe audit line.
- `ORIGIN04-08`: zero set-url/mv/chown, robust state unchanged, forbidden git empty.

Не менять production только ради zero redundant set-url; текущий контракт
«не более одного exact canonical call» допустим и должен быть честно описан.

### NET exact read-only cases

Перед **каждым** NET case: reset только audits/output данного case, snapshot. После:
state unchanged, no chown/mv/set-url, forbidden git empty, exact allowed curl/
timeout/git audit counts.

IDs:

```text
NET01 .. NET07
NET08_NONZERO
NET08_TIMEOUT
NET09 .. NET20
NET21_403
NET21_429
NET21_500
NET21_503
NET21_INVALID
NET21_CURL
NET21_TIMEOUT
NET22
NET23
```

`NET21_INVALID` — invalid HTTP string; `NET21_CURL` — curl rc 1;
`NET21_TIMEOUT` — curl rc 28. Для malformed remote case использовать уникальный
`MALFORMED_REMOTE_SENTINEL`, который production не должен повторять в output.

### FAIL01-09 и recovery

Расположить в числовом порядке. Ровно:

```text
FAIL01 FAIL01_REC
FAIL02 FAIL02_REC
FAIL03 FAIL03_REC
FAIL04 FAIL04_REC
FAIL05 FAIL05_REC
FAIL06 FAIL06_REC
FAIL07 FAIL07_REC
FAIL08 FAIL08_REC
FAIL09 FAIL09_REC
```

- FAIL01-03 — три mktemp failures;
- FAIL04 — `MOCK_PYTHON_FAIL_OP=config-write`, не mktemp;
- FAIL05 — `MOCK_PYTHON_FAIL_OP=authorized-write`, не mktemp;
- FAIL06-08 — три exact mv failures;
- FAIL09 — exact set-url failure; начальный origin сделать HTTPS, чтобы failure
  доказал сохранение old URL, а recovery — реальную нормализацию.

Для каждого failure:

1. snapshot old state;
2. rc non-zero;
3. success message отсутствует;
4. каждый destination равен либо полному old, либо полному canonical expected-new;
5. no temp files;
6. only allowed safe audit attempts;
7. снять injection;
8. `_REC` apply rc 0;
9. full canonical bytes/modes и canonical origin.

Подготовить canonical expected-new state один раз в отдельном sandbox snapshot;
не считать этот setup product case. Не утверждать all-file rollback.

## 5. Global output scan, который реально что-то доказывает

В setup сохранить exact безопасно в переменные, но никогда не печатать:

- checkout public base64 token;
- Actions public base64 token;
- credential URL sentinel;
- `API_BODY_SENTINEL_R13`;
- `MALFORMED_REMOTE_SENTINEL_R13`;
- `ENV_SECRET_SENTINEL_R13`;
- Actions comment;
- PEM marker.

Экспортировать env sentinel в child. Curl mock пишет API body sentinel в stderr,
который production обязан подавить. Один malformed remote case возвращает exact
remote sentinel; production обязан вернуть generic error. В конце сканировать все
per-case stdout/stderr exact fixed-string (`grep -F`) по каждому sentinel/token.

Fingerprint разрешён. При обнаружении печатать только safe sentinel name и case
output filename, не совпавшую строку.

## 6. Acceptance и честный handoff

До обновления handoff выполнить:

```bash
bash -n scripts/prod-github-access.sh scripts/tests/test-prod-github-access.sh
timeout 240 bash scripts/tests/test-prod-github-access.sh
git diff --check -- scripts/prod-github-access.sh scripts/tests/test-prod-github-access.sh
```

Повторить весь набор два раза подряд. Оба harness run:

- rc 0;
- exact honest count `162`;
- manifest всех required IDs совпал;
- видны `CFG15`, `NET21_TIMEOUT`, `FAIL09_REC`;
- final `All 162 ... passed!`.

В `56_HANDOFF...` записать:

- section counts, сумма = 162;
- explicit IDs новых subcases;
- два отдельных запуска с rc;
- mock self-check result;
- что FAIL04/05 используют Python injection;
- no production/network/commit/push.

После этого остановиться и ждать независимого архитектурного acceptance.
