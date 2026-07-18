# R12-R5 — offsite bootstrap, post-upload proof и незакрытые safety contracts

## Статус

R12 пока **не принят**, несмотря на green текущих shell harnesses. Независимый архитектурный review нашёл runtime/bootstrap gaps и тестовые false-green сценарии.

Работать только в этом infra slice. Запрещены production deploy, SSH/live-host mutations, реальные DB backup/restore, реальные Restic operations, app service mutations, commit и push. Не трогать frozen/unrelated paths: `.grace/`, `artifacts/design/`, `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`, `grace.db`, `skills/`.

Полные Vitest/Pytest/Playwright пока не запускать: сначала закрыть этот safety acceptance.

## 1. P0: новый пустой Restic repository невозможно заполнить первым backup

Сейчас `scripts/prod-backup.sh` до `restic backup` вызывает:

```bash
prod-offsite-check.sh --check
```

После R12-R4 `--check` требует уже существующий snapshot. Поэтому после корректного `restic init` пустой repository не проходит pre-check, `restic backup` никогда не запускается, первый snapshot никогда не появляется.

Одновременно `prod-host-prepare.sh --apply` в финальной verification вызывает тот же readiness check и откатывает apply на пустом, но корректно инициализированном repository. Единственный обход сейчас — временно выключать offsite, применять host state, снова включать offsite и повторять apply. Это запрещённый operational «танец с бубном».

### Требуемая архитектура

Разделить два разных понятия:

1. **Preflight** — бинарник, credentials и repository доступны; валидный JSON array может быть пустым.
2. **Readiness** — всё из preflight плюс существует минимум один snapshot.

Добавить в `scripts/prod-offsite-check.sh` два exact read-only режима:

```text
scripts/prod-offsite-check.sh --preflight
scripts/prod-offsite-check.sh --check
```

Другие аргументы — exact rc `2`.

- disabled в обоих режимах: документированный rc `3`, restic не вызывается;
- `--preflight`: valid JSON array `[]` допустим и даёт `OFFSITE PREFLIGHT READY`/0; malformed JSON, uninitialized/unreachable repo или restic nonzero — rc 1;
- `--check`: valid JSON array length >= 1 даёт `OFFSITE READY`/0; `[]` — rc 1;
- raw JSON и snapshot metadata не выводить;
- repository/password/key values не выводить;
- S3-compatible не читает и не требует SSH key/known_hosts.

Это осознанное дополнение прежнего exact CLI: `--preflight` разрешён именно для безопасного bootstrap, не для обхода launch readiness.

### Общий helper вместо трёх расходящихся реализаций

Добавить `scripts/lib/prod-offsite-runtime.sh` с GRACE contract/map. Он не читает `.env` сам и не выполняет mutations.

Рекомендуемые публичные функции:

1. `prod_offsite_prepare`
   - вызывается после `prod_env_load`;
   - проверяет `restic` и обязательные env keys;
   - проверяет password file, а для SFTP key/known_hosts: real regular non-symlink, non-empty, readable, exact разрешённые owner/mode combinations;
   - для non-SFTP вообще не обращается к SSH variables;
   - экспортирует только `RESTIC_PASSWORD_FILE` и `RESTIC_REPOSITORY`;
   - формирует global indexed array `PROD_OFFSITE_RESTIC_ARGS`, без `eval` и string command execution;
   - не выполняет network call и не печатает values.
2. `prod_offsite_snapshot_count [tag]`
   - выполняет bounded `restic ... --no-cache snapshots [--tag TAG] --json --latest 1`;
   - JSON передаёт Python 3.12 через stdin/pipe или private temp file, но не через process argv и не в logs;
   - с `pipefail` сохраняет nonzero Restic/timeout/parser status;
   - принимает только JSON array и печатает вызывающему коду только целое count;
   - optional tag передаётся отдельным argv element, не интерполируется в shell command.

Использовать helper из checker, daily backup и maintenance, чтобы credential policy/SFTP argv не копировались в трёх местах. Обновить inventory, fingerprint и `bash -n` lists в `prod-host-prepare.sh` и `prod-infra-fingerprint.sh`.

## 2. P0: daily post-upload verification сейчас ложноположительная

Сейчас после `restic backup` выполняется обычный:

```bash
restic ... snapshots --tag "$TAG" --latest 1 >/dev/null
```

