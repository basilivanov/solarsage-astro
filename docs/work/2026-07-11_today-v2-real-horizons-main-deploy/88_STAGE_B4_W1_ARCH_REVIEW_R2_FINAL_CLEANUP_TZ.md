# Stage B4.W1 architectural review R2 — final literal cleanup

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Базовый SHA: `1a944717efa7a70124f81cb950992998491bf72e`
Предыдущие ТЗ: `86`, `87`
Статус: **FINAL NARROW CLEANUP — NO COMMIT / NO PUSH**

## 1. Scope

Production behavior и version matrix приняты. Не менять их. Выполнить ровно
пять механических/тестовых поправок ниже, затем повторить gates.

Разрешены только:

~~~text
lib/contracts/today.ts
components/today/why-expanded.tsx
__tests__/components/TodayScreen.v2-downstream.test.tsx
~~~

Остальные три уже изменённых B4.W1 файла оставить без новых правок. Документы
не редактировать. Без subagents, git add/commit/push, W2/W3, 3003, services.

## 2. R2.1 — один `invariants:` в module contract

В `lib/contracts/today.ts` текущий `START_MODULE_CONTRACT` содержит два ключа
`invariants:`: новый на строках около 17 и старый на строках около 24. Это
невалидная/двусмысленная GRACE-разметка.

Оставить один блок `invariants:` в каноническом месте после `emitted_logs` и
объединить в нём все четыре утверждения:

- no manual raw V2 wire schema object declarations;
- `TodayWireIdentitySchema` derived from generated Today meta `.pick()`;
- optional only for legacy adapted artifacts, real adapter always populates;
- missing identity remains unknown/fail-closed.

Порядок полей module contract должен быть:

~~~text
purpose
owns
inputs
outputs
dependencies
side_effects
emitted_logs
invariants
failure_policy
~~~

## 3. R2.2 — исправить смысловую опечатку

В `components/today/why-expanded.tsx` заменить:

~~~text
never infers inferred horizons
~~~

на:

~~~text
never infers horizons
~~~

Никаких иных production-code изменений.

## 4. R2.3 — current-null test закрывает весь negative DOM contract

В test `current pair + horizons=null shows unavailable state` добавить exact
assertions:

~~~text
why-expanded present
why-time-horizon absent
astrology-calculation absent
astrology-calculation-toggle absent
why-today absent
~~~

Существующие unavailable/data-state/data-source/selector=0 assertions сохранить.

## 5. R2.4 — mismatch/missing не маскируются safe whyToday

В обоих тестах:

- `mismatched wire identity with horizons=null...`;
- `missing wire identity with horizons=null...`;

добавить assertion `data-testid="why-today"` absent. Это доказывает, что
имеющийся в canonical V2 safe `whyToday` не подменяет fail-closed state.

Существующие no legacy/no technical/selector=0 assertions сохранить.

## 6. R2.5 — убрать две случайные indentation-регрессии

В старых legacy tests поправить две строки с лишним пробелом перед `expect`:

~~~text
uses the human-only fallback...
does not render a legacy timing container...
~~~

Должна быть обычная локальная indentation, без содержательных изменений.

## 7. Проверки

~~~bash
npx vitest run __tests__/lib/adapt-payload.test.ts __tests__/components/TodayScreen.v2-downstream.test.tsx
pnpm typecheck
npx vitest run __tests__/contracts/generated-runtime.test.ts __tests__/contracts/today-fixture-roundtrip.test.ts
pnpm guardrails:prod
bash scripts/grace/check-markers.sh
git diff --check
git diff --name-only
git diff --cached --name-only
git diff -- packages/contracts/_generated.ts packages/contracts/_generated.zod.ts packages/contracts/openapi.json
~~~

GRACE gate ожидаемо может вернуть только уже подтверждённый unrelated baseline
SyntaxError в `scripts/grace_front_lint.py:588`; не исправлять.

Дополнительно выполнить read-only проверки:

~~~bash
grep -n '^// invariants:' lib/contracts/today.ts
grep -RIn 'never infers inferred\|^[[:space:]]\{5\}expect' components/today/why-expanded.tsx __tests__/components/TodayScreen.v2-downstream.test.tsx
~~~

Ожидается один `invariants:` в contract и пустой второй grep.

## 8. Callback

~~~text
READY_FOR_ARCH_REVIEW_STAGE_B4_W1_R2
changed_now: EXACT_3_PATHS
production_logic: UNCHANGED
today_contract_invariants_blocks: 1
typo: FIXED
current_null_negative_dom: COMPLETE
mismatch_safe_copy_masking: ABSENT
missing_safe_copy_masking: ABSENT
indentation_regressions: FIXED
targeted_vitest: <result>
typecheck: <result>
generated_runtime_tests: <result>
prod_guard: <result>
grace_gate: UNRELATED_BASELINE_ERROR_UNCHANGED
git_diff_check: <result>
generated_diff: EMPTY
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

После callback остановиться.
