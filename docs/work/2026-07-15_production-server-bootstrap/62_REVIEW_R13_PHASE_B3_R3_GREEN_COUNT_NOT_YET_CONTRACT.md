# R13 Phase B3 R3 — REJECTED: 162 green, но count ещё не доказывает contract

## Независимый результат

Архитектор выполнил два свежих запуска `timeout 300 bash
scripts/tests/test-prod-github-access.sh`. Оба вернули `rc 0` и финальную строку
`All 162 ... passed!`. Исполняемость подтверждена.

Acceptance пока отклонён, потому что статическая инспекция обнаружила конкретные
расхождения между `56_HANDOFF...`, ТЗ 55/60 и фактическим harness. Исправление
узкое: только `scripts/tests/test-prod-github-access.sh` и затем честное обновление
`56_HANDOFF...`. Production script менять не требуется, если новый тест не выявит
новый production defect.

Запрещены production/network/SSH/GitHub, другие harness/workflow, commit и push.

## 1. Обязательный ID manifest, а не только число 162

Сейчас `case_ids` используется только для duplicate check, а в конце сравнивается
только `CASE_COUNT == 162`. Поэтому любой другой набор из 162 уникальных ID пройдёт,
хотя handoff утверждает «each verified against manifest».

Создать `$TEST_DIR/expected_case_ids` независимо от фактически выполненных cases.
Сформировать canonical список:

- `CLI01..CLI15`;
- `PATH01..PATH40`;
- `PATH41_SYMLINK`, `PATH41_MODE`, `PATH41_OWNER`;
- `PATH42_SYMLINK`, `PATH42_MODE`, `PATH42_OWNER`;
- `PATH43_SYMLINK`, `PATH43_MODE`, `PATH43_OWNER`;
- `KEY01..KEY16`;
- `CFG01..CFG15`;
- `AK01..AK11`;
- `ORIGIN01..ORIGIN08`;
- `NET01..NET07`, `NET08_NONZERO`, `NET08_TIMEOUT`, `NET09..NET20`;
- `NET21_403`, `NET21_429`, `NET21_500`, `NET21_503`, `NET21_INVALID`,
  `NET21_CURL`, `NET21_TIMEOUT`, `NET22`, `NET23`;
- `FAIL01..FAIL09` и `FAIL01_REC..FAIL09_REC`.

Переименовать текущие loop ID `NET21-403` и т. п. в underscore-варианты выше,
чтобы совпасть с handoff. В конце:

1. оба файла сортируются в отдельные safe temp copies;
2. exact `cmp -s` expected vs actual;
3. expected line count = 162;
4. actual line count = 162;
5. при mismatch печатать только generic missing/unexpected ID либо безопасные ID,
   не case output.

## 2. Handoff переоценивает fail-closed mocks

Исправить оставшиеся permissive формы.

### `chown`

- Разрешить только owner `astro:astro`; production в этом script не вызывает
  `root:root`.
- Target должен существовать, быть regular non-symlink и иметь exact basename
  `known_hosts.github.<6 alnum>`, `config.<6 alnum>` или
  `authorized_keys.<6 alnum>`.

### `mv`

- Source должен существовать, быть regular non-symlink;
- exact six-character mktemp suffix, не broad `config.*`;
- destination/category уже проверяются — оставить;
- audit до injected failure.

### `ssh-keygen`

- `-y -P '' -f` разрешён только для exact checkout private fixture;
- `-l -f` разрешён только для exact checkout private или Actions public fixture;
- произвольный sandbox file должен fail.

### `mktemp`

One-arg форма должна совпадать ровно с одним из трёх template strings:

```text
$MOCK_HOME/.ssh/known_hosts.github.XXXXXX
$MOCK_HOME/.ssh/config.XXXXXX
$MOCK_HOME/.ssh/authorized_keys.XXXXXX
```

Не принимать любой prefix внутри `.ssh`.

### `python3.12`

- host-parse target: existing regular non-symlink
  `$TEST_DIR/validation.<6 alnum>`;
- config-write temp: exact existing regular non-symlink
  `$MOCK_HOME/.ssh/config.<6 alnum>`;
- authorized-write temp: exact existing regular non-symlink
  `$MOCK_HOME/.ssh/authorized_keys.<6 alnum>`;
- source targets остаются exact config/authorized paths;
- arbitrary sandbox path должен fail.

### `verify_mock_contracts`

Добавить negative self-checks именно для оставшихся дыр:

- `chown root:root` на допустимом sandbox temp;
- `mv` nonexistent source, symlink source и wrong category;
- `ssh-keygen` на произвольном sandbox file;
- `mktemp $MOCK_HOME/.ssh/arbitrary.XXXXXX`;
- Python host-parse на arbitrary sandbox file;
- Python config/authorized temp с wrong basename.

