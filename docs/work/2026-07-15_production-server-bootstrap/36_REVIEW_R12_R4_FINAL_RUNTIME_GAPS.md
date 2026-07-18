# R12-R4 review — final runtime gaps before acceptance

## Статус

R12 почти принят: все пять isolated harnesses сейчас проходят и основные R12-R3 дефекты исправлены. Остались конкретные runtime gaps ниже. Исправить только их; не переписывать принятые части.

Запрещены commit/push/SSH/production/real backup/restore/Restic/app service mutations. Frozen paths не трогать.

## 1. Systemd сейчас убьёт long backup/maintenance через 90 секунд

Локальный systemd подтверждает `DefaultTimeoutStartSec=90s`. Скрипты допускают Restic operation до 2 часов, а maintenance выполняет две такие операции последовательно. В обоих oneshot units `TimeoutStartSec` отсутствует, поэтому собственные timeout contracts фактически не работают.

Исправить:

- `infra/systemd/solarsage-backup.service`: explicit `TimeoutStartSec=3h`, `TimeoutStopSec=2min`;
- `infra/systemd/solarsage-backup-maintenance.service`: explicit `TimeoutStartSec=5h`, `TimeoutStopSec=2min`;
- module contracts/invariants объясняют пределы;
- сохранить hardening/UMask/ReadWritePaths;
- `systemd-analyze verify` всех четырёх units;
- добавить static assertion в safe harness либо отдельный grep-based unit-template test, что exact timeout values присутствуют.

## 2. Restore должен исключить автоматический backup во время pg_restore

Сейчас operator останавливает только api/sidecar/frontend. После pre-restore backup `backup.lock` освобождается, и `solarsage-backup.timer` может запустить новый dump во время destructive restore.

Исправить restore boundary без automatic service mutation:

1. До pre-restore backup require `solarsage-backup.timer` loaded и inactive. Active/activating timer — fatal с инструкцией остановить вручную.
2. Require `solarsage-backup.service` loaded и inactive/failed. Active/activating/deactivating service — fatal; restore не ждёт и не останавливает его.
3. Проверка идёт до pre-restore backup/SQL.
4. Restore script по-прежнему не вызывает executable `systemctl stop/start/restart`.
5. Runbook restore order:
   - stop app services **и** `solarsage-backup.timer` manually;
   - verify `solarsage-backup.service` is inactive;
   - run restore;
   - после migrations/health manually start app services и `solarsage-backup.timer`;
   - если restore aborted, operator всё равно обязан вернуть timer.
6. `--plan` печатает тот же порядок.

Дополнить restore harness markers: active backup timer fails before pre-backup; active backup service fails before pre-backup; inactive timer/service позволяет дойти до existing multiple-output/confirmation cases.

## 3. Lock paths: reject FIFO/directory/device и не truncate existing lock

Backup/restore проверяют только `-L`, затем используют `exec N>LOCKFILE`. Existing FIFO может заблокировать process на open; unexpected regular ownership/mode не проверяются; `>` truncate не нужен.

Для `backup.lock` и `restore.lock`:

- symlink/dangling symlink — fatal;
- если path существует, require regular file, owner `astro:astro`, mode `0600`;
- FIFO/socket/directory/device — fatal **до open**, без hang;
- если отсутствует, создать exact regular file mode 0600 under already verified backup dir, затем re-stat exact owner/mode;
- открыть without truncation (`exec N<>"$lockfile"`) и взять nonblocking `flock`;
- не следовать symlink;
- helper допустим в `scripts/lib/`, если это уменьшает безопасное дублирование; тогда GRACE/inventory/fingerprint/bash-n обязательны.

Harness:

- existing symlink sentinel unchanged;
- FIFO lock under outer `timeout 2` fails quickly, не timeout/hang;
- directory lock fails quickly;
- wrong owner/mode (narrow stat mock) fails;
- valid existing regular lock не truncate (sentinel contents byte-exact) и flock succeeds.

## 4. Retention EXIT recovery не должен удалять q-copy при занятом destination

