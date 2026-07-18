# R13 Phase B4 R2 — last false-green fix

Прочитать `71_REVIEW_R13_PHASE_B4_R1_REJECTED_TWO_FALSE_GREEN_ASSERTIONS.md`. Это последний узкий wrapper pass.

## Scope

Менять только `scripts/tests/test-prod-github-wrapper.sh`. Production wrapper не менять. Production/network/SSH/GitHub/commit/push запрещены.

## Required changes

1. Построить non-hex SHA из canonical value заменой, а не append:

```bash
NONHEX_SHA="${DEP_SHA%?}g"
```

До cases assert:

- `${#NONHEX_SHA} == 40`;
- значение содержит `g`;
- не соответствует `^[0-9a-f]{40}$`;
- short/long cases остаются отдельными.

2. Вынести canonical output check в reusable helper с function contract. Он должен уметь вернуть non-zero и symbolic reason, не завершать процесс напрямую. `run_case` использует его для exact stdout/stderr contract.

3. Self-test 10:

- mutation пишет raw `SSH_ORIGINAL_COMMAND`;
- вызывается тот же reusable output validator;
- validator обязан вернуть non-zero с ожидаемой leak/mismatch reason;
- если validator вернул 0, harness падает;
- удалить exception `*/self10*) continue`;
- удалить intentional self10 stdout/stderr до финального global scan либо хранить их вне scanned directory после доказанного non-zero;
- не печатать raw content.

4. `run_self_test` сразу reject invalid/duplicate IDs. Финальный exact manifest сохранить.

5. Path mutation self-proof должен реально добавить canonical comment decoy и вызвать тот же executable-path validator, что canonical path substitution. Не дублировать упрощённую альтернативную логику. Если reusable extraction требует небольшого refactor — сделать его, не меняя production wrapper.

6. Удалить неиспользуемый `BASELINE_DIR` или задействовать его по реальному контракту.

## Verification

После последнего edit дважды:

```bash
bash -n infra/production/solarsage-github-deploy scripts/tests/test-prod-github-wrapper.sh
timeout 120 bash scripts/tests/test-prod-github-wrapper.sh
timeout 120 bash scripts/tests/test-prod-github-wrapper.sh
git diff --check
```

Сообщить exact counts/rc и остановиться. Не писать independent/accepted.
