# R12-R2 review — atomicity, env-loader и реальная readiness-проверка

## Статус

R12 пока не принят. Исправь только перечисленные ниже дефекты, не расширяя scope и не меняя принятые R3–R11 решения.

Запрещено: commit/push/merge, SSH/production, реальный `pg_dump`, restore, Restic init/backup/forget/prune/check, запуск или остановка production app services. Не трогай frozen paths: `.grace/`, `artifacts/design/`, `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`, `grace.db`, `skills/`.

Все изменения кода выполняет кодер `cliproxy/gemini-3-flash-agent`. После исправлений нужен точный handoff с командами и exit codes, без утверждений, которые не подтверждены тестом.

## 1. `prod-env-loader.sh`: убрать `eval` и починить потерю exit code

Текущая реализация не соответствует R12-R1:

- в helper остались три исполняемых `eval "$old_trap"`;
- конструкция `if ! python3.12 ...; then local exit_code=$?` всегда сохраняет уже инвертированный status `0`, а не код Python parser;
- на текущем `.env.production` это воспроизводится как `Error: Environment validation failed with exit code 0`;
- helper временно перезаписывает traps вызывающего shell и пытается восстанавливать их через `eval`;
- cleanup function, объявленная внутри функции, остаётся в namespace вызывающего shell.

Исправить архитектурно, без строкового исполнения trap:

1. `prod_env_load FILE DOMAIN` остаётся source-only функцией.
2. Python parser и приватный temp mode 0600 выполняются внутри отдельного producer-subshell/process substitution. Cleanup temp устанавливается и снимается только внутри этого subshell; traps вызывающего shell не изменяются.
3. Producer сначала полностью валидирует файл и записывает NUL-records во временный файл, затем отдаёт их в pipe. При ошибке parser не должен отдавать частичный набор assignments.
4. В вызывающей функции сначала собрать все NUL-records в локальный array, затем дождаться producer PID и проверить его настоящий exit status. Только после успешного `wait` экспортировать assignments. Нельзя экспортировать частичный результат до подтверждённого успеха producer.
5. Не использовать `eval`, `source` данных env, command substitution с NUL bytes или печать значений.
6. На failure вывести только безопасное сообщение по реальному parser exit code; temp удалить на success/failure/INT/TERM/HUP.
7. Helper сам проверяет env file: regular, final path не symlink, owner exact `astro:astro`, mode exact `0600` или `0640`. Тогда backup/restore/offsite используют один и тот же contract.
8. Проверять наличие нужных helper dependencies безопасно; не менять `PATH` из env до завершения всех проверок.

Рекомендуемый безопасный shape: открыть FD на process substitution, сразу сохранить `$!`, прочитать NUL records в array, закрыть FD, выполнить `wait "$producer_pid"` через обычный `if wait ...; then ... else rc=$?; ... fi`, затем экспортировать array. Не использовать `if ! wait ...; rc=$?` по той же причине инверсии status.

## 2. Env contract должен поддерживать S3 без фиктивных SSH-файлов

Сейчас loader требует `OFFSITE_RESTIC_SSH_KEY` и `OFFSITE_RESTIC_KNOWN_HOSTS` при любом `OFFSITE_BACKUP_ENABLED=true`, поэтому заявленный S3-compatible режим неработоспособен.

Правила:

- при enabled всегда обязательны непустые `OFFSITE_RESTIC_REPOSITORY` и `OFFSITE_RESTIC_PASSWORD_FILE`;
- `OFFSITE_RESTIC_SSH_KEY` и `OFFSITE_RESTIC_KNOWN_HOSTS` обязательны только если repository начинается с `sftp:`;
- whitespace/control/leading `-` проверки применять к реально используемым path values;
- для S3 не требовать dummy SSH values;
- `OFFSITE_RESTIC_TAG`, если задан, передаётся как один argv и не интерпретируется shell.

Добавь изолированный harness `scripts/tests/test-prod-env-loader.sh` с fake, non-secret env values. Минимальные cases: valid production env; duplicate key; substitution; control/shell operator; malformed quote; S3 enabled without SSH keys passes; SFTP without key/known_hosts fails; SFTP complete passes; parser failure не экспортирует ни одной переменной; реальный nonzero parser code не превращается в zero. Harness не читает настоящий env.

