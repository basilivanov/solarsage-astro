# R13 Phase B3 R2 — access harness ещё не принят: false-green gaps

## Статус ревью

`56_HANDOFF_R13_PHASE_B3_ACCESS_ONLY.md` пока **не принимается**. Независимо
подтверждено, что текущий harness возвращает `0` два раза и печатает 151 case,
но проверка исходника показывает, что несколько обязательных контрактов из
`55_TZ_R13_PHASE_B3_ACCESS_CONTRACT_MATRIX_ONLY.md` всё ещё не исполняются.
Количество `151` само по себе не является доказательством покрытия: туда входят
подготовительные вызовы (`PATH_PREP*`, `CFG03 prepare`, `AK03 prepare`,
`Prepare API`), а обязательные FAIL-кейсы отсутствуют.

Этот проход остаётся узким: менять только `scripts/tests/test-prod-github-access.sh`
и минимальный `scripts/prod-github-access.sh`, необходимый для красного теста.
Запрещены production apply/preflight/check на реальном сервере, сеть/SSH/GitHub,
изменения workflow/других harness, commit и push.

## Доказанные gaps в текущем коде

### 1. Матрица failure/recovery неполная

В тесте есть `FAIL01-03`, `FAIL06-08`, но отсутствуют:

- `FAIL04` — ошибка config helper/write;
- `FAIL05` — ошибка authorized_keys helper/write;
- `FAIL09` — ошибка `git remote set-url`.

Для каждого добавить отдельный failure и `_REC` case. Failure должен проверить
ненулевой rc, отсутствие success-сообщения, отсутствие temp-файлов и состояние
каждого назначения как полностью старое или полностью новое. Recovery после снятия
инъекции обязан снова пройти apply и дать канонические байты/режимы/владельцев.
Не заявлять rollback всех трёх файлов: текущая реализация делает последовательные
`mv` и допускает частично применённые, но полные per-file состояния.

Для `FAIL09` mock `git` обязан реально вернуть ошибку только на точный
`remote set-url origin git@github.com-solarsage-prod:basilivanov/solarsage-astro.git`;
после этого повторный apply без инъекции должен восстановить origin.

### 2. Installed security cases не покрывают mode/owner

Сейчас `PATH41-43` проверяют только symlink. Добавить отдельные subcase с
установленным обычным файлом:

- known_hosts: wrong mode, wrong owner;
- config: wrong mode, wrong owner;
- authorized_keys: wrong mode, wrong owner.

Каждый negative case — read-only preflight, state byte-identical, zero `mv`/`chown`/
`set-url`; не объединять три дефекта в один label.

### 3. Byte-exact assertions заменены на substring

`CFG02`, `AK02`, `AK11` сейчас проверяют `grep`. Перед apply сохранить ожидаемый
бинарный файл с пробелами, комментариями, CR-sensitive байтами и final LF; после
apply проверять весь файл через `cmp -s`. Для hostile comment/glob проверить и
неизменность unrelated line, и отсутствие path expansion.

### 4. NET и origin read-only доказательства неполные

Перед каждым `ORIGIN04-08`, `NET01-23` сбрасывать только audit-файлы и делать
snapshot. После invocation проверять:

- snapshot всех mutable files (включая отсутствие origin);
- нет `chown`, `mv`, `remote set-url`;
- нет `fetch`, `checkout`, `push`;
- для NET разрешены только точные формы `curl`, `timeout`, `git ls-remote`.

Добавить для `--check` отдельные invalid HTTP status и curl non-zero/timeout,
а не только 403/429/500/503. Не печатать полные hostile argv в диагностике.

`ORIGIN01-03` должны проверять число вызовов `remote set-url` и точные аргументы:
нормализованный origin не должен менять URL повторно (или это должно быть явно
зафиксировано контрактом; предпочтителен zero redundant mutation).

### 5. Fail-closed mocks фактически ещё permissive

Независимая инспекция показала, что текущие моки не соответствуют `55`:

- `mv` проверяет только destination, не source и не exact argc;
- `git` разбирает только частичный subcommand и принимает лишние аргументы;
- `ssh-keygen` принимает произвольные флаги/формы;
- `mktemp` без аргументов вызывает реальный `/usr/bin/mktemp` и создаёт файл вне
  `$TEST_DIR`;
- `stat`/`chown` допускают неизвестные форматы/targets;
- `curl`/`timeout` принимают лишние или повторные аргументы;
- `assert_no_forbidden_git` объявлен, но не вызывается во всех negative/read-only
  cases.

Ужесточить моки до exact argv/shape и fail-closed. Любой target/source вне
`$TEST_DIR` — немедленный non-zero. `mktemp` без args должен создавать fixture
внутри `$TEST_DIR` либо завершаться с ошибкой; не писать в `/tmp` вне harness.
Audit должен регистрировать и разрешённые попытки, и injected failure, не раскрывая
ключи/токены.

### 6. Output safety не является global scan

`assert_output_safe` сейчас проверяет только три простых шаблона и вызывается по
одному файлу. Добавить безопасный global scan по всей
`$TEST_DIR/outputs` после suite. В запрещённые sentinel включить:

- checkout и Actions base64 material;
- PEM/private-key markers;
- credential-bearing origin fixture;
- API body sentinel;
- malformed remote-output sentinel;
- `.env`/secret sentinel;
- Actions comment, если он присутствует в fixture output.

Разрешённый fingerprint не считать утечкой. При failure печатать только case id и
имя файла, не содержимое hostile argv.

### 7. Host parser должен различать alias и runtime error

В `scripts/prod-github-access.sh` любой non-zero от inline Python сейчас
интерпретируется как «alias найден». Изменить на явные exit-коды (например,
`0 = alias отсутствует`, `10 = alias найден`, другое = parse/runtime error`) и
generic безопасную ошибку для runtime error. Добавить harness case на injected
Python parse failure; он должен завершаться non-zero до mutation и не маскироваться
сообщением про alias.

## Требования к структуре теста

- Не считать `PATH_PREP*`, `CFG03 prepare`, `AK03 prepare`, `Prepare API` как
  acceptance cases; preparation может быть обычной shell-функцией без `run_case`.
- Сохранить `LAST_CASE_ID` до запуска child и per-case stdout/stderr.
- `snapshot_mutable_state` обязан явно возвращать `0` при отсутствующем optional
  origin.
- `assert_no_temp_files` использовать сгруппированный `find` и сканировать весь
  `$TEST_DIR`, а не только `.ssh`.
- Не менять frozen/unrelated paths.

## Acceptance после исправления

Кодер должен выполнить локально в tmux и передать exact output:

```bash
bash -n scripts/prod-github-access.sh scripts/tests/test-prod-github-access.sh
timeout 240 bash scripts/tests/test-prod-github-access.sh
git diff --check -- scripts/prod-github-access.sh scripts/tests/test-prod-github-access.sh
```

Запустить harness два раза подряд. Оба раза должны иметь `rc 0`, напечатать
`ORIGIN08`, `NET23`, `FAIL09` и последний recovery case, затем финальную строку
`All <honest-case-count> test-prod-github-access matrix cases passed!`.

Только после этого обновить `56_HANDOFF...` фактическими ID/section counts и
результатами двух свежих запусков. До принятия этого ревью commit/push и любые
production действия запрещены.
