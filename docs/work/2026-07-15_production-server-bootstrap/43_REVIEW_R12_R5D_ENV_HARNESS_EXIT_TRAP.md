# R12-R5D — env-loader harness оставляет sandbox на каждом green run

## Причина

`scripts/tests/test-prod-env-loader.sh` сначала устанавливает cleanup:

```bash
trap 'rm -rf "$TEST_SANDBOX"' EXIT
```

Но в Test 10 заменяет его на `dummy_exit_trap`, проверяет сохранение caller trap, затем выполняет:

```bash
trap - EXIT
```

Исходный cleanup trap не восстанавливается. Поэтому каждый успешный запуск оставляет свежий `/tmp/solarsage-env-test-*`.

## Исправление

- Во время dummy-trap test failure sandbox всё равно должен удаляться.
- После проверки caller trap восстановить canonical cleanup trap, а не очищать EXIT trap полностью.
- Не использовать `eval` для восстановления trap string.
- Самый простой вариант: dummy handler при фактическом EXIT также удаляет exact `$TEST_SANDBOX`, а после assertion снова установить `trap 'rm -rf "$TEST_SANDBOX"' EXIT`.
- Cleanup касается только unique test sandbox в `/tmp`, production code не менять.

## Acceptance

```bash
rm -rf /tmp/solarsage-env-test-*   # только после проверки, что test process не запущен
scripts/tests/test-prod-env-loader.sh
find /tmp -maxdepth 1 -type d -name 'solarsage-env-test-*' -print
```

Последняя команда должна быть empty. Затем один раз повторить полный R12 suite и проверить все canonical `/tmp/solarsage-*-test-*` patterns. Commit/push/production запрещены.