## 3. Backup publish: закрыть signal/failure windows

Текущий cleanup устанавливается только после обоих `mktemp`, а после первого final `mv` не удаляет current final pair. Возможны:

- temp dump остаётся, если второй `mktemp`/`chmod` упал до установки trap;
- одиночный final dump остаётся при INT/TERM/HUP или shell failure между publish dump и publish checksum;
- повторный запуск в ту же секунду может перезаписать уже существующую good pair из-за `mv -fT`.

Исправить:

1. После lock и до первого temp creation инициализировать все temp/final path variables пустыми и поставить cleanup.
2. Cleanup до `LOCAL_BACKUP_COMMITTED=1` удаляет только непустые temp paths и только exact current timestamp final dump/checksum. Никакие старые файлы не трогать.
3. Обработать `EXIT`, `INT`, `TERM`, `HUP`; сохранить исходный exit status.
4. Перед dump fail closed, если exact final dump или checksum уже существует либо является dangling symlink. Не перезаписывать существующую pair.
5. Любой failure/signal между двумя publish operations оставляет либо обе final files, либо ни одной.
6. После post-publish checksum и `pg_restore --list` только тогда выставить commit flag.
7. Убрать незафиксированные external dependencies из логики checksum (`cat | cut`) либо добавить exact preflight dependencies; предпочтительнее получить hash безопасным `read`, проверить `^[0-9a-f]{64}$` и сформировать canonical checksum line через `printf`.
8. GRACE contract должен совпадать с фактическим lock `/var/backups/solarsage/backup.lock`, UMask и state machine; убрать лишний/ошибочный `END_MODULE_MAP`.

## 4. Offsite network operations должны быть bounded и fail-closed

В daily backup `restic backup` и последующий `restic snapshots` сейчас без `timeout`; snapshots также без `--no-cache`.

Исправить:

- bounded timeout с `--foreground` и разумным большим пределом для upload, плюс `--kill-after`; короткий 30-second limit для самого upload запрещён;
- `restic --no-cache backup ...` и `restic --no-cache snapshots ...`;
- snapshot check минимум ограничить exact tag `OFFSITE_RESTIC_TAG`, чтобы unrelated old snapshot не считался доказательством текущего production backup;
- local committed pair при любом offsite failure сохраняется, script nonzero, retention не запускается;
- required `timeout`/`restic` behavior отражён в contract/preflight;
- repository/password/key values никогда не печатаются.

## 5. Retention: не удалять/портить orphan или непроверенную pair

Текущая схема с двумя заранее созданными quarantine-файлами опасна: если второй `mv` падает, recovery может переместить пустой placeholder поверх существующего checksum. Также текущий код удаляет orphan checksum, хотя contract разрешает удалять только complete old pairs, и может удалить pair по возрасту только dump, не checksum.

Исправить:

1. Кандидат на retention — только complete dump+checksum pair, обе final regular non-symlink, owner `astro:astro`, mode `0600`, обе старше 14 days.
2. Wrong owner/mode, symlink, dangling symlink, unexpected type и orphan любого направления только report + leave untouched. Не удалять orphan checksum.
3. Использовать private quarantine directory mode 0700, а не pre-created placeholder files.
4. Явно отслеживать `dump_moved`/`sha_moved`. Если второй rename не удался, восстанавливать только реально перемещённый dump и никогда не overwrite существующий checksum пустым файлом.
5. До завершения обоих rename signal/failure cleanup пытается вернуть exact moved entry. После обоих rename canonical pair отсутствует целиком; удалить оба файла внутри quarantine и затем пустой directory.
6. Stale quarantine state не считать normal success: безопасно report, не угадывать исходные имена без достаточной информации.
7. Retention failure nonzero, current committed backup pair остаётся.

Добавь небольшой isolated backup state-machine harness либо вынеси publish/retention helpers в sourceable testable functions. Обязательные proof cases: второй publish `mv` падает — final orphan отсутствует; existing final pair не перезаписывается; второй quarantine rename падает — исходная pair восстановлена byte-exact; orphan checksum остаётся нетронутым; wrong-mode pair не удаляется. Все paths только в temp sandbox, все DB/Restic commands mocked, реальный backup запрещён.

