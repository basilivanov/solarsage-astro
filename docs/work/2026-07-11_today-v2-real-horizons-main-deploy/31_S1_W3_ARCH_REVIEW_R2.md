# S1.W3 Architect Review R2 — restore drift detection and close false-green tests

Дата: 2026-07-11
Вердикт: `CHANGES_REQUIRED_R2`
Commit/push: запрещены.

R1 исправлен частично. YAML теперь валиден, binary split сделан правильно,
`any` удалён, фактический stderr normalizer тестируется. Ниже только оставшиеся
блокеры.

## 1. P0 — `contracts:check` больше не проверяет Pydantic → generated drift

В R2 из `scripts/contracts/check.sh` удалён обязательный первый шаг:

```bash
bash scripts/contracts/generate.sh
```

Это ломает главную цель всей волны. Если разработчик изменит Pydantic и забудет
регенерировать OpenAPI/TS/Zod, текущий `contracts:check` увидит чистые старые
generated files и ложно завершится успешно.

Вернуть точный pipeline из `27_S1_W3_IMPLEMENTATION_TZ.md`:

```text
1. bash scripts/contracts/generate.sh
2. bash scripts/contracts/today_fixture.sh --check
3. git diff --exit-code --
     packages/contracts/openapi.json
     packages/contracts/_generated.ts
     packages/contracts/_generated.zod.ts
```

GRACE должен честно говорить:

- `check.sh` может перезаписать generated artifacts через `generate.sh`;
- fixture он не нормализует и не пишет;
- любой subprocess/drift failure возвращает non-zero, не обязательно ровно 1.

README вернуть к этому же трёхшаговому описанию. Сейчас README повторяет
ошибочно урезанный pipeline.

## 2. P0 — isolation guard проходит при полном удалении разрешённого import

Текущий `importCount` проверяется только внутри цикла по найденным import.
Если import из route удалить полностью, цикл не выполнится, `violations`
останется пустым и test пройдёт.

Нужно иметь отдельный global/exact allowed count и после полного scan доказать:

```ts
expect(allowedImportCount).toBe(1)
```

`await` также нужно привязать к фактически найденному match, а не к
`text.includes(...)`, который теоретически может найти строку в comment или
другом месте.

Предпочтительная структура:

1. Для каждого match построить exact matched statement range/needle.
2. Разрешить match только если одновременно:
   - exact route;
   - exact specifier;
   - exact `await import(...)` statement;
   - все четыре guard indices существуют и меньше exact import index.
3. Увеличить `allowedImportCount` только для полностью разрешённого match.
4. После scan `expect(allowedImportCount).toBe(1)`.
5. Любой второй match остаётся violation.

Добавить/сохранить assertion, который действительно стал бы красным при
нулевом allowed import. Callback-фразы недостаточно.

## 3. P1 — normalizer пишет filesystem в `--check` и стал избыточно сложным

Сейчас `normalize_file` сначала создаёт отсутствующий parent directory, а уже
потом проверяет `check_only`. Это нарушает invariant «`--check` ничего не
пишет».

Также создание нового отсутствующего fixture, `chmod` и `chown` не нужны этой
волне и усложняют простой developer workflow.

Вернуть минимальный алгоритм:

```py
if not file_path.is_file():
    sanitized stderr
    return 2

read existing file
validate
render

if check_only:
    compare bytes only; never mkdir/write/chmod/chown
else:
    write sibling temp file
    Path.replace
```

Не создавать parent directories. Не поддерживать создание fixture с нуля.
Не делать `os.chown`. Canonical fixture уже существует и version-controlled.

Исправить function contract: ожидаемые JSON/Pydantic/IO errors ловятся и
превращаются в return codes, а не «raises».

Добавить test:

```text
missing_parent / fixture.json + check_only=True
-> non-zero
-> missing_parent после вызова всё ещё не существует
```

