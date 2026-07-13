# Stage 2.W2C-1 R2 — exact ESLint negative-rule assertions

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`d50f0268efe6c5c9ea88e7c6bc1cc12f85fdfc6e`
Parents:

- `141_STAGE_2_W2C_GRACE_ACTIVE_SLICE_SUBWAVE_MASTER_TZ.md`;
- `142_STAGE_2_W2C1_APP_PAGES_TRUTHFUL_GRACE_PREAMBLES_TZ.md`;
- `143_STAGE_2_W2C1_R1_SELF_CONTAINED_GRACE_NEGATIVE_HARNESS_TZ.md`.

Статус: **MANDATORY REVIEW REPAIR — NO COMMIT/PUSH**

## 1. Архитекторское решение

R1 пока не принят к коммиту.

Синтетический marker baseline и четыре точных marker-case реализованы верно:

```text
NEG-MARK-1 -> GRC001
NEG-MARK-2 -> GRC004
NEG-MARK-3 -> GRC030
NEG-MARK-4 -> GRC031
```

Но два ESLint-case всё ещё используют общий helper, который считает успехом
**любой** ненулевой exit code. Поэтому harness способен снова дать ложный PASS
при parser/config/module-resolution ошибке, не доказав работу нужного GRACE
правила. Такой ложноположительный сценарий уже был фактически обнаружен в R1:
временные TypeScript-файлы содержали `#`-комментарии и падали на parser error.

Нужно сделать ESLint-половину harness такой же строгой, как marker-половина:
case проходит только по своему точному rule ID и штатному lint exit code.

## 2. Замороженное принятое состояние

Не изменять ни одного байта в 14 app pages из 142:

```text
app/(grace)/calendar/page.tsx
app/(grace)/chat/page.tsx
app/(grace)/checkin/page.tsx
app/(grace)/debug/page.tsx
app/(grace)/onboarding/page.tsx
app/(grace)/page.tsx
app/(grace)/profile/page.tsx
app/(grace)/readings/horary/[id]/page.tsx
app/(grace)/readings/horary/page.tsx
app/(grace)/readings/natal/[id]/page.tsx
app/(grace)/readings/natal/generating/page.tsx
app/(grace)/readings/natal/page.tsx
app/(grace)/readings/page.tsx
app/(grace)/today/page.tsx
```

Также сохранить без смысловых изменений уже принятую R1-архитектуру в
`scripts/grace/check-negative.sh`:

- self-contained synthetic pilot под `$WORK`;
- изолированный временный `grace/frontend.paths`;
- clean marker baseline до отрицательных мутаций;
- exact marker codes `GRC001`, `GRC004`, `GRC030`, `GRC031`;
- все временные output-файлы под `$WORK`;
- валидные `//`-комментарии в TypeScript ESLint fixtures;
- итоговое количество case: ровно 6.

Docs 141–144 кодер не редактирует.

## 3. Exact edit scope

Редактировать только:

```text
scripts/grace/check-negative.sh
```

Нельзя редактировать:

- 14 app pages;
- `eslint.config.mjs`;
- `eslint-rules/grace-plugin.mjs`;
- `grace/frontend.paths`;
- package/config/contract/product/test files;
- любые docs;
- любые runtime/systemd/nginx/env файлы.

No commit. No push. No stash/reset/rebase/force. Index должен остаться пустым.

Итоговый tracked implementation scope W2C-1 после R2 остаётся exact 15 paths:
14 замороженных pages + `scripts/grace/check-negative.sh`.

## 4. Mandatory preflight

До правки:

1. полностью прочитать 141, 142, 143 и 144;
2. проверить branch/local/tracking/remote/main invariants из 142;
3. проверить, что tracked diff состоит ровно из принятых 15 implementation paths;
4. проверить пустой index;
5. сохранить hashes всех 14 pages и доказать их неизменность после R2;
6. сохранить текущий script в `/tmp/stage2-w2c1-r2-negative-before.sh`;
7. воспроизвести текущий `pass=6 fail=0`;
8. явно зафиксировать по исходнику, что текущий generic `report()` проверяет
   только zero/non-zero и не ищет ESLint rule ID;