## 6. Verifier и его harness сейчас дают ложноположительный bad-digest test

`scripts/tests/test-prod-backup-verify.sh` mock `sha256sum` не вычисляет digest. Case «bad digest» добавляет лишний текст и отклоняется regex до checksum check; это не тест digest mismatch. Owner case отсутствует.

Исправить verifier:

- CLI parse должен происходить до backup-dir/runtime checks, чтобы unsupported/missing args стабильно давали exit 2 даже если `/var/backups/solarsage` отсутствует;
- принимать только exact direct canonical path `$BACKUP_DIR/$basename`, а не путь через symlinked parent/subdirectory/`..`;
- checksum — exact одна физическая строка canonical формата; extra blank/second line reject; не нормализовать содержимое через `xargs`;
- filename в checksum exact selected basename;
- owner/mode/type checks для dump и checksum остаются hard failures;
- latest выбирает newest actually valid pair.

Исправить harness:

- использовать реальный system `sha256sum`; mock нужен только для `pg_restore --list`;
- valid pair checksum генерировать реальным digest;
- bad digest оставить syntactically valid 64-lowercase-hex line, но digest должен не совпадать;
- добавить wrong dump owner и wrong checksum owner через узкий fake `stat` wrapper/sentinel, который все остальные calls делегирует real `stat`;
- отдельно wrong dump mode и checksum mode;
- extra checksum line/blank line;
- input path через parent symlink/direct symlink;
- missing checksum, empty, invalid basename, malicious checksum filename, valid pair, latest-valid.

Test harness не должен патчить production files и не должен обращаться к `/var/backups/solarsage`.

## 7. Restore: `--plan`, service existence и exact pre-backup output

Текущий `--plan` не вызывает verifier, хотя комментарий утверждает обратное. `systemctl show ActiveState` может вернуть `inactive` для nonexistent unit, поэтому missing unit сейчас может быть принят. Backup-dir owner/mode и exact output cardinality также не доказаны.

Исправить:

1. `--plan` сначала обязательно вызывает verifier; при failure ничего не печатает как valid plan. После success выводит только проверенный canonical direct path/basename и ordered instructions.
2. Для каждого app unit получить и проверить `LoadState=loaded`, затем `ActiveState`. `not-found`, `masked`, пустой/unknown query — fatal. Разрешены только exact inactive/failed/deactivating states после loaded check; active/activating fatal.
3. Backup dir перед lock exact real non-symlink `astro:astro:0700`.
4. Output pre-backup разобрать как NUL-safe/line-safe array: должна существовать ровно одна строка `FINAL_DUMP: /var/backups/solarsage/db-...dump`. Zero или multiple matches — fatal. Не использовать `echo | grep | cut` как доказательство cardinality.
5. До destructive SQL показать selected basename и verified byte size, затем exact token prompt. CLI confirm flag + interactive token остаются двумя отдельными barriers.
6. Добавить `psql -v ON_ERROR_STOP=1`; target DB остаётся через `-v target_db=...` и `:'target_db'`.
7. Для `pg_restore` не использовать arbitrary 600-second cutoff. Использовать явно документированный большой bounded timeout (например 2 hours с `--foreground --kill-after`) либо обосновать другой production-safe предел.
8. Любая ошибка после pre-backup печатает только basename pre-restore dump; automatic rollback не заявлять.
9. Убрать unused `REPO_ROOT`, `CONFIRM_FLAG`, duplicate `END_BLOCK`, обновить contract lock path.
10. Никаких исполняемых `systemctl stop/start/restart`; plan может печатать manual operator commands как текст.

Добавь non-destructive harness для plan/service-state/output parsing с mocked verifier/systemctl/backup, без SQL и без реального restore. Минимум: plan invalid dump fails; nonexistent unit fails even when ActiveState looks inactive; multiple `FINAL_DUMP` lines fail; non-TTY restore exit 2 before writes.

## 8. Offsite credential permissions и readiness semantics

Исправить combinations:

