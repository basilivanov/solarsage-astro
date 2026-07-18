# R12-R4A — точная причина падения restore-safety harness

Статус: обязательная корректировка перед повторным acceptance-review R12.

Production deploy, реальные backup/restore/offsite операции, commit и push по-прежнему запрещены.

## Найденная причина текущего падения

`scripts/tests/test-prod-db-restore-safety.sh` не доходит до mock `prod-backup.sh` в Test 5 не из-за передачи `MOCK_BACKUP_MULTIPLE`.

Текущий mock `stat` безусловно возвращает `700` для любого запроса `%a`. Это верно для каталога backup, но неверно для созданного `restore.lock`, для которого production script требует ровно `600`. Поэтому restore завершается на проверке lock-файла раньше вызова backup mock, а проверка закономерно пишет `FAIL: backup was not called`.

Дополнительно выражение

```bash
MOCK_BACKUP_MULTIPLE="${MOCK_BACKUP_MULTIPLE:-$MOCK_BACKUP_MULTIPLE}"
```

некорректно при `set -u`: если переменная не задана, fallback снова читает ту же незаданную переменную. Вернуть безопасную форму `${MOCK_BACKUP_MULTIPLE:-}`. Префиксное присваивание перед вызовом shell-функции и/или `export` уже достаточно передаётся в формируемый `env -i`, если helper использует эту безопасную форму.

## Что исправить в harness

1. Сделать mock `stat` path-aware:
   - backup directory: owner `astro:astro`, mode `700`;
   - `restore.lock` и `backup.lock`: owner `astro:astro`, mode `600`;
   - dump size: детерминированное положительное значение;
   - для негативных тестов разрешить явное управление owner/mode через отдельные test-only env variables.
2. Не использовать самоссылочный parameter expansion. Все optional mock variables должны безопасно становиться пустой строкой под `set -u`.
3. Не считать исчезновение `/tmp/solarsage-restore-test-*` отдельной ошибкой: sandbox удаляется `EXIT` trap. Для диагностики печатать captured stdout/stderr до выхода либо временно вводить test-only `KEEP_TEST_SANDBOX=1`, не меняя production script.
4. Упростить генерацию `TEST_SCRIPT_NO_TTY`: он уже создаётся из заранее пропатченного `TEST_SCRIPT`, поэтому второй поиск исходной строки `SCRIPT_DIR=...` не должен быть обязательным условием.

## Обязательные restore-lock сценарии из R12-R4

Harness должен доказать, а не только декларировать:

- FIFO на месте `restore.lock` отвергается быстро и не зависает;
- directory на месте `restore.lock` отвергается;
- symlink и dangling symlink отвергаются;
- regular file с неправильным owner отвергается;
- regular file с неправильным mode отвергается;
- существующий валидный regular file `astro:astro 0600` не обнуляется: sentinel content остаётся byte-exact после попытки;
- новый lock создаётся с `0600`, открывается без truncate через `<>`, после чего берётся `flock`;
- негативные lock-сценарии не вызывают backup, `psql` или `pg_restore`.

Production implementation также нужно повторно проверить на требование R12-R4: создание нового lock должно быть безопасным в приватном каталоге `astro:astro 0700`, затем обязательны повторная проверка типа/owner/mode и non-truncating open. Простая последовательность `test -> touch -> chmod` без защиты от уже появившегося path не считается достаточным доказательством безопасного создания.

## Acceptance после исправления

Запустить сначала только:

```bash
bash -n scripts/prod-db-restore.sh
bash -n scripts/tests/test-prod-db-restore-safety.sh
timeout 60 scripts/tests/test-prod-db-restore-safety.sh
```

Затем выполнить весь acceptance-набор из `36_REVIEW_R12_R4_FINAL_RUNTIME_GAPS.md`. Полные Vitest/Pytest/Playwright в этой точке не заменяют shell safety harnesses и запускаются только после их прохождения.
