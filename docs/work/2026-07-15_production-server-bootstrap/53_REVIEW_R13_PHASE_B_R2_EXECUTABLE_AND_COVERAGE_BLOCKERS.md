# R13 Phase B R2 — REJECTED: executable failure и незакрытая contract matrix

## Статус

Phase B повторно не принята. После handoff кодера независимый запуск дал:

- `bash -n ...` — `rc 0`;
- `test-prod-github-access.sh` — `rc 0`, но test matrix остаётся существенно неполной и содержит ложные assertions;
- `test-prod-github-wrapper.sh` — `rc 0`, но не закрывает оба verbs и exact argv/rc contract;
- `test-prod-source-readiness-workflow.sh` — **`rc 1`**;
- `test-prod-deploy-source-loader.sh` — `rc 0`, но порядок вызовов не доказан и обязательные negative cases отсутствуют.

`51_REVIEW_R13_PHASE_B_HANDOFF.md` снова недостоверен: в нём заявлен `rc 0` workflow harness, хотя текущий файл воспроизводимо падает. Production apply/deploy, commit и push запрещены.

## 1. Немедленный executable blocker: workflow harness

Текущая причина падения:

```text
grep: invalid option -- ' '
FAIL: SR has IdentitiesOnly (pattern '-o IdentitiesOnly=yes' not found ...)
```

В `assert_contains`/`assert_not_contains` pattern начинается с `-o`, а вызывается `grep -q "$pattern"`. Исправить на безопасную форму (`grep -Fq -- "$pattern"` для literal search либо эквивалент с `--`). После исправления тест обнаружит следующий ложный positive: global forbidden-word checks видят слова `checkout`, `build`, `systemctl` в GRACE-комментариях. Проверять executable YAML content/steps, игнорируя comments, а не весь файл целиком.

После любого изменения workflow harness обязательно запустить заново из свежего shell. Нельзя переносить `rc` от запуска до последнего редактирования в handoff.

## 2. `test-prod-source-readiness-workflow.sh`: validator должен доказывать контракт, а не наличие слов

### 2.1 Текущие пробелы

1. Проверяется отсутствие только `push`, `pull_request`, `schedule`; отсутствуют `repository_dispatch`, `workflow_call` и другие запрещённые triggers из ТЗ.
2. Наличие `workflow_dispatch` плюс несколько negative grep не доказывает, что trigger действительно единственный в `on` block.
3. `verify_step_order` считает `github.event.repository.private` в `env` доказательством private gate. Удаление фактического `if [ "$IS_PRIVATE" != "true" ] ... exit 1` останется зелёным.
4. Secret validator проверяет только отсутствие неизвестных имён. Если удалить один или все четыре обязательных secrets, тест пройдёт. Нужен exact set equality.
5. Не проверяются `-T`, `-i`, `ConnectTimeout`, `ServerAliveInterval`, `ServerAliveCountMax` и `UserKnownHostsFile` для обоих workflows.
6. Remote command проверяется presence substring, а не exact final argument без `;`, pipe, suffix/prefix или второго command.
7. Cleanup presence не привязана к конкретному cleanup step и не доказывает, что `if: always()` относится именно к нему.
8. Forbidden operations проверяются глобальными словами; после исправления grep они конфликтуют с GRACE comments и всё равно не анализируют реальные `uses:`/`run:` steps.
9. Нет проверки branch/SHA fail-closed gate, хотя workflow contract его фиксирует.
10. Нет self-proof, что validator падает при удалении критической строки; предыдущая версия уже пропустила отсутствие `BatchMode`.

### 2.2 Требуемая реализация

Вынести проверку одного workflow в функции, принимающие path, чтобы canonical и намеренно испорченные sandbox copies проходили через один и тот же validator.

Canonical assertions:

- exact `on` contract: только `workflow_dispatch`;
- exact concurrency group/cancel mode;
- `permissions: {}`, `environment: production`, readiness timeout `<= 10`;
- branch `refs/heads/main`, exact lowercase 40-hex SHA и private check с non-zero exit;
- gate step расположен до Configure SSH и до `ssh -T`;
- exact secrets set равен четырём разрешённым именам;
- exact SSH option set для readiness и deploy: `-T`, `-i`, `IdentitiesOnly=yes`, `BatchMode=yes`, `UserKnownHostsFile`, `StrictHostKeyChecking=yes`, bounded ConnectTimeout/keepalive;
- exact remote command argument;
- cleanup step имеет `if: always()` и удаляет оба файла;
- readiness executable steps не содержат checkout/build/deploy/systemctl/restart/migration/package installation.

