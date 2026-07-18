# R13 Phase B4 R1 — primary wrapper audit fix

## Прочитать сначала

- `64_TZ_R13_PHASE_B4_WRAPPER_FINAL_CONTRACT.md`;
- `67_REVIEW_R13_PHASE_B4_WRAPPER_REJECTED_PRIMARY_AUDIT.md`.

Это минимальный remedial pass. Менять только `scripts/tests/test-prod-github-wrapper.sh` и при необходимости coder-handoff `66_HANDOFF...`. Production wrapper semantics не менять. Production/network/SSH/GitHub/commit/push запрещены.

## 1. Primary target audit: ровно одна invocation

Оба основных mock target должны писать audit в append mode `>>`, а не перезаписывать через `>`.

Каждая invocation должна иметь однозначный record, например:

```text
BEGIN
target=deploy
/bin/bash
<%q mock path>
<%q arg 1>
...
END
```

или эквивалентный NUL-record. Separate deploy/access files сохранить. Expected file для каждого positive/propagation case содержит ровно один полный invocation record и сравнивается `cmp -s`.

Общий positive helper обязан проверить в одном месте:

- нужный audit существует;
- другой target audit отсутствует;
- exact target ID/path;
- exact argv count/order/bytes;
- ровно одна invocation — второй append автоматически ломает `cmp`;
- rc target `0`, `1`, `42`, `126` проходит без преобразования.

Self-test double-call обязан использовать тот же основной audit encoder/validator либо byte-identical эквивалент. Mutation с двумя одинаковыми вызовами должна быть отвергнута именно из-за лишнего invocation record. Отдельный ручной `wc -l == 8`, не связанный с primary validator, недостаточен.

## 2. Executable-only fail-closed path substitution

До подмены извлечь только executable dispatch lines, а не comments/module contract. Текущий canonical shape:

```text
exec /bin/bash /opt/solarsage-astro/scripts/prod-deploy.sh --expected-sha "$sha"
exec /bin/bash /opt/solarsage-astro/scripts/prod-github-access.sh --check --expected-sha "$sha"
```

Обязательные assertions до первого wrapper execution:

- executable `exec /bin/bash` dispatch lines ровно две;
- deploy exact runtime line ровно одна;
- source-check exact runtime line ровно одна;
- нет третьего/unknown absolute target;
- после exact-line substitution runtime lines указывают ровно на `$MOCK_DEPLOY` и `$MOCK_ACCESS` с неизменённым argv;
- canonical executable paths отсутствуют;
- все executable target paths находятся внутри normalized `$TEST_DIR`;
- zero/multiple replacement — fail до valid cases.

Добавить mutation/self-proof: canonical string остаётся только в comment, а executable path заменён на другой absolute path. Проверка обязана упасть до запуска. Никакой real target в mutation не создавать и не выполнять.

## 3. Exact output safety contract

Расширить `run_case` параметром expected diagnostic class либо exact expected stderr file.

Для каждого case byte-exact проверить:

- valid/propagation: stdout empty, stderr empty;
- empty command: stdout empty, stderr exact generic `Remote commands are not permitted for this deploy key.` + LF;
- positional args: stdout empty, stderr exact generic `Arguments are not permitted for this deploy key.` + LF;
- остальные rejects: stdout empty, stderr exact generic `Forbidden command format.` + LF.

Raw `SSH_ORIGINAL_COMMAND`, SHA, shell payload или target output не разрешены. Удалить текущий no-op block `forbidden_found`.

Добавить hostile sentinel cases так, чтобы строки содержали literal `$(touch <sandbox-sentinel>)` и backticks, но shell harness сам их не выполнил. После case assert sentinel отсутствует. Также combined output не содержит sentinel path/string.

При assertion failure печатать только case ID, rc и пути stdout/stderr/audit. Не делать `cat` raw logs. Удалить неиспользуемый `self_check_fails`, который печатает raw output, либо переделать безопасно и реально использовать.

Добавить self-test: mutated wrapper печатает raw `SSH_ORIGINAL_COMMAND` перед generic reject. Output validator обязан его отвергнуть.

## 4. Исправить hostile matrix

Симметрично для `deploy` и `source-check`:

- non-hex case должен иметь **ровно 40 characters total**, один canonical hex character заменён на `g`, а не добавлен 41-м;
- отдельный dollar command-substitution case;
- отдельный backtick case;
- отдельный pipe case;
- отдельный `&&` case.

Остальные cases из `64` сохранить. После добавления backtick и `&&` ожидается минимум 21 negative case на verb плюс 10 positive/propagation, то есть минимум 52 product cases. Обновить exact manifest; label не может заявлять два payload вида при проверке только одного.

## 5. GRACE/test structure

Добавить:

- `START_MODULE_MAP` с реальными helpers/semantic blocks;
- `START_FUNCTION_CONTRACT` для `run_case`, audit builders/validator и mutation helper(s);
- stable case ID manifest с duplicate/missing equality;
- `trap ... EXIT INT TERM HUP` сохранить.

Self-tests не включать в product `CASE_COUNT`, но дать им отдельный exact manifest/count, чтобы случайное удаление self-test было видно.

## 6. Проверка кодером

Из свежего shell, два последовательных прогона после последнего edit:

```bash
bash -n infra/production/solarsage-github-deploy \
  scripts/tests/test-prod-github-wrapper.sh
timeout 120 bash scripts/tests/test-prod-github-wrapper.sh
timeout 120 bash scripts/tests/test-prod-github-wrapper.sh
git diff --check
```

Не писать `accepted`/`independent`. Сообщить exact product/self-test counts, rc, изменённые файлы и остановиться для архитекторского review.