Handoff не должен говорить «all wrong targets proved», пока эти checks не работают.

## 3. NET должен доказывать exact read-only call counts

Строгие argv mocks не обнаруживают повторный разрешённый вызов. Сейчас NET cases
проверяют state/no-set-url, но не counts `curl`, `timeout`, `ls-remote`.

Добавить helper `assert_net_audit <remote_expected:0|1>`:

- `curl_audit.log`: ровно одна строка `curl`;
- `git_audit.log`: ровно одна строка `git remote get-url origin`;
- `git remote set-url origin`: zero;
- `git ls-remote`: ровно `remote_expected`;
- `timeout_audit.log`: ровно `remote_expected` строк `timeout`;
- никаких других строк в этих audit files;
- forbidden git empty.

Вызывать после каждого NET case. `remote_expected=1`:

- NET01, NET02;
- NET09..NET18;
- NET20, NET22, NET23.

Для остальных NET — `0`. Если фактическая production flow отличается, сначала
получить красный test и проверить логику; expected rc менять ради зелёного нельзя.

## 4. Sentinels должны реально входить в опасный канал

Сейчас `API_BODY_SENTINEL_R13` нигде не передаётся mock curl, а
`MALFORMED_REMOTE_SENTINEL_R13` передаётся как curl stderr, не как remote output.
Global scan поэтому не доказывает заявленные два свойства.

- В одном curl failure/timeout case установить
  `MOCK_CURL_BODY_SENTINEL="$API_BODY_SENTINEL_R13"`; production stderr redirect
  должен скрыть его.
- В `NET13` сформировать malformed/wrong-ref `MOCK_GIT_LS_REMOTE_OUT`, содержащий
  exact `$MALFORMED_REMOTE_SENTINEL_R13`; production error обязан остаться generic.
- После cases обязательно очистить env controls.
- Global exact fixed-string scan оставить.

`ENV_SECRET_SENTINEL_R13` уже экспортирован в child и scan остаётся полезным.

## 5. Failure/recovery contract пока почти не проверяется

Сейчас FAIL01–08 проверяют главным образом rc и отсутствие temp. Не проверяются
отсутствие success message, complete old-or-new destinations и canonical recovery,
хотя handoff заявляет полноценный failure matrix.

### Expected state

Один раз вне `CASE_COUNT` построить canonical expected installed state успешным
sandbox apply и сохранить exact bytes + modes для:

- known_hosts.github;
- config;
- authorized_keys;
- canonical origin.

### После каждого FAIL01–09

Проверить:

1. stdout/stderr не содержат `Successfully applied GitHub transport configuration.`;
2. no temp files;
3. каждый destination — regular non-symlink с полными canonical expected bytes/
   mode **или** равен полному old state/absent; никакого truncated/другого файла;
4. origin равен old либо canonical только там, где это допустимо порядком операций;
   для FAIL09 обязательно old HTTPS;
5. audit содержит только допустимые попытки этого failure и forbidden git empty.

### После каждого `_REC`

Проверить full canonical installed state: три exact файла, modes `600`, non-symlink,
canonical origin. Recovery rc 0 недостаточен сам по себе.

Не заявлять all-file rollback: для FAIL07/08 допустимы ранее завершённые complete
renames.

## 6. Safe diagnostics и cleanup

- `prepare_installed_state` при failure сейчас делает raw `cat` stdout/stderr.
  Заменить на safe setup label, rc и пути к output; сначала scan, содержимое не
  печатать.
- После успешного harness проверить отсутствие новых
  `/tmp/solarsage-r13-access-test.*`.
- Существует старый каталог
  `/tmp/solarsage-r13-access-test.Mq98br` от оборванного предыдущего запуска.
  Перед удалением проверить, что owner=`astro`, path exact и внутри только harness
  fixture; затем удалить **только этот exact path**, не wildcard.

## 7. Acceptance

Число product cases остаётся **162**, новые self-checks не входят в `CASE_COUNT`.

Выполнить два раза подряд:

```bash
bash -n scripts/prod-github-access.sh scripts/tests/test-prod-github-access.sh
timeout 300 bash scripts/tests/test-prod-github-access.sh
git diff --check -- scripts/prod-github-access.sh scripts/tests/test-prod-github-access.sh
```

Оба запуска:

- rc 0;
- exact expected-ID manifest = actual manifest;
- `All 162 ... passed!`;
- последний `FAIL09_REC` выполнен;
- no leaked current harness temp directory.

После этого обновить `56_HANDOFF...` только фактическими доказанными claims и
остановиться. Никаких следующих R13 phases, commit/push или production действий.
