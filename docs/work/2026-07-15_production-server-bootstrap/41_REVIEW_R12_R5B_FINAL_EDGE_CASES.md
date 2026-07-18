# R12-R5B — финальные edge cases после повторного acceptance

Большой набор harnesses уже green. Перед принятием R12 закрыть только следующие конкретные дефекты.

## 1. Opened FD verification не может быть optional

В `scripts/prod-backup.sh` и `scripts/prod-db-restore.sh` сейчас блок выглядит как:

```bash
if [ -f "/proc/self/fd/N" ]; then
  # inode/owner/mode checks
fi
```

Если `/proc/self/fd/N` не regular target, проверки silently skip и код всё равно доходит до `flock`. Это нарушает lock contract.

Сделать fail-closed:

```bash
if [ ! -f "/proc/self/fd/N" ]; then
  echo "Error: opened lock FD is not a regular file." >&2
  exit 1
fi
```

Только после этого выполнять `stat -Lc`, inode comparison и owner/mode validation. Для `-L` обязательно сохранять `stat -Lc` — это уже исправило прежний procfs-symlink false hijack.

## 2. Atomic lock create должен реально использовать umask 077

Сейчас `noclobber` блок наследует глобальный `umask 027`, а затем делает `chmod 0600`. Итоговый mode в конце корректный, но creation window не соответствует R5 contract.

В обоих production scripts создавать новый lock в отдельном subshell с:

```bash
( umask 077; set -C; : > "$LOCKFILE" ) 2>/dev/null
```

или эквивалентом, который одновременно гарантирует `O_EXCL`/noclobber и mode 0600. PID можно не записывать; sentinel tests относятся к существующему файлу. После race/creation всё равно re-stat + opened-FD checks.

Добавить static assertion в lock harness, что new path mode 0600 и production lock creation block не содержит обычный `touch`.

## 3. Snapshot parser должен отвергать valid JSON object

`prod_offsite_snapshot_count` сейчас печатает `0` для любого valid JSON, который не является list. Контракт требует принимать только JSON array; `{}` не должен считаться валидным empty repository.

Python parser должен завершаться nonzero для non-list/non-array, а harness `test-prod-offsite-check.sh` добавить:

- `object_json`: `{"snapshots": []}` → rc 1 в `--preflight` и `--check`;
- обычный `[]`: `--preflight` rc 0, `--check` rc 1;
- one-element list: оба режима rc 0.

JSON metadata не печатать.

## 4. Runbook должен описывать первый snapshot явно

В `docs/PRODUCTION_RUNBOOK.md` после успешного `prod-host-prepare.sh --apply` сейчас сразу предлагается readiness `--check`, но empty initialized repository закономерно ещё не ready.

Добавить линейный шаг до `--check`:

```bash
sudo systemctl start solarsage-backup.service
# либо эквивалентно:
sudo -u astro -- /opt/solarsage-astro/scripts/prod-backup.sh
```

Эта команда создаёт первый local+offsite snapshot; затем выполняются:

```bash
sudo -u astro -- /opt/solarsage-astro/scripts/prod-offsite-check.sh --check
sudo /opt/solarsage-astro/scripts/prod-host-prepare.sh --check
```

Не предлагать временно переключать `OFFSITE_BACKUP_ENABLED`; не запускать application services автоматически.

## 5. Acceptance delta

После исправлений повторить только затронутые harnesses, затем весь R12-R5 набор. Очистить `/tmp/solarsage-*-test-*` после suite. Commit/push и реальные операции запрещены.
