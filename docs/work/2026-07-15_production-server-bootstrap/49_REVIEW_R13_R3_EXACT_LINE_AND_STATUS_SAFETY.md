# R13 review R3 — exact-line validation и последние Phase A blockers

Статус: **Phase A всё ещё не принята**. Исправить только этот короткий список, tests пока не переписывать.

## 1. Critical: `xargs` ломает exact forced-command validation

Текущий код в `validate_installed_state` делает:

```bash
line=$(echo "$line" | xargs)
```

Для канонической строки:

```text
restrict,command="/usr/local/sbin/solarsage-github-deploy" ssh-ed25519 ... solarsage-github-actions-prod
```

`xargs` удаляет кавычки и возвращает `restrict,command=/usr/local/...`. Сравнение с `expected_forced_line`, где кавычки есть, всегда false. Следствие: `--apply` записывает файлы, затем post-validation падает; `--preflight`/`--check` тоже никогда не принимают корректный managed line.

Исправление:

- не пропускать authorized_keys lines через `echo`, `xargs`, word splitting или shell reconstruction;
- сравнивать raw line byte-for-byte с exact canonical line (удаляется только завершающий LF самим `read -r`);
- blank/unrelated lines сохранять и игнорировать без нормализации;
- same base64 token искать как SSH key field, не как произвольный substring комментария, либо использовать консервативный parser, который не меняет bytes;
- Actions public key тоже читать через `IFS= read -r`, а не `cat | xargs`; key type/base64 извлекать без интерпретации quotes/backslashes;
- добавить внутренний безопасный proof/harness в Phase B: canonical quoted line проходит, unquoted/extra options/duplicate line fails.

Независимое доказательство текущего бага:

```text
raw:        restrict,command="/usr/local/sbin/solarsage-github-deploy" ...
xargs:      restrict,command=/usr/local/sbin/solarsage-github-deploy ...
raw == xargs: no
```

## 2. GitHub API body должен быть suppressed

`get_github_visibility_status` сейчас сохраняет весь anonymous API body в `curl_out` и берёт последнюю строку. R13 требует body suppressed.

Использовать:

```bash
curl -sS -o /dev/null -w '%{http_code}' --connect-timeout ... --max-time ... URL
```

Capture curl rc отдельно; rc != 0 — runtime fail. Проверить status regex `^[0-9]{3}$`. Не хранить и не печатать body.

## 3. Duplicate `--expected-sha` должен быть usage error

Сейчас два `--expected-sha` молча перезаписывают друг друга. Ввести `EXPECTED_SHA_SEEN=0/1`; повтор → rc 2. Также доказать rc 2 для duplicate action, missing SHA, SHA без check и unknown option.

## 4. Safe `ls-remote` error output

Exact regex с TAB работает, но при malformed output ошибка сейчас печатает raw remote line. Не печатать untrusted remote output; сообщение должно содержать только факт shape mismatch. SHA печатать только после успешной exact validation.

## 5. Dependency inventory

`prod-github-access.sh` использует `timeout`. Добавить `timeout` в `REQUIRED_CMDS` host/bootstrap readiness (coreutils обычно уже установлен, но readiness должна проверять фактическую команду). Если используются `wc`, `tail`, `od`, оставить их как base-system dependency либо перечислить в module dependency contract последовательно.

## Acceptance этого раунда

```bash
bash -n scripts/prod-github-access.sh scripts/prod-deploy.sh scripts/prod-host-prepare.sh scripts/prod-os-bootstrap.sh
scripts/prod-github-access.sh --check --expected-sha 0123456789012345678901234567890123456789 --expected-sha 0123456789012345678901234567890123456789
# expected rc 2, no filesystem/network check
git diff --check
```

Дополнительно локально показать, что raw canonical forced line сравнивается без удаления кавычек. Никакой реальной сети/apply/deploy, commit/push.