В `retention_cleanup` rollback выполняется только при `[ ! -f "$ret_dump_file" ]`. Если `ret_dump_moved=1`, но canonical destination неожиданно появился, rollback пропускается, `rollback_failed` остаётся 0, затем q-copy удаляется. Это data-loss window.

Исправить:

- для каждого moved member: если canonical destination уже существует **или symlink**, считать rollback conflict/failure и сохранить qdir/q-copy; ничего не overwrite и не delete;
- только absent destination разрешает exact q->canonical rename;
- при conflict safe error + nonzero + qdir preserved for manual recovery;
- cleanup не удаляет unknown files;
- убрать unused `exit_code=1`;
- при старте retention перечислить `.quarantine-*`: stale directory/symlink/unexpected type только report warning, не mutate;
- после successful pair transaction qdir отсутствует.

Дополнить backup state-machine harness: во время rollback создать canonical conflict, затем доказать, что q-copy preserved byte-exact и script nonzero; stale qdir reported/untouched.

## 5. Offsite readiness должна доказать наличие snapshot, а не только rc команды

`restic snapshots --latest 1` может успешно подключиться к пустому repository. Production launch readiness должна требовать минимум один snapshot.

Исправить `prod-offsite-check.sh --check`:

- bounded `restic ... snapshots --json --latest 1`;
- stdout не логировать; pipe/capture безопасно разобрать Python parser;
- require valid JSON array с length >= 1;
- empty array => non-ready exit 1 с generic message;
- network/restic/parser failure => exit 1;
- enabled + at least one snapshot => `OFFSITE READY`/0;
- disabled остаётся rc=3;
- contract output line обновить (сейчас ошибочно говорит disabled exit 0).

В daily backup post-upload snapshot check также require non-empty tagged JSON result, хотя `restic backup` success остаётся основным proof. Не печатать snapshot metadata.

Добавить `scripts/tests/test-prod-offsite-check.sh`: disabled=3/no restic; enabled empty JSON fails; malformed JSON fails; restic nonzero fails; one JSON snapshot succeeds; S3 не требует SSH files; credential owner/mode combinations проверяются через narrow stat mock. Никакой сети.

Maintenance harness дополнить assertions: first Restic call действительно `forget` с `--keep-daily 14 --keep-weekly 8 --keep-monthly 12 --keep-yearly 3 --prune`; second действительно `check`; обе содержат `--no-cache`.

## 6. Contracts/GRACE/test hygiene

- `prod-offsite-check.sh` output contract: disabled rc=3;
- restore invariant: services/timer must already be inactive, script их не «stops»;
- backup header не заявляет unconditional Restic dependency;
- убрать оставшийся `awk` из second temp hash parsing либо объявить dependency; предпочтительно `${output%% *}` + regex;
- все новые R12 test scripts должны иметь `AI_HEADER`, `START_MODULE_CONTRACT`, `START_MODULE_MAP` (сейчас у test harnesses только header);
- test-only `rm -rf` допустим только для unique `/tmp/solarsage-*-test-*` sandbox, production scripts — zero;
- очистить созданные во время debugging `/tmp/solarsage-*-test-*` после завершения tests.

## 7. Acceptance

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

scripts/tests/test-prod-env-loader.sh
scripts/tests/test-prod-backup-verify.sh
scripts/tests/test-prod-backup-state-machine.sh
scripts/tests/test-prod-db-restore-safety.sh
scripts/tests/test-prod-offsite-check.sh
scripts/tests/test-prod-offsite-maintenance.sh

systemd-analyze verify \
  infra/systemd/solarsage-backup.service \
  infra/systemd/solarsage-backup.timer \
  infra/systemd/solarsage-backup-maintenance.service \
  infra/systemd/solarsage-backup-maintenance.timer

scripts/prod-infra-fingerprint.sh
git diff --check
```

Дополнительно:

- invalid args exact rc2;
- production scripts zero `rm -rf`, zero executable app/backup timer stop/start/restart in restore;
- unit exact timeouts visible in templates;
- no debug temp dirs remain;
- no real DB/Restic/systemd/production mutation.

После этого handoff должен отдельно перечислить: local backup readiness, restore concurrency boundary, offsite readiness semantics и всё ещё необходимые operator inputs. Commit/push запрещены.
