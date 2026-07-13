# S1.W3 Architect Review R4 — final truthful-contract cleanup

Дата: 2026-07-11
Вердикт: `FINAL_MICRO_FIX_REQUIRED`
Commit/push: запрещены.

Логика S1.W3 принята. Исправить только три оставшихся расхождения между
callback и фактическим index.

## 1. Shell comments/contracts

`scripts/contracts/today_fixture.sh` всё ещё содержит:

```text
otherwise forward args
failure_policy: exit 1 on error
```

Оба утверждения неверны. Заменить на:

```text
canonical fixture only; accepts no args or exactly --check
usage error -> exit 2; otherwise propagates normalizer non-zero status
```

`scripts/contracts/check.sh`:

```text
failure_policy: propagates the first non-zero generator, fixture-check, or diff status
```

Не менять уже правильное shell behavior.

## 2. Manual initializer regex сделать shape-based, а не type-name-based

Текущий regex ловит только:

```ts
dayPayloadV2: TodayPayload = {
```

и пропустит `dayPayloadV2 = {` или другой annotation.

Использовать guard вида:

```ts
/dayPayloadV2[^=]*=\s*\{/
```

или эквивалентный, который запрещает любой manual object initializer, но не
запрещает текущий `= TodayPayloadWireSchema.parse(...)`.

## 3. Удалить мёртвый `expectedMatch` и сделать raw-payload assertion точным

В isolation guard удалить неиспользуемый `expectedMatch`.

В Python test вместо повторного sentinel assertion вычислить serialized
payload тем же `json.dumps`, которым он записан, и проверить, что вся строка не
встречается ни в stdout, ни в stderr. Sentinel assertions сохранить.

## 4. Проверки

```bash
npx vitest run \
  __tests__/guardrails/preview-isolation.test.ts \
  __tests__/contracts/today-fixture-roundtrip.test.ts

cd apps/api && .venv/bin/python -m pytest tests/test_today_fixture_contract.py -q

cd /opt/solarsage-astro
npx tsc --noEmit
git diff HEAD --check
git diff --cached --check

rg -n 'otherwise forward args|failure_policy: exit 1 on error|const expectedMatch|dayPayloadV2\\s\*:\\s\*TodayPayload' \
  scripts/contracts/today_fixture.sh \
  scripts/contracts/check.sh \
  __tests__/guardrails/preview-isolation.test.ts \
  __tests__/contracts/today-fixture-roundtrip.test.ts
```

Ожидается 0 matches. Stage этот doc. Два PNG оставить unstaged. Commit/push не
делать.

Callback:

```text
READY_S1_W3_FINAL_ACCEPTANCE
shell_contract_scan: 0
manual_initializer_shape_guard: PASS
dead_expected_match: REMOVED
serialized_raw_payload_not_logged: PASS
focused_vitest: PASS
api_fixture_tests: PASS
tsc: PASS
diff_check: PASS
baseline_repair_files_unstaged: 2
s1_w3_binary_files_staged: 0
commit: NOT_YET
push: NOT_YET
```
