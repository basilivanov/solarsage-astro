# R12-R5C — host-prepare всё ещё блокирует empty-repo bootstrap

## P0 runtime defect

`verify_host_state` по-прежнему принимает только `check_marker` и использует его одновременно как fingerprint-marker switch и offsite mode.

Текущий код:

- offsite block вообще выполняется только при `check_marker == 1`;
- `verify_host_state 0` внутри apply не делает даже preflight;
- финальный `verify_host_state 1` внутри apply вызывает `prod-offsite-check.sh --check`;
- следовательно, `--apply` снова падает на корректном пустом repository до первого snapshot.

Комментарии о том, что apply использует preflight, не соответствуют runtime.

## Exact fix

Разделить параметры:

```bash
verify_host_state <check_marker:0|1> <offsite_mode:--preflight|--check>
```

Offsite block не должен зависеть от `check_marker`; он использует только второй explicit parameter.

Три call site должны быть ровно такими:

```bash
# explicit host check: fingerprint + full offsite readiness
verify_host_state 1 --check

# apply before marker: template/runtime verification + empty-repo-safe connectivity preflight
verify_host_state 0 --preflight

# apply after marker: fingerprint equality + тот же empty-repo-safe preflight
verify_host_state 1 --preflight
```

Внутри function валидировать оба параметра fail-closed. Не использовать global MODE, hidden env flag или inference из marker.

Добавить `scripts/tests/test-prod-host-offsite-routing.sh` с GRACE contract/map. Без root/live mutations он должен доказать хотя бы structural contract:

- function имеет два explicit параметра;
- explicit `--check` branch вызывает `verify_host_state 1 --check`;
- apply содержит ровно два вызова: `0 --preflight` и `1 --preflight`;
- offsite command получает exact second parameter;
- нет старого `if [ "$check_marker" -eq 1 ]` вокруг всего offsite block.

Если удобнее сделать isolated patched runtime harness — лучше, но static test должен быть fail-closed и exact, не просто искать слово `preflight` где угодно.

## Runbook order

В `docs/PRODUCTION_RUNBOOK.md` сейчас сразу после apply всё ещё стоит команда `prod-host-prepare.sh --check`, а первый backup описан ниже. Переставить в один непротиворечивый порядок:

1. `prod-host-prepare.sh --apply`;
2. первый `solarsage-backup.service`/`prod-backup.sh`;
3. `prod-offsite-check.sh --check`;
4. `prod-host-prepare.sh --check`;
5. STOP до ручной команды владельца на application launch.

Не оставлять ранний `--check` до первого snapshot.

## Малый contract cleanup

- В комментарии `prod-db-restore.sh` убрать устаревшее утверждение, что app `deactivating` разрешён: runtime правильно разрешает только inactive/failed.
- При offsite `--preflight` failure после уже committed local backup в `prod-backup.sh` также emit safe `EVENT: offsite_transfer_failed`; local pair сохраняется, retention не запускается.

## Acceptance delta

```bash
bash -n scripts/prod-host-prepare.sh
bash -n scripts/tests/test-prod-host-offsite-routing.sh
scripts/tests/test-prod-host-offsite-routing.sh
scripts/tests/test-prod-backup-offsite.sh
scripts/tests/test-prod-db-restore-safety.sh
scripts/prod-infra-fingerprint.sh
git diff --check
```

После этого повторить полный R12 suite из R5B. Никаких real host/DB/Restic/service operations, commit или push.