9. подтвердить неизменность canonical services и отсутствие listeners на
   `3003`, `8001`, `18092`.

Стоп при любом несовпадении. Ничего не чинить за пределами exact scope.

## 5. Требуемая реализация

Заменить generic ESLint report semantics на отдельный строгий helper, например:

```bash
report_eslint() {
  local name="$1"
  local expected_rule="$2"
  local expected_fail_cmd="$3"
  local output="$WORK/eslint-negative-$((pass + fail + 1)).out"

  eval "$expected_fail_cmd" > "$output" 2>&1
  local rc=$?

  # дальнейшая строгая классификация результата
}
```

Имя helper может отличаться, но контракт обязателен.

### 5.1. Строгий контракт helper

Для каждого ESLint negative-case helper должен:

1. выполнить команду ровно один раз и сохранить stdout/stderr в отдельный файл
   под `$WORK`;
2. сохранить фактический exit code, не потеряв его через `if`, pipe или `!`;
3. считать exit `0` как `UNEXPECTED PASS`;
4. считать любой exit, отличный от `1`, как неправильную причину падения;
   ESLint exit `2` означает config/internal failure и не доказывает правило;
5. при exit `1` потребовать точное вхождение ожидаемого rule ID через literal
   match (`grep -F` или эквивалент), а не общий текст `grace`;
6. отдельно отклонить `Parsing error`, даже если формат вывода когда-либо
   позволит ему соседствовать с другим сообщением;
7. увеличить `pass` только когда одновременно выполнены условия:

   ```text
   exit code == 1
   exact expected rule ID is present
   no Parsing error
   ```

8. при неправильной причине вывести captured output с префиксом
   `[grace-negative]   ` и увеличить `fail`;
9. в success message напечатать точный rule ID, например:

   ```text
   [grace-negative] NEG-LINT-1 (...): ok (caught by grace/contracts-only-import)
   ```

Generic helper, который принимает любой non-zero как PASS, удалить или оставить
неиспользуемым нельзя: после R2 в script не должно остаться misleading dead
helper с ослабленной семантикой.

## 6. Exact ESLint case mapping

Вызовы должны быть ровно такими по смыслу:

```text
NEG-LINT-1
fixture: foreign import of TodayPayload
expected rule: grace/contracts-only-import

NEG-LINT-2
fixture: local redeclare of TodayPayload
expected rule: grace/no-redeclare-contract-types
```

Не менять сами нарушения и не ослаблять правила. Не добавлять unrelated
violations специально для получения non-zero.

Обе команды продолжают lint-ить по одному временному файлу:

```text
lib/api/foreign-import.ts
lib/api/local-redeclare.ts
```

## 7. Обязательная проверка harness

Сначала:

```bash
bash -n scripts/grace/check-negative.sh
bash scripts/grace/check-negative.sh
```

Ожидается exit `0` и смысловой вывод:

```text
clean marker baseline PASS
NEG-MARK-1 ... caught by GRC001
NEG-MARK-2 ... caught by GRC004
NEG-MARK-3 ... caught by GRC030
NEG-MARK-4 ... caught by GRC031
NEG-LINT-1 ... caught by grace/contracts-only-import
NEG-LINT-2 ... caught by grace/no-redeclare-contract-types
pass=6 fail=0
```

Дополнительно по diff/source доказать:

```text
generic any-nonzero ESLint acceptance absent
ESLint rc == 1 required
exact expected rule token required
Parsing error rejected
```

## 8. Полный continuation gate

После успешного harness повторить все acceptance gates, потому что это
последняя правка перед архитектурным принятием W2C-1.

### 8.1. GRACE tooling and exact 14-page slice

