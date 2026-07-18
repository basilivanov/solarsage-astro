# R13 Phase B R2A — production env overrides для теста запрещены

## Немедленная корректировка

Не добавлять в `scripts/prod-deploy.sh` testability seams через runtime environment variables:

```bash
LOCKFILE="${SOLARSAGE_DEPLOY_LOCKFILE:-/tmp/solarsage-deploy.lock}"
tmp_untracked=$(mktemp "${SOLARSAGE_DEPLOY_MKTEMP_PREFIX:-...}")
```

Если эти изменения уже внесены — вернуть production literals к принятому состоянию:

```bash
LOCKFILE="/tmp/solarsage-deploy.lock"
tmp_untracked=$(mktemp)
```

Причина: caller-controlled environment позволяет выбрать другой lockfile и обойти взаимное исключение deploy-процесса; prefix также расширяет production input surface и позволяет направить temp creation в неожиданный путь. Это production security regression ради harness и противоречит правилу `50_TZ`: тестовая копия может менять пути, production semantics не меняются.

## Как изолировать harness правильно

- `LOCKFILE="/tmp/solarsage-deploy.lock"` заменить на sandbox path только в copied `$TEST_DEPLOY`.
- Для production `mktemp` без template добавить fail-closed mock `mktemp` в `$TEST_DIR/bin`:
  - поддержать только exact ожидаемый invocation без аргументов;
  - вызвать `/usr/bin/mktemp "$TEST_DIR/untracked.XXXXXX"`;
  - записать безопасный audit marker;
  - любой другой argv — non-zero.
- Проверить, что созданный temp удалён после success и failure.
- Не добавлять `SOLARSAGE_DEPLOY_LOCKFILE`, `SOLARSAGE_DEPLOY_MKTEMP_PREFIX`, `TEST_MODE` или другие test-only env branches в production script.

Разрешённые production changes в Phase B остаются ограничены:

- `source-readiness.yml`: `BatchMode=yes` и GRACE contract;
- forced-command wrapper: минимальная защита exact-one-space, если она подтверждена hostile-byte тестом;
- иной production fix — только после воспроизводимого failing harness и отдельного архитектурного обоснования.

Production/real deploy, commit/push запрещены.
