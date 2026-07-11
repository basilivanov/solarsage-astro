# S1.W3 Architect Review R3 — bind exact import and finish truthful guards

Дата: 2026-07-11
Вердикт: `CHANGES_REQUIRED_R3`
Commit/push: запрещены.

Приняты в R3:

- `contracts:check` снова выполняет generate → fixture check → generated diff;
- CI использует `python -m pip install -e ./apps/api`;
- normalizer больше не создаёт directories/chown/chmod;
- missing-parent check доказан;
- wrapper exact arity работает;
- allowed import count проверяется как `1`.

Остались четыре точечных исправления.

## 1. Guard всё ещё не связывает `await` с найденным import match

Сейчас:

```ts
const hasExactForm = text.includes(allowedForm)
```

Это global substring search. Если `await import("...")` останется в comment,
а реальный code станет `import("...")`, test может ложно пройти.

Использовать `m.index`, а не `text.indexOf(m[0])`, и связать exact statement с
этим конкретным match. Для текущего фиксированного source допустима строгая
проверка:

```ts
const matchIndex = m.index ?? -1
const expectedMatch = `import("${allowedSpecifier}"`
const hasExactForm =
  matchIndex >= 6
  && m[0] === expectedMatch
  && text.slice(matchIndex - 6, matchIndex) === "await "
```

Если фактический regex match включает иной хвост, адаптировать exact expected
match к реальному `m[0]`, но проверять именно `m.index` и непосредственный
prefix, не `includes`.

Все guard ordering comparisons делать относительно этого же `matchIndex`.

## 2. Single-source test в index не изменён по R2

Сейчас всё ещё:

```ts
file.startsWith("day-v2-")
```

Это запрещает будущую fixture на другую дату. Исправить на текущий stem:

```ts
file.startsWith("day-v2-2026-07-08")
```

и exact result:

```ts
["day-v2-2026-07-08.json"]
```

Добавить реальный manual initializer guard, например regex, который запрещает:

```ts
dayPayloadV2 ... = {
```

но не запрещает текущий:

```ts
dayPayloadV2: TodayPayload = TodayPayloadWireSchema.parse(rawDayPayloadV2)
```

После этого запустить focused test и показать фактический diff этих строк.

## 3. Truthful shell GRACE/comments

`scripts/contracts/today_fixture.sh`:

- comment всё ещё говорит `otherwise forward args`, хотя extra args
  отклоняются;
- `failure_policy: exit 1` неверен: usage возвращает `2`, normalizer может
  вернуть другие non-zero codes.

`scripts/contracts/check.sh`:

- `failure_policy: exit 1` заменить на truthful propagation/non-zero wording.

Код поведения уже правильный; исправить только contracts/comments.

## 4. Python test cleanup

`apps/api/tests/test_today_fixture_contract.py`:

- удалить неиспользуемый `ValidationError`;
- отделить stdlib / third-party imports;
- разнести две длинные timing comprehensions;
- в sanitized error test дополнительно доказать, что serialized raw payload
  целиком не присутствует в stdout/stderr.

Это последний quality cleanup перед acceptance.

## 5. Final focused gates

```bash
npx vitest run \
  __tests__/guardrails/preview-isolation.test.ts \
  __tests__/contracts/today-fixture-roundtrip.test.ts

cd apps/api && .venv/bin/python -m pytest tests/test_today_fixture_contract.py -q

cd /opt/solarsage-astro
pnpm contracts:check
npx tsc --noEmit
git diff HEAD --check
git diff --cached --check

rg -n 'text\.includes\(allowedForm\)|startsWith\("day-v2-"\)|Record<string, any>|\\bas any\\b|as unknown as|@ts-ignore|@ts-expect-error' \
  __tests__/guardrails/preview-isolation.test.ts \
  __tests__/contracts/today-fixture-roundtrip.test.ts
```

Последний `rg` должен дать 0 matches.

Stage этот review doc вместе с остальными S1.W3 docs. Два baseline-repair PNG
по-прежнему оставить unstaged. Никаких commit/push.

## 6. Callback R4

```text
READY_S1_W3_REVIEW_R4
guard_match_index_bound: PASS
guard_global_includes_removed: PASS
fixture_filter_exact_stem: day-v2-2026-07-08
manual_initializer_guard: PASS
shell_grace_truthful: PASS
python_unused_imports: 0
raw_payload_not_logged: PASS
focused_vitest: <count>
api_fixture_tests: <count>
contracts_check: PASS
tsc: PASS
forbidden_rg_matches: 0
baseline_repair_files_unstaged: 2
s1_w3_binary_files_staged: 0
commit: NOT_YET
push: NOT_YET
```