```bash
python3 scripts/test_grace_front_lint.py
python3 scripts/grace_front_lint.py \
  'app/(grace)/calendar/page.tsx' \
  'app/(grace)/chat/page.tsx' \
  'app/(grace)/checkin/page.tsx' \
  'app/(grace)/debug/page.tsx' \
  'app/(grace)/onboarding/page.tsx' \
  'app/(grace)/page.tsx' \
  'app/(grace)/profile/page.tsx' \
  'app/(grace)/readings/horary/[id]/page.tsx' \
  'app/(grace)/readings/horary/page.tsx' \
  'app/(grace)/readings/natal/[id]/page.tsx' \
  'app/(grace)/readings/natal/generating/page.tsx' \
  'app/(grace)/readings/natal/page.tsx' \
  'app/(grace)/readings/page.tsx' \
  'app/(grace)/today/page.tsx'
```

Expected: self-tests `11 PASS`; explicit slice `PASS — 14 file(s) clean`.

### 8.2. Frontend static gates

```bash
pnpm lint
pnpm typecheck
```

Expected: zero errors and zero warnings; typecheck PASS.

### 8.3. Targeted regression suite

Повторить те же 5 файлов / 31 тест из R1:

```bash
npx vitest run \
  __tests__/app/checkin-page.test.tsx \
  __tests__/app/today-redirect.test.ts \
  __tests__/horary/horary-error-state.test.tsx \
  __tests__/natal/natal-component-states.test.tsx \
  __tests__/natal/natal-no-english.test.tsx
```

Expected: 5 files / 31 tests PASS.

### 8.4. Full active-slice marker diagnostic

Сохранить полный output и доказать ровно:

```text
violations=32
failing_paths=27
green_paths=20
checked_paths=47
app/(grace) failing paths=0
remaining prefixes only:
  components/grace
  lib/api
  lib/grace
```

Любое другое число или префикс — STOP, без самостоятельного расширения scope.

### 8.5. Frontend aggregate guardrail

Запустить диагностически:

```bash
pnpm guardrails:frontend
```

Допустим только прежний ожидаемый non-zero из-за того же exact marker
remainder `32/27/20/47`, после успешных ESLint/typecheck/negative sections.

## 9. Final scope and integrity proof

Перед callback:

1. hashes всех 14 pages равны preflight hashes;
2. их body/comment-only equivalence остаётся принятой из R1;
3. единственный R2 diff — `scripts/grace/check-negative.sh`;
4. combined tracked implementation scope — exact 15 paths;
5. `git diff --check` PASS;
6. index empty;
7. docs 141–144 не изменялись кодером;
8. frozen unrelated paths не тронуты и не staged:

   ```text
   .grace/
   artifacts/design/
   docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
   grace.db
   skills/
   ```

9. canonical API/sidecar/frontend/nginx state unchanged;
10. ports `3003`, `8001`, `18092` absent;
11. commit/push not performed.

## 10. Required callback

Вернуть один итоговый callback:

```text
READY_STAGE_2_W2C1_R2_EXACT_NEGATIVE_RULES_REVIEW
tracked_scope: EXACT_15
r2_edit_scope: scripts/grace/check-negative.sh_ONLY
app_pages_hashes: UNCHANGED_14
negative_clean_baseline: PASS
negative_cases: 6_PASS_0_FAIL
marker_exact_codes: GRC001_GRC004_GRC030_GRC031
eslint_exact_rules: grace/contracts-only-import_AND_grace/no-redeclare-contract-types
eslint_exit_contract: EXACT_1
parser_error_rejection: PRESENT
generic_any_nonzero_acceptance: ABSENT
grace_linter_self_tests: 11_PASS
authorized_paths_grace: PASS_14
eslint: PASS_ZERO
typecheck: PASS
targeted_tests: 5_FILES_31_PASS
remaining_grace: 32_VIOLATIONS_27_FAILING_20_GREEN_47_CHECKED
remaining_prefixes: COMPONENTS_LIB_API_LIB_GRACE_ONLY
guardrails_frontend: EXPECTED_MARKER_REMAINDER_ONLY
git_diff_check: PASS
index: EMPTY
commit_push: NOT_PERFORMED
runtime_services: UNCHANGED
ports: 3003/8001/18092_ABSENT
```

После callback остановиться. W2C-2 не начинать.
