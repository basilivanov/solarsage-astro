# R12 — independent acceptance

Дата: 2026-07-15
Ветка: `infra/production-bootstrap`
Статус: **принято как infra slice; production launch не выполнялся**.

## Что принято

Закрыта проверяемая цепочка локального backup/restore/offsite:

- атомарный PostgreSQL custom-format dump и checksum;
- `pg_restore --list` до и после публикации;
- read-only verifier с exact canonical path/owner/mode/checksum contract;
- retention pair transaction с quarantine/recovery и stale-quarantine reporting;
- manual-only destructive restore с pre-restore backup, exact confirmation token, TTY boundary и service/timer checks;
- safe backup/restore lock handling: symlink/FIFO/directory/wrong owner/mode rejection, non-truncating open, dereferenced FD inode validation, sentinel preservation;
- Restic SFTP/S3-compatible config validation без secret output;
- distinct `--preflight` (empty repository allowed) и `--check` (at least one snapshot required);
- first empty repository bootstrap: preflight → first backup → tagged non-empty snapshot proof;
- weekly offsite maintenance and exact systemd timeout contracts;
- host-prepare routing: `--apply` uses preflight, explicit `--check` uses readiness;
- runbook order for stopping/starting backup timer and seeding first offsite snapshot;
- GRACE contracts/maps for new modules and test harnesses.

## Независимое evidence

Повторно выполнено без live/production/DB/Restic mutations:

```text
9 harnesses: PASS
15 production/helper/test files: bash -n PASS
4 systemd units: systemd-analyze verify PASS
invalid args: exact rc=2 for backup/verifier/restore/offsite/maintenance/host-prepare
git diff --check: PASS
production forbidden scan (rm -rf/eval/direct .env source): none
restore executable systemctl mutations: none
lock creation touch scan: none
test temp hygiene after full suite: empty
infra fingerprint: a4453fe97715d65db47a2bb52dde04bddb1bc4e768dfb8581feb5a983bea8f39
```

Ожидаемые retention warning/report строки в isolated harness — test fixtures, не ошибки acceptance.

## Что намеренно не сделано

- нет commit/push;
- нет запуска `solarsage-api`, `solarsage-sidecar`, `solarsage-frontend`;
- нет реального backup/restore/Restic init/prune/check;
- не выполнялся live host prepare/apply;
- не менялись Telegram Bot API settings;
- не читались и не печатались production secrets.

## Remaining operator inputs / blockers

До production readiness остаются внешние вводы и действия оператора:

1. Сделать GitHub repository private и подтвердить deploy-key boundaries.
2. Ротировать ранее раскрытые bot token, root password и LLM/API credentials; новые значения вне Git.
3. Выбрать offsite target и вручную разместить Restic password + SFTP key/known_hosts либо S3 credentials.
4. Проверить outbound `api.telegram.org:443` с production host — текущий live факт блокирует Telegram launch.
5. Настроить BotFather metadata/avatar/commands после ротации token.
6. По owner command выполнить только host preparation, затем first backup/readiness; application launch остаётся отдельной ручной командой.

Следующий infra slice: private GitHub access/readiness gates и pre-launch production readiness report. Он не должен запускать приложение.
