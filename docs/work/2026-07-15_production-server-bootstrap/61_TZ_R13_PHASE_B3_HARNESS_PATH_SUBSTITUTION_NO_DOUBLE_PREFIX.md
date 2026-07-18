# R13 B3 — точечный fix path substitution в isolated harness

## Проблема

Тестовый `reset_fixture` несколько раз заменяет абсолютные пути generic `sed` и
получает двойные/пустые prefixes (`$TEST_DIR$TEST_DIR`, отсутствующий
`$TEST_SCRIPT`). Из-за этого production copy нельзя диагностировать, а suite
зависит от случайного порядка замен.

## Сделать ровно так

В `reset_fixture` после `cp` production script выполнить только замены **полных
строк assignment**, без поиска/замены всех вхождений `/opt/solarsage-astro`:

```bash
sed -i \
  -e "s|^SSH_DIR=\"/home/astro/\\.ssh\"$|SSH_DIR=\"$MOCK_HOME/.ssh\"|" \
  -e "s|^ACTIONS_PUB=\"/etc/solarsage/keys/github-actions-deploy.pub\"$|ACTIONS_PUB=\"$MOCK_ETC/keys/github-actions-deploy.pub\"|" \
  -e "s|^FORCED_WRAPPER=\"/usr/local/sbin/solarsage-github-deploy\"$|FORCED_WRAPPER=\"$MOCK_WRAPPER\"|" \
  -e "s|^REPO_DIR=\"/opt/solarsage-astro\"$|REPO_DIR=\"$MOCK_REPO\"|" \
  "$TEST_SCRIPT"
```

В actual-файле используй корректное экранирование `.` для sed; смысл — match
только четыре assignment lines от начала до конца строки.

Никаких дополнительных замен для:

- `TEMPLATE_KNOWN_HOSTS` — он вычисляется из уже подменённого `REPO_DIR`;
- `CHECKOUT_KEY`, `CHECKOUT_PUB`, `KNOWN_HOSTS_GH`, `SSH_CONFIG`,
  `AUTHORIZED_KEYS` — они вычисляются из уже подменённого `SSH_DIR`;
- cmp/error strings в теле production script;
- inline Python arguments.

После substitution добавить fail-fast sanity check **до запуска matrix**:

```bash
grep -Fxq "SSH_DIR=\"$MOCK_HOME/.ssh\"" "$TEST_SCRIPT"
grep -Fxq "REPO_DIR=\"$MOCK_REPO\"" "$TEST_SCRIPT"
grep -Fxq "FORCED_WRAPPER=\"$MOCK_WRAPPER\"" "$TEST_SCRIPT"
! grep -Fq '$TEST_DIR$TEST_DIR' "$TEST_SCRIPT"
! grep -Fq 'MOCK_REPO_PLACEHOLDER' "$TEST_SCRIPT"
```

При провале печатать только safe reason и завершать setup; не делать `cat` script.

## Python mock

Mock не должен ссылаться на shell-переменные production (`SSH_CONFIG`,
`AUTHORIZED_KEYS`) во время child execution: они не экспортированы. Сравнивай
runtime `target_cfg` с уже подставленными `$MOCK_HOME/.ssh/config` и
`$MOCK_HOME/.ssh/authorized_keys`, причём значения должны быть зафиксированы в
generated mock через quoted/unquoted heredoc без случайной ранней экспансии.
Никогда не подменяй target константой, не проверив фактический argv: иначе mock
перестаёт быть fail-closed.

## Acceptance этого hotfix

После исправления выполнить в tmux:

```bash
bash -n scripts/prod-github-access.sh scripts/tests/test-prod-github-access.sh
timeout 240 bash scripts/tests/test-prod-github-access.sh
```

В выводе должны появиться минимум `PASS: CLI01` и последний реально достигнутый
case; если suite падает до matrix, сначала исправить setup, не менять expected rc.
После успешного прохода вернуться к полному ТЗ 60 и не обновлять handoff до
honest 162-case acceptance.
