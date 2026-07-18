# R12-R3 review — retention data safety, signal semantics и false-positive harnesses

## Статус

R12 не принят. Syntax/systemd checks и четыре harness-а зелёные, но минимум два harness-а проходят не по заявленной ветке, а production code всё ещё содержит runtime/data-loss defects.

Исправь только R12. Не менять принятые R3–R11 решения. Commit/push/merge, SSH/production, real backup/restore/Restic operations и app service mutations запрещены. Frozen paths не трогать.

## 1. Runtime blocker: maintenance содержит top-level `local` и теряет rc

В `scripts/prod-offsite-maintenance.sh`:

```bash
if ! "$check_script" --check; then
  local check_rc=$?
```

Обе части ошибочны:

- `local` находится вне функции и на runtime failure path даёт `local: can only be used in a function`;
- после `if ! command` значение `$?` уже инвертировано и равно `0`, а не исходному `3`/`1`.

Исправить без `!`:

```bash
if "$check_script" --check; then
  :
else
  check_rc=$?
  ...
fi
```

`check_rc` — обычная top-level variable либо весь flow вынести в `main()` и тогда использовать `local`. Disabled checker rc=3 должен дать maintenance warning + exit 0 без вызова `restic`; другой nonzero — maintenance exit 1 с безопасным generic message.

Добавь isolated `scripts/tests/test-prod-offsite-maintenance.sh`: disabled rc=3 => success/no Restic marker; checker rc=1 => failure/no Restic marker; enabled success => mocked forget и check вызваны ровно по одному разу с `--no-cache` и canonical retention. Никакой сети.

## 2. Signal traps сейчас глотают TERM/INT/HUP

В backup и restore установлено:

```bash
trap cleanup EXIT INT TERM HUP
```

Cleanup не делает `exit`, поэтому signal handler возвращается и shell может продолжить выполнение. Это воспроизводится обычным Bash: handler выполняется, затем печатается `CONTINUED_AFTER_TERM`, process rc=0.

Исправить во всех R12 flows, включая env producer-subshell:

- отдельный `trap cleanup EXIT`;
- отдельные signal handlers, которые снимают signal trap и завершают process с 128+signal (`130` INT, `143` TERM, `129` HUP);
- EXIT cleanup выполняется после signal exit;
- исходный non-signal exit status не заменять cleanup-командами;
- restore после TERM никогда не продолжает к confirmation/psql/pg_restore;
- backup после TERM до local commit удаляет только current temp/current timestamp partial pair и завершается nonzero.

Добавь реальный isolated signal case в backup state-machine harness: mocked command/`mv` даёт контролируемое окно, test отправляет TERM в test process, после wait требует nonzero и отсутствие partial final pair. Не использовать production paths.

## 3. Retention всё ещё может потерять backup

Текущая реализация небезопасна:

- один общий quarantine dir создаётся на весь retention pass;
- `dump_moved`/`sha_moved` выставляются, но нигде не используются для cleanup;
- signal между rename не восстанавливает pair;
- если второй rename failed, restore dump выполняется с `|| true`; если restore тоже failed, код позже делает `rm -rf "$QUARANTINE_DIR"` и удаляет единственную оставшуюся копию dump;
- `cleanup_quarantine` вообще не входит в EXIT trap;
- `rm -rf` против path внутри backup dir прямо запрещён R12-R2;
- проверяется возраст dump, но не checksum; новый checksum рядом со старым dump будет удалён;
- plain `rm -f q_dump q_sha` под `set -e` может оборвать script до controlled retention failure path.

Перепроектировать retention pair transaction:

1. Кандидат: dump и checksum оба regular/non-symlink, exact owner/mode, **оба** старше 14 days.
2. Orphan, wrong type, symlink, wrong owner/mode, pair с хотя бы одним новым member — report/ignore, без mutation.
3. На каждую pair отдельный private `mktemp -d` quarantine mode 0700.
4. Явное состояние current transaction: qdir, source paths, q paths, `dump_moved`, `sha_moved`, `delete_started`.
5. После первого rename и до второго любой failure/signal восстанавливает только реально перемещённый dump. Existing checksum никогда не overwrite placeholder-ом.
6. Если restore canonical name failed, hard nonzero и qdir с единственной копией сохраняется для manual recovery; никогда не удалять его generic cleanup-ом.
7. После обоих successful rename canonical pair отсутствует целиком. До начала deletion signal cleanup может вернуть обе entries.
8. После начала intended deletion не делать ложный automatic rollback claim. Остаток в qdir сохранить/report, script nonzero.
9. Удалять exact two regular q files через `rm -f --` с проверкой rc, затем exact empty qdir через `rmdir --`. Ноль `rm -rf` в production scripts.
10. После success очистить transaction state. Stale `.quarantine-*` только report; не угадывать recovery.
11. Current newly committed pair retention failure не удаляет.

