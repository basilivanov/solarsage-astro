# Review R9A-R5 — secret-safe harness and explicit env syntax rejection

Дата: 2026-07-15

Исполнитель: кодер в `tmux astro:0.0`, модель `cliproxy/gemini-3-flash-agent`.

Статус: финальная коррекция R9A; commit/push/live apply запрещены.

## Обязательные исправления

### 1. Явно отвергать shell-substitution syntax

Неиcполняющий parser уже не запускает `$(...)`, но текущий harness показал, что строка `MALICIOUS=$(touch ...)` принимается как literal и проверка может продолжиться. Для production env contract это запрещённый shell-like синтаксис.

До сохранения значения отклоняй (без вывода значения) минимум:

```text
$(
`...
${
$((
```

и shell control operators `;`, `&&`, `||`, `|`, `<`, `>` в unquoted values. Для текущего production env это обратно совместимо: реальные значения не содержат эти конструкции. Верни отдельный безопасный validation code/message без value.

`exit 0`, `return`, heredoc, `export`, строки без `=` и duplicate keys уже должны давать non-zero.

### 2. Никогда не раскрывать секреты в harness/handoff

Не копируй и не печатай настоящий `.env.production` в команды/вывод (`cat`, `grep`, `echo`, `print` значения). Для теста создай синтетический временный env только с redacted placeholders (`REDACTED_TOKEN`, `REDACTED_PROVIDER_KEY`, `REDACTED_PASSWORD`) и проверяй:

- malicious syntax -> non-zero;
- proof file не создан;
- настоящий production env не изменён.

В handoff перечисляй только имена файлов, rc и факт redaction. Если какое-либо реальное значение provider key уже попало в tmux/tool output, считай его скомпрометированным и явно сообщи архитектору, не повторяя значение.

### 3. Cleanup

Для временного файла dirty-gate добавь `trap`/cleanup, чтобы interruption не оставлял env/репозиторные данные в `/tmp`. Не меняй production runtime.

## Проверки

```bash
bash -n scripts/prod-infra-fingerprint.sh scripts/prod-host-prepare.sh scripts/prod-deploy.sh infra/production/solarsage-github-deploy
systemd-analyze verify infra/systemd/solarsage-db.service infra/systemd/solarsage-api.service infra/systemd/solarsage-sidecar.service infra/systemd/solarsage-frontend.service infra/systemd/solarsage-backup.service infra/systemd/solarsage-backup.timer
visudo -cf infra/production/solarsage-deploy.sudoers
POSTGRES_USER=dummy POSTGRES_PASSWORD=dummy POSTGRES_DB=dummy docker compose -f infra/production/docker-compose.yml config >/dev/null
git diff --check
```

Повтори только синтетические argument/fingerprint/marker/dirty/env harnesses. Не запускай root apply, deploy или application services; не commit/push.
