# R13 Phase B3 R1 — REJECTED: suite не доходит до конца и остаются safety gaps

## Независимый результат

Команда:

```bash
bash -n scripts/prod-github-access.sh scripts/tests/test-prod-github-access.sh && \
timeout 240 bash scripts/tests/test-prod-github-access.sh && \
git diff --check -- scripts/prod-github-access.sh scripts/tests/test-prod-github-access.sh
```

завершилась `rc 1`. Последний напечатанный case — `ORIGIN07`; `ORIGIN08`, все NET и FAIL cases фактически не выполнялись. Поэтому `56_HANDOFF...` с `rc 0`/111 cases не принят.

## 1. Немедленный silent-exit blocker

`snapshot_mutable_state` заканчивается строкой:

```bash
[ -f "$TEST_DIR/mock_origin" ] && cp ...
```

В `ORIGIN08` origin намеренно отсутствует, выражение возвращает 1; функция также возвращает 1, а top-level `set -e` завершает suite до `run_case` без сообщения.

Исправить helpers явными `return 0` там, где отсутствие optional fixture является нормальным:

- `snapshot_mutable_state`;
- `reset_audits`/`reset_fixture` и другие helpers с условной последней командой проверить на тот же дефект.

Добавить EXIT diagnostic trap для harness, который при unexpected exit печатает только безопасные `last_case_id` и rc, не secrets.

## 2. Реальный secret-log defect в production origin validation

`scripts/prod-github-access.sh` сейчас включает raw `$current_origin` в error messages. Case `ORIGIN06` использует credential-bearing URL; такой URL не должен попадать в stdout/stderr.

Сначала расширить `assert_output_safe` exact sentinel-проверкой credential URL/token, получить красный case, затем минимально исправить production errors:

- не печатать raw invalid origin;
- писать generic: origin отсутствует/не соответствует expected owner/repo/canonical alias;
- canonical safe target URL можно печатать только как expected constant, но не caller-controlled value.

Global output scan должен искать exact generated checkout/Actions base64 tokens, Actions comment, credential sentinel, API-body sentinel, malformed-remote sentinel и env sentinel. Сохранять каждый case output в отдельный `$TEST_DIR/outputs/<case-id>.stdout|stderr`, а не перезаписывать два файла; в конце сканировать всю директорию.

## 3. Cases, которые всё ещё не реализованы полностью

### Installed file security

После successful apply добавить отдельные cases, а не объединённые labels:

- installed known-hosts wrong mode и wrong owner;
- config wrong mode и wrong owner;
- authorized_keys wrong mode и wrong owner.

### Byte-exact preservation

- `CFG02` сейчас проверяет только `grep "Host unrelated"`; сформировать exact expected binary file и `cmp -s` всего config.
- `AK02`/`AK11` сейчас проверяют только substring; сравнить unrelated prefix/suffix bytes exact, включая spaces/comments/CR-sensitive bytes.

### Origin audit

- `ORIGIN01/02/03`: assert exact count и exact argv `remote set-url`; normalized form — no redundant mutation либо contractually documented one exact call.
- `ORIGIN04-08`: zero set-url/mv/chown and state unchanged. Missing-origin snapshot должен также доказать, что origin остаётся absent.

### NET read-only proof

После prepare reset audits и snapshot. Перед каждым NET case reset only audits/output, затем assert:

- state byte-identical;
- no chown/mv/set-url;
- no fetch/checkout/push;
- only expected curl/timeout/git ls-remote shapes.

Добавить для `--check` также invalid HTTP status и curl nonzero/timeout, а не только 403/429/500/503.

### Failure injection/recovery

Сейчас есть только FAIL01/02/03/06(config)/08(authorized), причём recovery не проверяется. Добавить:

- mv known-hosts failure;
- config helper/write failure;
- authorized helper/write failure;
- origin set-url failure;
- после каждого failure assert no success message, destinations complete old-or-new, no temps;
- снять injection и повторить apply: exact canonical state должен восстановиться.

Не называть config mv `FAIL06`, если по матрице FAIL06 — known-hosts; IDs/описания должны совпадать с `55_TZ`.

## 4. Mock/test correctness

1. `assert_no_temp_files` переписать с grouped find expression:

```bash
find "$MOCK_HOME/.ssh" \( ... \) -print -quit
```

Текущая OR-expression без скобок может не печатать часть совпадений.
2. Mock `mktemp` без args сейчас вызывает real `/usr/bin/mktemp` и создаёт `/tmp/tmp.*` вне sandbox. Для no-arg invocation создавать `$TEST_DIR/validation.XXXXXX`; unknown argv fail. Искать temp leaks во всём `$TEST_DIR`, не только `.ssh`.
3. Mock `mv` валидирует destination, но не source. Проверить оба operands и exact argc.
4. Mock `git` валидирует только partial subcommand. Проверить exact full argv и exact canonical set-url URL.
5. Mock `ssh-keygen` привести к exact allowed invocation shapes из `55_TZ`, не generic argument walk.
6. `assert_no_forbidden_git` не печатает полный potentially hostile args; только safe command name.
7. `run_case` должен устанавливать `LAST_CASE_ID` до child invocation и сохранять per-case outputs.

## 5. Production cleanup

- Добавить `sha256sum` в `# DEPENDENCIES` `scripts/prod-github-access.sh` (host required-command inventory уже содержит его).
- SHA-256 pin и wrapper single comparator оставить.
- Host parser оставить case-insensitive/all-pattern, но отличить alias-found от Python parse/runtime error либо fail closed с generic parse error; не маскировать любой helper crash как «alias найден».

## 6. Acceptance этого узкого исправления

Не менять другие harnesses, `51`, R12 или unrelated production files. Обновить `56_HANDOFF...` только после свежего полного прогона.

Выполнить два раза подряд:

```bash
bash -n scripts/prod-github-access.sh scripts/tests/test-prod-github-access.sh
timeout 240 bash scripts/tests/test-prod-github-access.sh
git diff --check -- scripts/prod-github-access.sh scripts/tests/test-prod-github-access.sh
```

Оба запуска harness должны напечатать final `All ... passed`, включать ORIGIN08, NET23 и последний recovery case, и вернуть `rc 0`. После handoff остановиться. Production/real network/commit/push запрещены.
