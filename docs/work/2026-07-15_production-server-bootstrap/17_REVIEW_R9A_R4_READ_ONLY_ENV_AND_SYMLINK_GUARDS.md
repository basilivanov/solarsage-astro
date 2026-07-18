# Review R9A-R4 — read-only environment contract and type-safe inventory

Дата: 2026-07-15

Исполнитель: кодер в `tmux astro:0.0`, модель `cliproxy/gemini-3-flash-agent`.

Статус: исправить до принятия R9A; commit/push/live apply запрещены.

## Почему нужна ещё одна итерация

R9A-R3 перенёс `source .env.production` из root-shell в `runuser -u astro`, что закрывает root privilege escalation, но `--check` всё ещё исполняет произвольные команды из пользовательского env-файла и может быть обманут строкой `exit 0`. Это нарушает read-only контракт host prepare и позволяет успешную проверку без проверки обязательных переменных. Нужен неисполняющий parser.

## Обязательные исправления

### 1. Сделать env contract validator неисполняющим

В `scripts/prod-host-prepare.sh` полностью убери `source "$ENV_FILE"` из env-контрактной проверки. Не запускай shell-код из `.env.production` ни от root, ни от `astro`.

Разрешённый формат production env-файла:

- пустые строки и строки, начинающиеся с `#` после ведущих пробелов — пропустить;
- assignment `KEY=VALUE`, где `KEY` соответствует `[A-Za-z_][A-Za-z0-9_]*`;
- split только по первому `=`;
- literal value без command substitution, arithmetic expansion, execution, `source`, `eval`, `exit`, `return` или shell expansion;
- поддержи безопасно текущий файл (в нём простые unquoted `KEY=value`, включая пустое значение и URL/токены с `=` внутри);
- если решишь поддержать outer single/double quotes, снимай только внешнюю пару и не интерпретируй содержимое как shell; malformed quote/дополнительный мусор — validation error;
- дублирующийся ключ, строка без `=`, `export KEY=...`, heredoc и любые другие строки — validation error;
- не печатай ни ключевые значения, ни строки файла.

Можно встроить короткий Python 3.12 parser в heredoc host script или сделать отдельный root-reviewed helper. Если helper добавляется в repository-owned infra, включи его в fingerprint inventory и документируй. Parser должен читать файл без записи и завершаться структурированным кодом ошибки; root получает только безопасное сообщение об имени общей проверки/required variable, не value.

Сохрани все текущие проверки: production APP_ENV/domain, DEV_MODE=false, secure cookie, non-empty critical secrets, normalized AstroGrace_Bot, active provider key, non-empty DATABASE_URL и reject sqlite.

Проверка `--check` после этого не должна иметь side effect от содержимого `.env.production`. В handoff приложи harness: временный env с `touch /tmp/...; exit 0` или `$(...)` должен вернуть non-zero, не создать файл и не привести к `ENV_VALID=1`.

### 2. Inventory должен отвергать symlink

Требование «regular file» означает `-f` и одновременно `! -L`. Для всех 14 inventory entries используй явную проверку, чтобы symlink на regular file не считался валидным. Иначе root может исполнить/установить файл вне clean checkout.

То же правило примени к критичным repository templates перед `bash -n`, `visudo`, `systemd-analyze` и compose config.

### 3. NUL-safe dirty gate должен проверять статус Git-команды

Текущий `while ... < <(git ls-files ... -z)` не передаёт status process substitution: при ошибке `git ls-files` цикл может выглядеть пустым и dirty gate пропустит ошибку.

Используй вариант, который одновременно сохраняет NUL safety и проверяет rc Git (например, временный root/astro-owned файл с `trap`, `git ls-files --others --exclude-standard -z > file`, затем `while read -d ''`, либо pipeline с проверкой `PIPESTATUS`). Применить в `prod-deploy.sh` и nested apply gate `prod-host-prepare.sh`. Не использовать `wc -l`, newline parsing или broad cleanup.

### 4. Cleanup и mode invariants

- Временные parser/compose/backup файлы удаляются и при success, и при preflight failure/interruption, с root-only mode.
- Не менять приложение, workflow, secrets или production server.
- Сохранить `0755` для `scripts/prod-infra-fingerprint.sh` и `scripts/prod-host-prepare.sh`, `0644` для `infra/systemd/solarsage-db.service`.
- Никаких start/restart/stop API/sidecar/frontend.

## Проверки перед handoff

```bash
bash -n scripts/prod-infra-fingerprint.sh scripts/prod-host-prepare.sh scripts/prod-deploy.sh infra/production/solarsage-github-deploy
systemd-analyze verify infra/systemd/solarsage-db.service infra/systemd/solarsage-api.service infra/systemd/solarsage-sidecar.service infra/systemd/solarsage-frontend.service infra/systemd/solarsage-backup.service infra/systemd/solarsage-backup.timer
visudo -cf infra/production/solarsage-deploy.sudoers
POSTGRES_USER=dummy POSTGRES_PASSWORD=dummy POSTGRES_DB=dummy docker compose -f infra/production/docker-compose.yml config >/dev/null
git diff --check
```

Повтори аргументный, fingerprint, marker-before-failure, NUL-safe dirty и malicious-env harnesses. Не делай commit/push/live apply; после handoff остановись.
