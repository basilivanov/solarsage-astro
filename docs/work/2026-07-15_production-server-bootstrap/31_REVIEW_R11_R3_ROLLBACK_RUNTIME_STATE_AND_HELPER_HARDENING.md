# R11-R3 review — rollback runtime state and helper hardening

## Статус

R11-R2 почти принят, но остаются runtime-safety дефекты. Исправь только их. Commit/push/production запрещены.

## 1. После rollback нужно восстановить не только bytes, но и runtime state

Сейчас `on_transaction_exit` вызывает `prod_tx_rollback`, но:

- cert flow не делает `nginx -t` + reload восстановленного config;
- host flow не делает `systemctl daemon-reload`, Nginx reload и Fail2ban restart после restore.

Из-за этого после ошибки файлы старые, а running process может продолжать candidate config.

Исправление:

- cert rollback success -> `/usr/sbin/nginx -t`, затем `systemctl reload nginx.service`;
- host rollback success -> `systemctl daemon-reload`; затем `nginx -t` + reload; затем `fail2ban-client -d` + restart;
- validation failure только логируется, primary exit code сохраняется;
- app services не трогать;
- DB не откатывать/рестартовать в rollback;
- вынести post-restore actions в named function каждого caller (`post_cert_restore`, `post_host_restore`).

Если `prod_tx_rollback` неуспешен, не удалять snapshot directory автоматически: вывести безопасный path к root-only recovery snapshot и primary error. Cleanup выполнять только при успешном rollback или committed success.

## 2. Shared helper: двухфазный rollback

До первой mutation внутри `prod_tx_rollback` пройти **все** registered paths и проверить:

- current candidate missing/regular/symlink;
- parent directory существует, real directory, не symlink;
- captured type/metadata/backup присутствуют и валидны;
- regular backup readable;
- key соответствует `^[A-Za-z0-9_.-]+$`.

Если любой path плох — return nonzero до изменения первого path. Нельзя частично восстановить половину paths и потом обнаружить directory.

## 3. Shared helper: убрать `mktemp -u` и silent metadata failures

- `mktemp -u` запрещён;
- для atomic symlink restore создать mode-0700 temp directory в target parent, внутри создать symlink, затем `mv -Tf` symlink на target path, удалить temp dir;
- `chown -h` symlink и `chown` regular restore не должны иметь `|| true`; exact metadata failure = rollback failure;
- все временные restore paths чистить локальным trap/явным cleanup при error;
- regular restore оставить temp + `mv -fT`.

## 4. Harness должен реально покрыть заявленные случаи

Обновить `scripts/tests/test-prod-path-transaction.sh`:

- обычный symlink должен иметь **relative** raw target, не absolute;
- проверить restored numeric uid/gid regular и symlink;
- отдельный сценарий: capture valid regular path -> заменить candidate на directory -> `prod_tx_rollback` обязан fail и не изменить другой registered path (доказательство двухфазности);
- убедиться, что snapshot сохраняется после rollback failure до явного cleanup;
- cleanup затем удаляет snapshot; double cleanup проходит;
- убрать черновые комментарии `Wait, ...`.

## 5. NodeSource dearmor runtime bug

Подтверждённый запуск:

```text
tmp=$(mktemp)
gpg --dearmor -o "$tmp" < key.asc
-> gpg: cannot open '/dev/tty'
```

Причина: output уже существует. Исправить без `mktemp -u`:

- создать root-only temp directory (`mktemp -d`),
- output path внутри него ещё не существует,
- `gpg --batch --yes --dearmor --output "$dir/nodesource.gpg" ...`,
- проверить non-empty regular output,
- install canonical key,
- temp dir включить в cleanup.

## 6. OS signal cleanup не должен глотать signal

Текущий один trap на `EXIT INT TERM` только удаляет temp files и может продолжить выполнение после INT/TERM.

Сделать named cleanup и signal handlers:

- EXIT -> cleanup;
- INT -> снять INT/TERM, exit 130 (EXIT cleanup выполнится);
- TERM -> снять INT/TERM, exit 143;
- primary status сохраняется;
- no inline trap body with business logic.

## 7. Minor exactness

- `prod_tx_capture` в начале должен очистить stale captured arrays/temp state или fail, если transaction уже active; не молча смешивать транзакции;
- `prod_tx_cleanup` сбрасывает captured state; `PROD_TX_PATHS` можно сохранить только если это явно нужно caller-у, иначе тоже сбросить;
- dependency header/library contract перечисляют `cat`, `dirname`, `readlink` и `rmdir`/`mkdir`, если используются;
- test harness source проверяет library как regular non-symlink.

## Acceptance

Выполнить:

```bash
bash -n scripts/lib/prod-path-transaction.sh
bash -n scripts/tests/test-prod-path-transaction.sh
bash -n scripts/prod-os-bootstrap.sh
bash -n scripts/prod-cert-prepare.sh
bash -n scripts/prod-host-prepare.sh
scripts/tests/test-prod-path-transaction.sh
scripts/prod-infra-fingerprint.sh
git diff --check
```

Повторить три safe `sudo -n ... --check`; ожидаемые live-state mismatches допустимы, shell/runtime ошибки — нет.

Показать `rg` evidence отсутствия:

- `mktemp -u`;
- `chown ... || true` в helper restore;
- inline `trap '...` в трёх новых production scripts (простая однословная trap-команда допустима, но named functions предпочтительнее).

Не делать apply, commit, push, SSH на production.