Удалить неиспользуемый `ValidationError` из backend test и отформатировать
длинные timing comprehensions.

## 4. P1 — wrapper принимает `--check extra` как валидный вызов

Условие проверяет только `$1`. Вызов:

```bash
scripts/contracts/today_fixture.sh --check unexpected
```

сейчас молча выполнит check.

Разрешить только exact arity:

```text
$# == 0
или
$# == 1 && $1 == --check
```

Все остальные варианты: usage + exit 2. Обновить устаревший comment
«otherwise forward args» и truthful failure policy.

## 5. P1 — single-source guard блокирует будущие даты, но не проверяет manual initializer

Сейчас:

```ts
file.startsWith("day-v2-")
```

запрещает добавить независимую fixture на другую дату. Проверять нужно только
копии текущего fixture stem:

```text
day-v2-2026-07-08*.json
```

Ожидаемый exact result:

```ts
["day-v2-2026-07-08.json"]
```

Дополнительно явно проверить regex/assertion, что wrapper не содержит manual
initializer `dayPayloadV2 = { ... }`. R1 требовал это отдельно; проверки
headline и `previewTiming` недостаточно.

## 6. P1 — CI install command не приведён к согласованному виду

В `contract-tests` всё ещё:

```bash
cd apps/api
pip install -e .
```

Использовать из repo root:

```bash
python -m pip install -e ./apps/api
```

Так job гарантированно использует interpreter из `setup-python`. Дополнительные
pytest packages этому job не нужны, если он не запускает pytest; не расширять
install без необходимости.

## 7. README — вернуть обязательные правила

README правильно исправил version semantics, но удалил полезные invariants.
Вернуть компактно:

- wire JSON содержит только JSON primitives/ISO strings, не `Date`, icons или
  React values;
- generated artifacts коммитятся вместе с Pydantic change;
- breaking shape/semantics требует contract version discipline и обновления
  canonical API docs;
- frontend импортирует public barrels и не объявляет wire schemas вручную;
- `contracts:check` реально выполняет generate → fixture check → generated
  diff.

## 8. R3 gates

Без commit/push:

```bash
apps/api/.venv/bin/python -c \
  'import pathlib, yaml; yaml.safe_load(pathlib.Path(".github/workflows/ci.yml").read_text()); print("YAML_OK")'

cd apps/api && .venv/bin/python -m pytest \
  tests/test_activation_contracts.py \
  tests/test_today_fixture_contract.py -q

cd /opt/solarsage-astro
pnpm contracts:fixture:check
pnpm contracts:check
npx vitest run \
  __tests__/contracts/today-fixture-roundtrip.test.ts \
  __tests__/guardrails/preview-isolation.test.ts \
  __tests__/contracts/generated-runtime.test.ts
npx tsc --noEmit

bash scripts/contracts/today_fixture.sh --check unexpected
# expected exit 2

git diff HEAD --check
git diff --cached --check
git status --short --branch
```

Browser/full Vitest/build из R2 повторять не требуется, если production TS/TSX
и payload не меняются; их зелёное доказательство остаётся действительным.

## 9. Callback R3

```text
READY_S1_W3_REVIEW_R3
contracts_check_runs_generate: PASS
contracts_check_fixture_read_only: PASS
guard_zero_import_fails: PASS
guard_exact_allowed_count: 1
normalizer_check_missing_parent_write: NO
normalizer_chown_mkdir_scope: REMOVED
wrapper_extra_args_exit: 2
fixture_stem_sources: [day-v2-2026-07-08.json]
manual_initializer_guard: PASS
ci_python_install: python -m pip install -e ./apps/api
readme_pipeline_truthful: PASS
yaml_parse: PASS
api_tests: <count>
focused_vitest: <files/tests>
tsc: PASS
contracts_check: PASS
baseline_repair_files_unstaged: 2
s1_w3_binary_files_staged: 0
commit: NOT_YET
push: NOT_YET
```
