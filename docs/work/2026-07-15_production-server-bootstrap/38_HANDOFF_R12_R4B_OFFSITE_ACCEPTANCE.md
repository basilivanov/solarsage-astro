# R12-R4B — handoff после зависания OpenCode: offsite acceptance

Статус: продолжить незавершённый R12 acceptance в новой чистой сессии кодера.

Обязательные исходные документы: `36_REVIEW_R12_R4_FINAL_RUNTIME_GAPS.md` и `37_REVIEW_R12_R4A_RESTORE_HARNESS_BLOCKER.md`.

Запрещено: production deploy, реальные backup/restore/offsite операции, изменение live services, commit, push, чтение или вывод secret values. Не трогать frozen/unrelated paths.

## Что уже подтверждено перед handoff

- `scripts/tests/test-prod-db-restore-safety.sh` после последней итерации кодера проходил целиком.
- В production restore и harness были добавлены restore-lock сценарии из R4A.
- Текущий блокер полного набора: `scripts/tests/test-prod-offsite-check.sh`.
- Независимый запуск:

```text
disabled: PASS
no_restic: PASS
enabled_empty_json: PASS
malformed_json: PASS
restic_nonzero: PASS
one_json_snapshot: FAIL, expected 0, got 1
```

## Точные дефекты offsite checker/harness

### 1. Top-level `local` в production script

В `scripts/prod-offsite-check.sh` сейчас используются:

```bash
local raw_json
local snapshot_count
```

Они находятся на верхнем уровне, не внутри функции. Bash завершается с `local: can only be used in a function` только в положительном пути, дошедшем до restic. Убрать `local` либо обернуть orchestration в функцию с корректным contract; минимальный безопасный фикс — обычные переменные `raw_json` и `snapshot_count`.

### 2. False-positive `stat` mock

Текущий mock `stat` в `scripts/tests/test-prod-offsite-check.sh` печатает сразу две строки (`astro:astro` и `600`) для каждого вызова независимо от requested format. Production checker вызывает `stat` отдельно для `%U:%G` и `%a`, поэтому mock должен печатать ровно одно соответствующее значение.

Сделать format- и path-aware поведение:

- `stat -c %U:%G <path>` → только owner;
- `stat -c %a <path>` → только mode;
- password/key/known_hosts по умолчанию `astro:astro 600`;
- `wrong_key_mode` меняет только `%a` для exact SSH-key path на `644`;
- неизвестный invocation должен завершаться nonzero, а не создавать ложный green result.

### 3. Негативные cases сейчас могут быть ложноположительными

`enabled_empty_json`, `malformed_json` и `restic_nonzero` могли завершаться раньше restic на неверной credential-проверке и всё равно считаться PASS, потому что тест проверяет только `rc != 0`.

Добавить marker вызова mock restic и обязательные утверждения:

- empty JSON: restic был вызван, rc checker nonzero;
- malformed JSON: restic был вызван, rc checker nonzero;
- restic nonzero: restic был вызван, rc checker nonzero;
- one valid snapshot: restic был вызван, rc 0, stdout содержит стабильный `OFFSITE READY`;
- wrong key mode: restic НЕ был вызван;
- disabled: restic НЕ был вызван, exact rc 3;
- missing restic: checker падает до invocation.

Проверить exact restic arguments хотя бы marker-логом: `--no-cache snapshots --json --latest 1`; JSON не печатать в production logs.

Добавить S3-compatible case: repository не начинается с `sftp:`, SSH key/known_hosts не заданы, один snapshot даёт rc 0. Это доказывает, что S3 не зависит от SSH credentials.

## Порядок продолжения

1. Исправить только offsite checker/harness по пунктам выше.
2. Запустить:

```bash
bash -n scripts/prod-offsite-check.sh
bash -n scripts/tests/test-prod-offsite-check.sh
timeout 90 scripts/tests/test-prod-offsite-check.sh
```

3. Затем заново выполнить весь shell/systemd acceptance из R12-R4:

```bash
bash -n scripts/lib/prod-env-loader.sh
bash -n scripts/prod-backup.sh
bash -n scripts/prod-backup-verify.sh
bash -n scripts/prod-db-restore.sh
bash -n scripts/prod-offsite-check.sh
bash -n scripts/prod-offsite-maintenance.sh
bash -n scripts/tests/test-prod-env-loader.sh
bash -n scripts/tests/test-prod-backup-verify.sh
bash -n scripts/tests/test-prod-backup-state-machine.sh
bash -n scripts/tests/test-prod-db-restore-safety.sh
bash -n scripts/tests/test-prod-offsite-check.sh
bash -n scripts/tests/test-prod-offsite-maintenance.sh
```

Запустить все шесть harnesses, затем:

- `systemd-analyze verify` для backup service/timer и maintenance service/timer;
- invalid args каждого production script должны иметь exact rc 2;
- `scripts/prod-infra-fingerprint.sh`;
- `git diff --check`;
- static scan: нет production `rm -rf`, `eval`, прямого `.env` source и executable `systemctl stop/start/restart` внутри restore;
- exact unit timeouts: backup `3h/2min`, maintenance `5h/2min`;
- удалить оставшиеся `/tmp/solarsage-*-test-*` и debug sandbox только после завершения тестов.

4. Не запускать полный Playwright вместо shell acceptance. После полного green R12 остановиться и дать детальный handoff с командами/результатами; архитектор выполнит независимый review и решит, нужен ли следующий correction pass.