Restic может вернуть rc 0 и при пустом результате. Это прямо нарушает R12-R4.

Исправить `scripts/prod-backup.sh`:

1. После local commit и при enabled offsite вызвать `prod_offsite_prepare`. **Не** требовать существующий snapshot до upload.
2. Выполнить bounded `restic backup --no-cache --tag "$TAG" FINAL_DUMP FINAL_SHA`.
3. После success вызвать `prod_offsite_snapshot_count "$TAG"` и require integer `>= 1`.
4. Empty/malformed/nonzero tagged snapshot proof означает общий backup rc 1 и safe `EVENT: offsite_transfer_failed`.
5. Новый local dump/checksum при этом остаются byte-exact на месте.
6. Retention при failed upload/post-upload proof не запускается.
7. Не использовать generic `--check` как pre-upload gate: он по контракту readiness, а не config preflight.

Это должно позволять первому scheduled/manual backup создать первый snapshot сразу после `restic init`.

## 3. Host prepare: apply использует preflight, explicit check использует readiness

Обновить `scripts/prod-host-prepare.sh` без запуска реального backup:

- во время `--apply`, включая финальную verification после fingerprint, enabled offsite проверяется через `prod-offsite-check.sh --preflight`;
- явный `prod-host-prepare.sh --check` использует `prod-offsite-check.sh --check` и требует существующий snapshot;
- не передавать hidden env bypass flag;
- disabled offsite сохраняет текущую документированную warning semantics, но production launch checklist отдельно требует enabled/readiness;
- error messages не включают secret values или repository URL.

Проверка режима должна быть явным параметром `verify_host_state`, а не зависеть от неявной global variable.

## 4. Lock creation всё ещё не соответствует R4/R4A

В `prod-backup.sh` и `prod-db-restore.sh` новый lock всё ещё создаётся последовательностью `test -> touch -> chmod`. В R4A явно записано, что этого недостаточно. Комментарий «touch is safe» не является proof.

Для `backup.lock` и `restore.lock`:

- удалить `touch` creation path;
- если path отсутствует, создать атомарно с `umask 077` + Bash noclobber (`set -o noclobber`/`set -C`) в уже проверенном private `astro:astro 0700` directory;
- если atomic create проиграл race, не overwrite: перейти только к повторной validation появившегося path;
- после creation/race обязательно reject symlink/dangling symlink/FIFO/socket/directory/device;
- require regular file, exact `astro:astro`, exact mode `600`;
- открыть без truncate через `<>`;
- после open сравнить device+inode path и `/proc/self/fd/N`, а также stat opened fd owner/mode; mismatch — fatal до `flock`/business operation;
- затем nonblocking `flock`;
- существующий valid lock sentinel content остаётся byte-exact.

Не использовать `eval`. Допустим небольшой shared helper, только если FD lifetime и opened-inode verification доказаны тестами; иначе две короткие явные реализации лучше сложной абстракции.

### Недостающие backup lock tests

`test-prod-backup-state-machine.sh` сейчас проверяет только symlink. Добавить для `backup.lock`:

- FIFO под outer `timeout 2`: быстрый nonzero, не timeout;
- directory: быстрый nonzero;
- dangling symlink;
- wrong owner;
- wrong mode;
- valid existing regular sentinel не truncate;
- new lock exact real mode 600;
- negative cases не вызывают `pg_dump`/publish/retention.

Restore harness сохранить и адаптировать к atomic creation/opened-inode verification.

## 5. Restore state и runbook расходятся с safety boundary

### Runtime

`prod-db-restore.sh` разрешает app service state `deactivating`, хотя contract требует services **already inactive**. Во время deactivating ещё возможны активные процессы/записи.

- Для API/sidecar/frontend разрешать только `inactive` или `failed`.
- `active`, `activating`, `deactivating`, `reloading`, unknown/empty — fatal до pre-backup/SQL.
- Добавить harness case: app service `deactivating` не доходит до backup/psql/pg_restore.

### Runbook

`docs/PRODUCTION_RUNBOOK.md` сейчас в restore step 3 останавливает только app services. Исправить точный порядок:

1. stop API/sidecar/frontend **и `solarsage-backup.timer`** вручную;
2. проверить `solarsage-backup.service` как inactive/failed;
3. выполнить restore;
4. migrations/health;
5. вручную start app services и `solarsage-backup.timer`;
6. отдельное предупреждение: если restore aborted/cancelled/failed, оператор всё равно обязан вернуть backup timer.

