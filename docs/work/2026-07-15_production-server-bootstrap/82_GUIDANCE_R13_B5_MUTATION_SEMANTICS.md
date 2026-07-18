# R13 B5 guidance — mutation must prove semantics

Addendum к `65_TZ...`.

## Non-negotiable rule

Semantic mutation считается PASS только если:

1. mutation anchor найден ровно один раз;
2. файл реально изменён;
3. mutated YAML остаётся parse-valid restricted subset;
4. validator возвращает exact expected **semantic** error code;
5. `E_PARSE_*`/generic structure corruption не считается доказательством semantic case.

## Gate order mutation

`MUT12_GATE_AFTER_SSH` должен физически переставить полные step blocks:

- весь `Verify branch and SHA` вместе с `env` и `run` body;
- весь `Configure SSH` вместе с `env` и `run` body.

Нельзя:

- только переименовать steps;
- добавить dummy step;
- удалить body;
- сломать indentation;
- принять `E_STEP_SCHEMA`/parse error вместо `E_STEP_ORDER`/`E_GATE_ORDER`.

Надёжный test-only helper на Python stdlib:

1. найти exact byte start каждой `      - name:` строки;
2. определить end до следующего step либо end jobs block;
3. проверить blocks non-empty и anchors unique;
4. swap byte slices без изменения их внутреннего content;
5. assert original gate bytes и configure bytes каждый присутствуют ровно один раз после swap;
6. validator должен вернуть exact order code.

## Other mutations

То же правило для:

- private conditional removal: удалить только exact `if...echo...exit 1...fi` block, оставить env reference;
- multiline forbidden command: добавить executable line внутрь существующего `run: |`, не inline malformed YAML;
- second job: добавить полностью valid second job mapping;
- duplicate key case — единственный case, где ожидается explicit parser duplicate-key code;
- TAB/anchor/folded block cases — единственные intentional parser errors.

Каждый mutation helper должен проверять effect before validator. Универсальный unchecked `sed` с zero/multiple matches запрещён.