## 4. Backup state-machine harness не тестирует обязательные failure windows

Текущий `test-prod-backup-state-machine.sh` не содержит mock второго publish `mv`, второго quarantine rename или signal. Он тестирует только pg_dump failure, existing timestamp и часть retention. Handoff утверждал больше, чем реально доказано.

Переписать harness так, чтобы он действительно проверял:

- second publish rename fails => script nonzero, final dump и checksum оба отсутствуют;
- TERM between first and second publish => nonzero, no final orphan;
- existing final pair byte-exact не overwrite;
- second quarantine rename fails => original dump+checksum canonical pair byte-exact восстановлена, script nonzero;
- если canonical restore rename also fails, qdir/data сохраняются, не удаляются;
- orphan checksum остаётся;
- wrong-mode/owner pair остаётся;
- dump old + checksum new остаётся;
- successful old complete pair удаляется;
- no stale temp/qdir after success.

Mock `mv` должен отличать publish от quarantine по source/destination и иметь deterministic counters/markers. Каждый case — отдельный fresh sandbox, иначе files из предыдущего case не маскируют результат.

Убрать hardcoded cleanup `db-20260715*`: harness должен быть date-independent. Получать созданный current path из exact `FINAL_DUMP:` output либо mock date per case.

## 5. Restore harness сейчас false-positive

Патч:

```bash
sed 's|SCRIPT_DIR/prod-backup-verify.sh|...|'
```

превращает production line в:

```bash
local verifier="$/tmp/.../prod-backup-verify.sh"
```

То же происходит с backup script. Поэтому plan/multiple-output cases могут падать из-за nonexistent `$/tmp/...`, не из-за проверяемой причины.

Mock systemctl также неверно разбирает реальные args `systemctl show -p LoadState --value service`: он ожидает `-p=LoadState`, поэтому часто проваливается в настоящий `/bin/systemctl`. Nonzero alone не доказывает нужную branch.

Переписать harness:

1. Скопировать restore script в sandbox и положить рядом exact filenames `prod-backup-verify.sh`, `prod-backup.sh`, `lib/prod-env-loader.sh`. Тогда `SCRIPT_DIR` естественно указывает на mocks; не sed-патчить substring с `$SCRIPT_DIR`.
2. Patch только canonical env/backup paths exact anchored replacements.
3. systemctl mock корректно обрабатывает раздельные `-p VALUE`, `--value`, service.
4. Каждый mock пишет stage marker. Test проверяет expected diagnostic/stage marker и отсутствие downstream markers (`psql`, `pg_restore`), а не только rc!=0.
5. Cases:
   - invalid plan вызывает verifier и fail;
   - valid plan вызывает verifier и success;
   - LoadState=not-found fails before target backup/SQL;
   - ActiveState=active fails;
   - multiple exact `FINAL_DUMP` lines reaches backup mock, then fails cardinality;
   - non-TTY exits 2 before env/service/backup/SQL;
   - wrong confirmation never invokes psql;
   - TERM before confirmation/downstream never invokes psql.

Все psql/pg_restore mocks fail closed and create markers if unexpectedly called. Никакого реального SQL.

## 6. Env loader: dynamic FD, producer fail-closed и caller state

Сейчас helper hardcodes FD 3 (`exec 3< ...`, затем closes it), поэтому source-only library может уничтожить уже открытый caller FD. Producer-subshell также не имеет `set -euo pipefail`; failure `chmod`/`cat` не гарантированно влияет на producer rc. Signal cleanup не exits.

Исправить:

- dynamic descriptor `exec {env_fd}< <(...)`, затем читать/закрывать именно `$env_fd`;
- producer `set -euo pipefail`, private temp, cleanup on EXIT, signal handlers exit nonzero;
- `mktemp`, `chmod`, Python, `cat` — каждый failure делает producer nonzero;
- assignments собирать в array и экспортировать только после successful `wait`;
- caller traps и pre-opened FDs не менять;
- parser failure не экспортирует partial variables.