- password/private key: `astro:astro` mode 0600 или 0640, либо `root:astro` mode 0640; `root:astro:0600` запрещён как unreadable для `astro`; дополнительно `[ -r FILE ]` as `astro`;
- known_hosts: regular non-symlink, owner/mode explicit; разрешить документированный safe набор (`astro:astro:0600|0640|0644`, `root:astro:0640|0644`, `root:root:0644`) и require readable;
- all required files non-empty;
- SFTP-only checks не выполняются для S3;
- `prod-offsite-check.sh --check` при disabled возвращает отдельный documented non-readiness code `3` после safe warning. Daily local backup не вызывает checker в disabled mode, поэтому local backup остаётся success. Maintenance при disabled может остаться warning/no mutation, но это не readiness proof.

`restic snapshots` в checker и maintenance должен использовать `--no-cache`; все network commands bounded. Не печатать repository URL или credential paths при failure, если путь может содержать operator-sensitive naming.

## 9. Host/systemd integration

В `prod-host-prepare.sh`:

- добавить `scripts/lib/prod-env-loader.sh` в `SHELL_SCRIPTS` для `bash -n`;
- loader failure при чтении offsite flag — verification error, а не silent fallback в `false`;
- при enabled checker запускается exact как `astro`; checker nonzero — verification error;
- при disabled остаётся явный warning в host preparation, но production launch checklist отдельно требует checker exit 0;
- apply должен enable **и start** оба timer: `solarsage-backup.timer` и `solarsage-backup-maintenance.timer`;
- final verify проверяет оба timer как enabled и active;
- app services не стартовать/restart; accepted legacy cleanup R11 не переписывать;
- inventory, installed units и fingerprint остаются согласованными.

Systemd units повторно проверить вместе одной командой. Не добавлять writable paths кроме backup dir/private tmp; `UMask=0077`, journal, `ProtectHome`, `ProtectSystem`, `NoNewPrivileges`, `PrivateTmp` сохранить.

## 10. Runbook corrections

Исправить без публикации secrets:

- direct scripts запускать как `astro` (`sudo -u astro -- ...`) либо через systemd service; не предлагать root direct execution;
- password/key combinations описать точно: `root:astro` только 0640, не 0600;
- S3 path не требует SSH key/known_hosts; SFTP требует;
- one-time Restic init показать как explicit operator command under `astro` с `RESTIC_PASSWORD_FILE`, repository и при SFTP exact `-o sftp.args=...`; никаких `source .env.production`;
- production launch checklist перед deploy требует `sudo -u astro -- scripts/prod-offsite-check.sh --check` с exit 0;
- RPO 24h отделить от RTO: указать target/assumption и требование измерить его restore drill на non-production; не выдавать непроверенный RTO за гарантию;
- restore из старой схемы требует matching code commit и owner-approved pinned deployment; schema/data rollback не равен code rollback;
- no blanket cache invalidation оставить.

## 11. Acceptance evidence

Выполнить только безопасные проверки:

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
# если restore harness создан:
bash -n scripts/tests/test-prod-db-restore-safety.sh

systemd-analyze verify \
  infra/systemd/solarsage-backup.service \
  infra/systemd/solarsage-backup.timer \
  infra/systemd/solarsage-backup-maintenance.service \
  infra/systemd/solarsage-backup-maintenance.timer

scripts/tests/test-prod-env-loader.sh
scripts/tests/test-prod-backup-verify.sh
scripts/tests/test-prod-backup-state-machine.sh
# если создан:
scripts/tests/test-prod-db-restore-safety.sh

scripts/prod-infra-fingerprint.sh
git diff --check
```

Invalid-arg evidence under user `astro`:

- `prod-backup.sh --bad` => 2;
- `prod-backup-verify.sh` and `--bad` => 2, даже если canonical backup dir отсутствует;
- `prod-db-restore.sh` and incomplete restore => 2;
- `prod-offsite-check.sh` without exact `--check` => 2;
- `prod-offsite-maintenance.sh` without exact `--run` => 2.

Static proof:

- zero executable `eval` in R12 production scripts/helper;
- zero `source "$ENV_FILE"`/`.env.production`;
- zero `rm -rf` against backup paths;
- zero executable app `systemctl stop/start/restart` in backup/offsite/restore (manual plan strings are allowed and must be identified as strings);
- no secret values in output/log messages.

Do not report R12 complete until all mandatory harnesses pass and every item above is mapped to an exact file/line or test case.
