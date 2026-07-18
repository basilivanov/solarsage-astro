# R13 Phase B4 R1 — rejected: two false-green assertions

## Independent evidence

После последнего edit архитектор выполнил два последовательных запуска:

```text
bash -n -> rc 0
run 1 -> rc 0, 56 product cases + 10 self-tests
run 2 -> rc 0, 56 product cases + 10 self-tests
stderr -> 0 bytes
temp wrapper dirs -> none
git diff --check -> rc 0
```

Phase B4 всё ещё не принята из-за двух точных дефектов ниже. Production/network/SSH/GitHub/commit/push не выполнялись.

## Blocker 1 — advertised 40-char non-hex is 41 bytes

`NONHEX_SHA` около `scripts/tests/test-prod-github-wrapper.sh:737-743` заявлен как replacement последнего символа, но фактически к исходному 40-char shape снова добавлен `g`.

Независимая проверка:

```text
DEP_SHA length = 40
NONHEX_SHA length = 41
```

Поэтому `DEP_N04`/`SRC_N04` не отличают запрет non-hex от запрета long SHA. Построить значение как `${DEP_SHA%?}g` и отдельно assert `length == 40`, содержит `g`, не совпадает с lowercase hex regex.

## Blocker 2 — self-test raw-output validator сам себя исключает

Self-test 10 создаёт stderr с raw SHA (`:690-715`), затем global output scan (`:1003-1023`) делает для `*/self10*` explicit `continue`. В результате:

- mutation действительно выводит raw command;
- harness видит leak;
- но тот validator, который якобы должен leak отвергнуть, сознательно его пропускает;
- self-test печатает PASS без доказанного non-zero validator result.

Вынести reusable `validate_output_file(s)`/`assert_case_output` helper, который возвращает non-zero без выхода из всего harness. `run_case` использует этот helper для canonical cases. Self-test 10 вызывает тот же helper на mutated output и требует non-zero с ожидаемой reason; exception/skip удалить. После self-test его intentional output можно удалить до global clean scan.

## Additional cleanup

- `run_self_test` должен reject duplicate/invalid self-test ID сразу, не полагаться только на финальный sorted comparison.
- Mutation path self-proof comment говорит, что canonical string добавлен в comment, но код его не добавляет. Либо реально добавить comment decoy и прогнать тот же path validator, либо исправить claim. Не писать доказательства, которых код не выполняет.
- `BASELINE_DIR` не используется; удалить либо использовать по контракту.