Не документировать несуществующий `prod-db-restore.sh --latest`; canonical restore CLI остаётся с exact dump path.

## 6. Test quality / contract cleanup

1. `test-prod-offsite-check.sh`:
   - удалить дублированный блок `is_s3` + mock env loader;
   - S3 case должен **не задавать** SSH key/known_hosts вообще;
   - добавить `--preflight`: empty array success, malformed/nonzero fail, disabled exact 3;
   - `--check`: empty fail, one snapshot success;
   - assertions exact restic argv и отсутствие raw JSON в stdout/stderr.
2. Добавить isolated `test-prod-backup-offsite.sh` с mocks:
   - initially empty repository не блокирует upload; backup call затем tagged snapshot count 1 => success;
   - backup success + tagged `[]` => rc 1, new local pair preserved, old retention candidate preserved;
   - malformed/nonzero tagged proof => rc 1, local pair preserved;
   - SFTP args exact; S3 invocation не содержит `sftp.args`;
   - никакой сети/real DB.
3. `test-prod-offsite-maintenance.sh`:
   - доказать exact order: call 1 `forget ... --prune`, call 2 `check`;
   - обе команды имеют `--no-cache`;
   - helper credential/argv path используется, а не отдельная копия.
4. Добавить автоматический unit-template regression test (можно `test-prod-backup-units.sh`):
   - backup exact `TimeoutStartSec=3h`, `TimeoutStopSec=2min`;
   - maintenance exact `TimeoutStartSec=5h`, `TimeoutStopSec=2min`;
   - `systemd-analyze verify` four units.
5. `prod-backup-verify.sh`:
   - убрать unused `line_count`, `wc|xargs`;
   - убрать `awk` extraction: filename взять из уже проверенного regex/BASH_REMATCH или safe parameter parsing;
   - обновить dependency/header truthfully.
6. Новые helpers/tests получают полный GRACE header/module contract/module map.

## 7. Runbook: путь первого offsite snapshot без переключения flags

После исправления документировать один линейный путь:

1. operator размещает Restic password/key/known_hosts или S3 credentials;
2. operator один раз выполняет `restic init`;
3. `prod-host-prepare.sh --apply` проходит offsite `--preflight`, устанавливает/запускает timers, но не создаёт snapshot сам;
4. operator вручную запускает `solarsage-backup.service`/`prod-backup.sh` либо ждёт timer — первый backup создаёт первый snapshot даже в пустом repo;
5. `prod-offsite-check.sh --check` и `prod-host-prepare.sh --check` подтверждают readiness;
6. только после этого возможен отдельный ручной launch приложения по команде владельца.

Никакого временного `OFFSITE_BACKUP_ENABLED=false -> true` между apply/check.

## 8. Acceptance

Сначала syntax всех production/helper/test scripts. Затем выполнить без real operations:

```bash
scripts/tests/test-prod-env-loader.sh
scripts/tests/test-prod-backup-verify.sh
scripts/tests/test-prod-backup-state-machine.sh
scripts/tests/test-prod-backup-offsite.sh
scripts/tests/test-prod-db-restore-safety.sh
scripts/tests/test-prod-offsite-check.sh
scripts/tests/test-prod-offsite-maintenance.sh
scripts/tests/test-prod-backup-units.sh
```

Затем:

```bash
systemd-analyze verify \
  infra/systemd/solarsage-backup.service \
  infra/systemd/solarsage-backup.timer \
  infra/systemd/solarsage-backup-maintenance.service \
  infra/systemd/solarsage-backup-maintenance.timer

scripts/prod-infra-fingerprint.sh
git diff --check
```

Дополнительные exact assertions:

- invalid args rc2 для backup/verifier/restore/offsite checker/maintenance;
- checker `--preflight` и `--check` имеют различную empty-repo semantics;
- production scripts: zero `rm -rf`, zero `eval`, zero direct `.env` source;
- restore: zero executable `systemctl stop/start/restart`;
- lock creation paths: zero `touch`;
- no debug `/tmp/solarsage-*-test-*` dirs после suite;
- no real DB/Restic/systemd/live-host mutation.

После green остановиться и дать exact handoff: files, state transitions, tests + rc, operator inputs. Commit/push запрещены до независимого acceptance архитектором.