Добавить mutation/self-test copies минимум для следующих дефектов; каждый испорченный copy обязан дать non-zero:

1. добавить `push` trigger;
2. удалить private conditional либо заменить `exit 1` на `:`;
3. переместить private gate после Configure SSH;
4. удалить `BatchMode=yes`;
5. добавить `secrets.EXTRA_SECRET`;
6. удалить один обязательный secret reference;
7. заменить remote command на `source-check $GITHUB_SHA; id`;
8. удалить `if: always()`;
9. добавить executable checkout/build/systemctl step.

Mutation copies живут только в `$TEST_DIR`; canonical workflows не менять во время теста.

## 3. `test-prod-github-access.sh`: заявленные 31 cases не соответствуют `50_TZ`/`52_REVIEW`

### 3.1 Текущие ложные утверждения

1. Passphrase key генерируется, но ни один case его не использует.
2. `Apply: mv failure leaves originals unchanged` неверно сформулирован и неверно проверен:
   - fixture до apply не содержит config;
   - `mv known_hosts` уже может успешно произойти до отказа на config;
   - assertion проверяет только отсутствие config;
   - known_hosts/authorized_keys bytes, partial state и temp cleanup не проверяются;
   - `PASS: Apply atomic cleanup` печатается без поиска temp files.
3. `Unrelated configuration preserved` использует `grep`, а не byte-exact `cmp`; изменение пробелов, LF/CR или комментария останется незамеченным.
4. Idempotence сравнивает только config и authorized_keys; installed known_hosts и origin audit не проверяются.
5. Output scan на private/public material, API body и malformed remote output отсутствует.
6. CLI cases не доказывают отсутствие stat/git/curl/mutation: audit после каждого usage error не проверяется.

### 3.2 Обязательные отсутствующие cases

Не сокращать матрицу из `52_REVIEW`, а реализовать её. В текущем файле отсутствуют как минимум:

- non-root `--apply`;
- short, long и uppercase SHA;
- missing/symlink/FIFO/directory/wrong mode/wrong owner отдельно для checkout pub/private, Actions pub, wrapper, template, installed files, repo и `.git`;
- checkout mismatch, passphrase private key, malformed key files;
- Actions CRLF, extra blank line, wrong key type, invalid base64, PEM/private material и explicit valid-line case;
- changed wrapper, changed known-hosts template и changed installed known-hosts;
- config duplicate BEGIN, duplicate END, reversed markers, alias outside block, conflicting block, no-final-LF и unrelated byte-exact preservation;
- authorized_keys canonical exact line, unquoted command, same key unrestricted, duplicate exact, same key multiple forms, same comment other key, no-final-LF, raw unrelated byte preservation;
- old SSH/already-normalized origin success; wrong repo/owner, credential URL, missing/unknown origin failures и zero `set-url` audit;
- API 429/5xx/invalid/timeout для preflight и check;
- ls-remote timeout 124, empty, multiple lines, wrong ref, spaces instead of TAB, uppercase/short/long SHA;
- read-only audit proving no writes/set-url/fetch/checkout/push;
- mktemp/write failure и каждый rename destination;
- partial-state recovery by second apply;
- complete secret-safe output scan.

### 3.3 Mock corrections

- `trap` должен включать `EXIT INT TERM HUP`.
- PATH передавать тестируемому child, не экспортировать на весь harness без необходимости.
- `mv` обязан проверить normalized source/destination внутри sandbox до `/usr/bin/mv`.
- `git` обязан проверить exact full argv, а не только первый subcommand.
- `curl` обязан проверить required timeout/output flags, а не только последний URL.
- `ssh-keygen` не должен разрешать реальные `/etc/solarsage/*` paths.
- `reset_fixture` обязан byte-exact восстанавливать все baseline fixtures и production-script copy; один case не должен загрязнять следующий.
- Каждый negative case: snapshot + exact rc + no-mutation audit + temp cleanup.

Case count не является acceptance-критерием. Принимать будем по явно перечисленным assertions и mutation proof.

## 4. `test-prod-github-wrapper.sh`: расширить оба verbs и exact target contract

Текущая версия улучшена, но остаются пробелы:

1. Почти вся hostile matrix выполнена только для `deploy`; `source-check` проверяется только без SHA.
2. Нет long SHA, non-hex SHA, leading/trailing space и extra argument variants для обоих verbs.
3. Target audit использует `echo "$@"`, что теряет границы argv. Grep не anchored и может принять дополнительные аргументы.
4. Проверен target rc только `42`; обязательны минимум `1`, `42`, `126` для обоих dispatch targets.
5. Helper ошибочно связывает `expected_rc == 126` с «target не должен быть вызван». Для propagation case target сам может вернуть 126. Передавать отдельный `expect_target_call=yes|no`.
6. `trap` должен включать `INT TERM HUP`.

Записывать target argv в безопасном однозначном формате (`printf '%q\n'` по каждому arg либо NUL-record) и сравнивать exact expected file через `cmp`.

Production wrapper сейчас может остаться с дополнительной tab/space защитой, но тест обязан доказать exact literal-one-space contract для обоих verbs.

## 5. `test-prod-deploy-source-loader.sh`: текущий audit не доказывает порядок

### 5.1 Критический false positive

Текущий код делает:

```bash
actual_order=$(cat "$TEST_DIR/monotonic_audit.log" | sort -n)
```

Сортировка исправляет неправильный фактический порядок. Если production вызовет fetch до access check, markers всё равно будут отсортированы в ожидаемый порядок. Сравнивать audit **как записан**, без sort. Номера должны отражать последовательность вызова, а не быть hardcoded именем mock. Лучше audit append без номеров и exact `cmp` с expected order.

### 5.2 Нарушение sandbox

Production copy продолжает использовать real `/tmp/solarsage-deploy.lock` и real `mktemp` внутри `check_clean_source`, то есть harness создаёт paths вне единственного `$TEST_DIR`. Path-substitute lockfile и mock/path-control `mktemp`, затем проверять cleanup.

### 5.3 Отсутствующие обязательные cases

- no args/unknown/extra/duplicate/current+SHA and short/long/uppercase SHA parser shapes согласно production contract;
- `.env.production`: symlink, directory/FIFO, wrong owner, allowed 600 and 640 modes;
- loader: missing, symlink, directory/non-regular;
- static scan на direct `.env.production` source, `eval`, `set -a` loader bypass;
- wrong origin с no `remote set-url`;
- access expected-SHA mismatch/nonzero до fetch/build;
- fingerprint missing/malformed/mismatch cases;
- loader export verification: exact sandbox `SOLARSAGE_EPHEMERIS_PATH` реально прочитан и directory validated;
- exact git argv validation; unknown remote subcommand должен падать;
- no real build/DB/systemctl/sudo/network calls;
- temp/lock cleanup.

### 5.4 Mock correctness

- `stat` outside sandbox должен fail, не делегировать real stat.
- owner override сделать path-specific; сейчас всегда `astro:astro`.
- git `remote` проверяет exact `get-url origin`; неизвестный remote subcommand — fail.
- `rev-parse HEAD` и `rev-parse origin/main` должны иметь отдельные configurable values.
- forbidden audit не выводить через command substitution в error, если там потенциально чувствительные args; печатать безопасные command names.
- early-stop insertion должен assert, что вставлена ровно одна marker line в ожидаемом месте.

## 6. `51_REVIEW_R13_PHASE_B_HANDOFF.md`

До зелёного независимого review документ не называть acceptance. Исправить:

- убрать утверждение «executed independently» — это coder-run evidence, независимый запуск делает архитектор;
- не указывать `rc 0`, который не был получен после последнего изменения;
- не утверждать no forbidden calls/temp leaks без соответствующих assertions;
- перечислить exact commands и фактические outputs/rc из одного финального прогона после всех edits;
- repository fingerprint пересчитать после последнего изменения;
- явно отметить, что production apply/deploy, commit/push не выполнялись.

## 7. Acceptance sequence после исправлений

Кодер должен выполнить в таком порядке и остановиться:

1. `bash -n` всех шести shell files.
2. Четыре R13 harnesses по одному из свежего shell, без параллельной записи общих paths.
3. Повторно четыре R13 harnesses единым sequential command, чтобы исключить state leakage.
4. Полный R12 suite, отдельный rc каждого файла.
5. `git diff --check`.
6. Repository fingerprint.
7. Обновить `51` только этими последними результатами.

Не запускать production, real network/SSH/GitHub API/fetch/checkout/push. Не делать commit/push. Не трогать/stage frozen paths из `52_REVIEW`.
