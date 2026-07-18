# R13 Phase B4 — финальный контракт forced-command wrapper harness

## Статус и границы

Это узкое ТЗ только для финализации изолированного теста:

- `scripts/tests/test-prod-github-wrapper.sh`;
- при доказанной необходимости — только тестовая копия wrapper, без изменения production semantics.

Production apply/deploy, SSH, GitHub, сеть, `git fetch`, checkout, systemd, commit и push запрещены. Не трогать и не stage-ить frozen/unrelated paths из `53_REVIEW...` и текущего handoff. Все временные файлы — только в одном `$TEST_DIR`.

Кодер не должен считать текущие `36 passed` доказательством приёмки: после изменения теста архитектор выполнит независимый запуск из свежего shell.

## Контракт production wrapper, который обязан быть доказан

Канонический файл `infra/production/solarsage-github-deploy` принимает только:

```text
SSH_ORIGINAL_COMMAND="deploy <ровно 40 строчных hex>"
SSH_ORIGINAL_COMMAND="source-check <ровно 40 строчных hex>"
```

Между verb и SHA ровно один ASCII-пробел. Никаких positional args у самого wrapper. Любая другая форма возвращает `126` и не запускает target.

Dispatch должен быть прямым `exec /bin/bash` с точным argv:

```text
deploy       -> /bin/bash <prod-deploy-path> --expected-sha <sha>
source-check -> /bin/bash <prod-github-access-path> --check --expected-sha <sha>
```

Код возврата target должен пройти наружу без преобразования, включая `1`, `42` и `126`.

## Обязательные изменения в harness

### 1. Безопасная проверка argv с сохранением границ

Текущая конструкция вида:

```bash
printf '%s\\0...' | tr -d '\\0'
tr -d '\\0' < audit
```

недопустима: она уничтожает границы аргументов и может пропустить лишний аргумент или неправильное разбиение.

Сделать один из эквивалентных вариантов:

- expected-файл и audit-файл с настоящими NUL-records и `cmp -s`;
- либо один безопасный, однозначный формат (`printf '%q\\n'` для каждого argv) и byte-exact `cmp -s`.

Проверка должна отдельно доказывать:

- какой именно target был вызван (`deploy` и `source-check` нельзя писать в неразличимый общий audit без target ID);
- target действительно был вызван в каждом valid/propagation case;
- target был вызван ровно один раз;
- argv ровно совпал, включая количество и порядок аргументов;
- пустой audit, отсутствующий audit и лишний trailing record считаются ошибкой.

Предпочтительно использовать отдельные audit-файлы для deploy/access mock либо начинать invocation record с однозначного NUL-safe target ID. Перестановка target paths в wrapper-copy обязана делать тест красным.

Не использовать `echo "$@"`, не использовать незафиксированный `grep`, не нормализовать пробелы/переводы строк.

### 2. Полная отрицательная матрица для обоих verb’ов

Для `deploy` **и** `source-check` выполнить отдельные cases с ожидаемым `126` и отсутствием target audit:

1. пустая/отсутствующая `SSH_ORIGINAL_COMMAND`;
2. positional arg у wrapper;
3. uppercase SHA;
4. non-hex SHA (например, `g` среди символов);
5. short SHA;
6. long SHA;
7. missing SHA (`deploy`, `source-check`);
8. два пробела после verb;
9. ведущий пробел;
10. trailing space;
11. tab вместо единственного ASCII-пробела;
12. trailing LF;
13. trailing CR;
14. valid SHA плюс дополнительный token (`... <sha> extra`);
15. valid SHA плюс `; id`;
16. `$(id)` и backticks;
17. pipe и `&&`;
18. другой verb с валидным SHA (`status <sha>`);
19. произвольная команда (`id`, `bash`, `env`).

Важно: `source-check` нельзя тестировать только на missing SHA — hostile cases должны быть симметричны с `deploy`.

Каждый negative case обязан проверять одновременно:

- точный rc `126`;
- отсутствие target audit-файла;
- отсутствие побочных файлов/маркеров за пределами `$TEST_DIR`;
- отсутствие выполнения shell substitution/injection (не полагаться только на rc).

### 3. Положительная матрица и propagation

Использовать один canonical lowercase SHA и минимум один другой lowercase SHA, чтобы не доказать случайно только конкретное значение.

