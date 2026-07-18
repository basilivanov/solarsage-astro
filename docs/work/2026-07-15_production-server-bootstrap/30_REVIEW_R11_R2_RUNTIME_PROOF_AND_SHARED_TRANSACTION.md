# R11-R2 review — runtime proof and shared path transaction

## Статус

R11-R1 не принят. `bash -n` проходит, но реальные read-only вызовы доказали runtime failures:

```text
sudo scripts/prod-cert-prepare.sh --check
-> REPO_ROOT: unbound variable

sudo scripts/prod-host-prepare.sh --check
-> report_error: command not found
```

Кроме того, в OS apply снова есть top-level `local`, а signal traps могут выполнить rollback дважды. Исправь пункты ниже. Commit/push/production запрещены.

## 1. Cert script: восстановить repo-root bootstrap

В начале `scripts/prod-cert-prepare.sh`, до функций:

- вычислить `SCRIPT_DIR` относительно `${BASH_SOURCE[0]}`;
- вычислить canonical `REPO_ROOT` как parent script dir;
- убедиться, что это directory и не symlink;
- valid `--check` больше не должен падать на unbound variable.

## 2. Host script: вернуть error aggregation

Внутри `main`, до первого preflight check:

- `local errors=0`;
- nested `report_error()` печатает только безопасное сообщение и увеличивает `errors`;
- `[ "$errors" -gt 0 ]` должен работать при нуле;
- real `sudo ... --check` обязан дойти до нормального aggregated verification/preflight result, а не exit 127/`set -u` failure.

## 3. OS script: никаких `local` вне функции

Сейчас top-level apply содержит минимум:

- `local dearmored_tmp`;
- `local JAIL_TEMPLATE`.

Вынеси весь apply flow в `apply_os_state()` и вызывай его из dispatch, либо убери top-level local. Предпочтительно функция, чтобы это больше не повторялось.

Проверка должна анализировать scope, а не просто `rg`: все `local` допустимы только внутри function bodies.

## 4. Shared exact transaction helper вместо двух копий

Дублированные capture/restore в cert и host уже расходятся и не имеют реального теста. Создай:

- `scripts/lib/prod-path-transaction.sh`;
- `scripts/tests/test-prod-path-transaction.sh`.

Library requirements:

- source-only, при source ничего не исполняет и не ставит traps;
- Bash 5.2, `set -euo pipefail` не навязывать caller-у;
- namespaced functions/variables `prod_tx_*` / `PROD_TX_*`;
- snapshot root — root-owned mode 0700 temp dir под `/run` в production, но test harness может задать safe temp base через явный function argument; не использовать env-based hidden test bypass;
- capture path states: missing, regular, symlink (включая dangling); другие types fail;
- regular metadata: exact bytes, numeric uid/gid, mode;
- symlink metadata: raw target, numeric link uid/gid;
- restore candidate разрешён только missing/regular/symlink; directory/fifo/device/socket на месте candidate — fail, никакого `rm -rf`;
- regular restore: temp в target parent, bytes + uid/gid + mode, `mv -fT`;
- symlink restore: temp symlink в target parent, `chown -h`, `mv -Tf`;
- missing restore удаляет только regular/symlink;
- cleanup идемпотентен;
- capture failure чистит уже созданные snapshots;
- никаких systemctl/nginx/fail2ban/env/network внутри library.

Оба production scripts должны source exact regular non-symlink helper из repo и использовать одну реализацию. Добавить helper:

- в host inventory/bash-n;
- в runtime fingerprint, потому что runtime scripts source его;
- в GRACE contracts.

Test harness без sudo и без `/etc` обязан реально проверить:

1. regular file bytes/mode restore;
2. relative symlink target restore;
3. dangling symlink restore;
4. missing path restore;
5. unexpected directory capture/restore rejection;
6. cleanup не оставляет temp dirs/files;
7. повторный cleanup безопасен.

## 5. Однократный trap/rollback

В cert и host scripts не использовать inline trap с `local`.