Дополнить env harness: pre-open FD 3 с sentinel, `prod_env_load`, затем sentinel всё ещё читается; caller EXIT/TERM trap text до/после совпадает; simulated producer/cat failure nonzero/no partial export; signal producer leaves no temp. Не читать настоящий env.

## 7. Backup preflight/lock/cleanup corrections

- `restic` не должен быть unconditional dependency для `--local-only` или disabled offsite. Local backup/pre-restore остаётся работоспособным без Restic; checker validates Restic only when enabled.
- `backup.lock` и `restore.lock`: reject symlink/dangling symlink/unexpected type before opening; existing lock regular, owner `astro:astro`, mode 0600. Создание fail-closed, не следовать symlink и не truncate arbitrary target.
- checksum hash parsing убрать из `echo | awk` либо включить exact dependencies; проще `${raw_sha_out%% *}` + regex.
- production backup script не содержит `rm -rf`.
- cleanup не печатает «backup failed» на successful local commit/offsite failure incorrectly; local committed pair сохраняется.

Lock behavior добавить в isolated harness: symlink lock reject и target sentinel byte-exact не меняется.

## 8. Restore production corrections

Строка:

```bash
echo "Terminating active connections to database '$POSTGRES_DB'...pass"
```

содержит случайный `pass` и печатает env value, хотя contract требует не показывать env values. Заменить на generic `Terminating active connections to the production database...`.

Также:

- `local_backup_script`, `PRE_RESTORE_DUMP` объявить local внутри `run_restore`;
- safe signal exits из пункта 2;
- safe restore lock из пункта 7;
- failure после pre-backup сообщает только basename;
- module contract говорит services **already inactive**, не «script stops services»;
- no executable app service mutations.

## 9. Offsite credential/runtime correctness

`prod-offsite-check.sh`:

- contract output обновить: disabled => documented rc=3, не exit 0;
- password/key combination проверять pair-wise: `astro:astro` 0600/0640; `root:astro` только 0640. `[ -r ]` оставить, но error/contract должен совпадать;
- known_hosts owner сейчас вообще не проверяется. Разрешить только documented safe combinations (`astro:astro` 0600/0640/0644, `root:astro` 0640/0644, `root:root` 0644) + readable/non-empty;
- S3 не требует SSH files;
- failure messages не обязаны печатать operator credential paths; безопаснее назвать только credential kind;
- checker network timeout bounded, `--no-cache` сохранить.

Maintenance:

- исправить rc/local bug;
- `restic --no-cache check` использовать в canonical order;
- 300 seconds для real prune/check может быть слишком коротко; использовать documented large bounded timeout с `--foreground --kill-after` (например 2 hours), не infinite;
- add harness из пункта 1.

## 10. Host integration и runbook

`scripts/prod-host-prepare.sh` всё ещё не включает `scripts/lib/prod-env-loader.sh` в `SHELL_SCRIPTS`; добавить.

Runbook:

- direct manual backup line должна быть `sudo -u astro -- /opt/.../prod-backup.sh`, не bare script;
- Restic init commands действительно показать под `sudo -u astro -- env RESTIC_PASSWORD_FILE=... RESTIC_REPOSITORY=... restic ...`; текущий `export` не доказывает user boundary;
- root:astro only 0640;
- production launch remains manual only and requires offsite checker rc0;
- no real init/deploy now.

## 11. Acceptance

Обязательны:

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
bash -n scripts/tests/test-prod-offsite-maintenance.sh

scripts/tests/test-prod-env-loader.sh
scripts/tests/test-prod-backup-verify.sh
scripts/tests/test-prod-backup-state-machine.sh
scripts/tests/test-prod-db-restore-safety.sh
scripts/tests/test-prod-offsite-maintenance.sh

systemd-analyze verify \
  infra/systemd/solarsage-backup.service \
  infra/systemd/solarsage-backup.timer \
  infra/systemd/solarsage-backup-maintenance.service \
  infra/systemd/solarsage-backup-maintenance.timer

scripts/prod-infra-fingerprint.sh
git diff --check
```

Static/manual proof:

- no top-level `local` in production scripts;
- no `if ! command; rc=$?` when original rc is needed;
- no production `rm -rf` on backup/quarantine paths;
- no swallowed signal continuation;
- no hardcoded FD clobber in env loader;
- helper included in host `bash -n` inventory;
- tests assert exact branch markers, not only generic nonzero;
- exact invalid args remain exit 2.

Handoff must map every R12-R3 item to a concrete test. Не заявлять «second mv tested» или «service state tested», пока harness marker действительно это не доказывает.