Для каждого verb проверить:

- valid command → rc `0`, target вызван ровно один раз;
- exact argv через byte-exact comparison;
- target rc `1`, `42`, `126` → wrapper возвращает тот же rc, target audit существует и exact argv сохраняется.

`expect_target_call` должен быть отдельным флагом, не выводиться из значения `expected_rc`: target вправе сам вернуть `126`.

Перед каждым case удалять audit и stdout/stderr, а после case проверять, что старый audit не ошибочно принят за новый вызов.

### 3.1 Fail-closed подмена canonical target paths

До первого запуска wrapper-copy harness обязан доказать подмену путей, иначе тест может случайно вызвать real production target:

- до подмены каждая canonical runtime target-строка встречается ровно один раз;
- подмена касается только этих двух runtime paths, не комментариев/контрактов;
- после подмены canonical `/opt/solarsage-astro/scripts/prod-deploy.sh` и `prod-github-access.sh` полностью отсутствуют в исполняемых строках;
- каждый sandbox target path присутствует ровно один раз;
- любое несовпадение count/path немедленно завершает harness до valid-command cases.

Глобальный unchecked `sed -i` без pre/post assertions недопустим. Если структура production wrapper изменилась и exact path не найден, harness обязан упасть, а не продолжить с real path.

### 4. Case manifest и честный счётчик

Сохранить список case IDs в массиве/manifest внутри harness. В конце проверить:

- каждый объявленный ID выполнен ровно один раз;
- фактический `CASE_COUNT` равен числу ожидаемых ID;
- duplicate/missing ID делает harness красным.

Число cases само по себе не является приёмкой, но manifest не должен позволять случайно забыть половину симметричной матрицы.

### 5. Безопасная диагностика и cleanup

- `trap 'rm -rf "$TEST_DIR"' EXIT INT TERM HUP` обязателен;
- при ошибке печатать только label, rc и пути audit/out/err; не печатать содержимое потенциально чувствительных файлов;
- reject cases должны иметь пустой stdout и только утверждённое generic stderr-сообщение; raw `SSH_ORIGINAL_COMMAND` и hostile sentinel не должны попадать в combined output;
- после успешного завершения `$TEST_DIR` должен отсутствовать;
- harness не должен менять `/opt/solarsage-astro`, кроме чтения production wrapper и создания sandbox-копии;
- не читать `.env`, Telegram token, private key или API body.

## Self-test против ложноположительного теста

Добавить в harness самопроверку валидатора (только в `$TEST_DIR`), чтобы следующие мутации специально давали non-zero, а затем cleanup возвращался в исходное состояние:

1. mock deploy добавляет лишний argv;
2. mock source-check меняет порядок argv;
3. deploy/source-check targets в wrapper-copy переставлены местами;
4. propagation branch возвращает нужный rc без вызова target;
5. два argv склеены в один аргумент с теми же суммарными байтами;
6. mock target вызывается дважды;
7. wrapper-copy принимает два пробела;
8. wrapper-copy принимает uppercase или non-hex SHA;
9. wrapper-copy принимает leading/trailing space либо произвольный `id`.

Self-test не должен изменять canonical production wrapper и не должен считаться production execution. Если реализация self-test чрезмерно усложняет harness, разрешён эквивалентный независимый mutation block с тем же доказательством.

## Дополнительное production hardening

Production wrapper по текущему чтению реализует требуемый dispatch. Допустимо добавить `LC_ALL=C` перед regex-проверками, чтобы `[0-9a-f]` всегда означал ASCII lowercase hex независимо от locale. Иных semantic-изменений production wrapper в этой итерации не делать без отдельного доказанного дефекта.

## Проверка кодером перед остановкой

Кодер запускает только в sandbox:

```bash
bash -n infra/production/solarsage-github-deploy \
  scripts/tests/test-prod-github-wrapper.sh
timeout 120 bash scripts/tests/test-prod-github-wrapper.sh
git diff --check
```

Не обновлять `51_REVIEW_R13_PHASE_B_HANDOFF.md` результатами кодера и не писать «accepted». В handoff попадут только результаты независимого запуска архитектора после последнего изменения.

В финальном сообщении кодер должен перечислить изменённые файлы, фактический rc, число cases, подтверждение отсутствия production/network/SSH/commit/push и остановиться.