Сделать named handler functions:

- `on_transaction_exit`;
- `on_transaction_int` -> снять INT/TERM traps и `exit 130`;
- `on_transaction_term` -> снять INT/TERM traps и `exit 143`.

`on_transaction_exit` первым действием снимает `EXIT INT TERM`, сохраняет `$?`, использует guard `ROLLBACK_STARTED`, выполняет rollback максимум один раз, cleanup, затем возвращает original nonzero status. Если uncommitted path выходит со status 0 — считать internal error и вернуть 1.

На success: final verification -> `TRANSACTION_COMMITTED=1` -> cleanup -> снять traps.

## 6. Полнота host transaction

В host transaction добавить paths:

- `/etc/nginx/sites-available/astro.vasiliy-ivanov.ru-bootstrap.conf`;
- `/etc/nginx/sites-enabled/astro.vasiliy-ivanov.ru-bootstrap.conf`;
- `/etc/solarsage/infra-fingerprint`.

Host apply должен удалить оба bootstrap paths. Marker больше не имеет отдельного ad-hoc backup/rollback: он входит в shared transaction и пишется atomically. Final `verify_host_state 1` до commit.

Не расширять rollback на DB data/cert files. App services не restart/start/stop.

## 7. Cert transaction completeness

- shared capture до first Nginx/hook mutation;
- final verification до commit;
- signal/EXIT rollback ровно один раз;
- certbot certificate/account files не rollback;
- timer state не обязан rollback, но это явно документировать;
- ACME dirs допустимо оставить с canonical owner/mode после failure.

## 8. Исправить оставшиеся OS verification bugs

Сейчас `unattended-upgrades` всё ещё использует `command || echo inactive` и может получить две строки. Сделать:

```bash
if ua_state=$(systemctl is-active "$unit" 2>/dev/null); then :; else ua_state=inactive; fi
```

То же правило применить к `LoadState`: не смешивать command stdout с fallback output.

UFW default line на Ubuntu выглядит:

```text
Default: deny (incoming), allow (outgoing), deny (routed)
```

Текущая literal-проверка `Default: allow (outgoing)` ошибочна. Проверить canonical line/fields так, чтобы этот normal output проходил, а incoming не-deny/outgoing не-allow падали. `ufw show added` extras policy оставить.

Убрать неиспользуемый `unexpected_rules`, если он не нужен.

NodeSource temporary dearmored file также должен входить в cleanup trap.

## 9. Required command and exact certificate checks

Host preflight добавить реально используемые commands: `mktemp`, `readlink`, `dirname`, `mv`, `fail2ban-client`, `sleep` (и shared helper dependencies).

Host certificate preflight:

- resolve fullchain и key;
- оба targets readable regular;
- `openssl x509 -checkhost "$DOMAIN"`;
- `openssl x509 -checkend 1209600`.

## 10. Реальные acceptance checks

После исправления выполнить:

```bash
bash -n scripts/lib/prod-path-transaction.sh
bash -n scripts/tests/test-prod-path-transaction.sh
bash -n scripts/prod-os-bootstrap.sh
bash -n scripts/prod-cert-prepare.sh
bash -n scripts/prod-host-prepare.sh

scripts/tests/test-prod-path-transaction.sh

sudo -n scripts/prod-cert-prepare.sh --check
sudo -n scripts/prod-host-prepare.sh --check
sudo -n scripts/prod-os-bootstrap.sh --check
```

На текущем test host три `--check` могут завершиться nonzero из-за несовпадения live state — это допустимо. Недопустимы: `unbound variable`, `command not found`, `local: can only be used in a function`, traceback, secret output.

Также:

- invalid CLI exit 2 tests из R11-R1;
- fingerprint;
- `git diff --check`;
- clean next-env/tsconfig;
- free ports 3003/18092.

## Handoff

Покажи фактические exit codes и первые безопасные строки всех трёх `sudo --check`, результат shared helper harness и подтверждение, что commit/push/production не выполнялись.
