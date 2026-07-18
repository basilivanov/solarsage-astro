# R12-R5A — точная причина opened-inode false hijack

Текущий blocker `Error: Restore lock file hijack detected during open` находится одновременно в production implementation и mock ordering.

## Production defect

`/proc/self/fd/N` является symlink. Текущий код использует:

```bash
stat -c "%d:%i" /proc/self/fd/9
stat -c "%U:%G" /proc/self/fd/9
stat -c "%a" /proc/self/fd/9
```

Без `-L` GNU `stat` возвращает metadata самого procfs symlink, а не открытого lock-файла. Поэтому device+inode никогда не совпадут с canonical lock path, а owner/mode тоже относятся не к открытому файлу.

Локально подтверждено:

```text
path      = device:inode regular file
fd-no-L   = другой device:inode symbolic link
fd-L      = тот же device:inode regular file
```

Исправить для обоих FD (`backup` и `restore`):

```bash
path_inode=$(stat -c "%d:%i" "$lockfile")
fd_inode=$(stat -Lc "%d:%i" "/proc/self/fd/$fd")
fd_owner=$(stat -Lc "%U:%G" "/proc/self/fd/$fd")
fd_mode=$(stat -Lc "%a" "/proc/self/fd/$fd")
```

Также require `test -f /proc/self/fd/N`/dereferenced regular target before flock. Сравнение path inode и dereferenced FD inode остаётся mandatory.

## Harness defect

Mock `stat` в restore harness сейчас обрабатывает generic `format+target` и делает `exec real_stat` раньше отдельной ветки `/proc/self/fd/`, поэтому нижняя ветка недостижима.

Исправить parser mock так, чтобы:

- он понимал `-L` и `-c`;
- `%d:%i` для sandbox lock path и `/proc/self/fd/N` делегировался реальному `/usr/bin/stat` с тем же dereference behavior, а не возвращал выдуманную константу;
- narrow owner/mode overrides применялись только к canonical sandbox lock path для wrong-owner/wrong-mode cases;
- owner/mode opened FD проверялись через real `stat -L`, поэтому positive path доказывает реальный target;
- generic fallback не делает последующую branch недостижимой.

После исправления сначала выполнить только:

```bash
bash -n scripts/prod-backup.sh
bash -n scripts/prod-db-restore.sh
bash -n scripts/tests/test-prod-backup-state-machine.sh
bash -n scripts/tests/test-prod-db-restore-safety.sh
timeout 120 scripts/tests/test-prod-backup-state-machine.sh
timeout 120 scripts/tests/test-prod-db-restore-safety.sh
```

После green продолжить полный acceptance из `39_REVIEW_R12_R5_BOOTSTRAP_AND_FALSE_GREEN_GAPS.md`. Все прежние запреты сохраняются.
