# Review: Horary questions implementation vs docs/16_Horary_questions_TZ.md

Date: 2026-06-09
Status: BLOCKED — implementation is green, but not compliant with the current TZ.

## Executive summary

The feature appears to compile and tests may be green, but the implementation is still based on the old quota model:

```text
HoraryQuota.questions_used / questions_limit
initial 3 free questions
+1 accumulating question every 7 days
left / nextInDays frontend quota model
```

The current TZ explicitly forbids this model and requires the new credit-ledger model:

```text
subscription_weekly_free
referral_bonus
gift
paid
adjustment
```

with weekly-free expiry, paid persistence, deterministic spend order, idempotency, and atomic spend transactions.

This review should be treated as a rework packet, not as a cosmetic cleanup.

---

## Reviewed sources

Primary TZ:

- `docs/16_Horary_questions_TZ.md`

Implementation files inspected:

- `apps/api/app/schemas/horary.py`
- `apps/api/app/services/horary_service.py`
- `apps/api/app/db/models.py`
- `apps/api/app/api/horary.py`
- `apps/api/app/main.py`
- `scripts/contracts/export_openapi.py`
- `apps/api/tests/test_horary_endpoints.py`
- `lib/contracts/horary.ts`
- `lib/api/horary.ts`
- `components/readings/horary/horary-screen.tsx`
- `components/readings/horary/horary-form.tsx`
- `components/readings/horary/horary-quota-bar.tsx`

---

# Blockers

## B1. Old `HoraryQuota` model is still the core backend model

Current code uses:

```python
class HoraryQuota(Base):
    __tablename__ = "horary_quotas"
    questions_used
    questions_limit = 3
    reset_at
```

and `HoraryService.get_or_create_quota()` creates an initial quota of 3 questions, then adds +1 every 7 days.

This directly violates TZ section `16.8 Deprecated model forbidden`:

```text
HoraryQuota.questions_used
HoraryQuota.questions_limit
left / nextInDays as primary quota model
default 3 free questions
+1 accumulating question every 7 days
weekly_bonus as a source
```

Required rework:

- Remove `HoraryQuota` as primary balance model.
- Add `horary_credits` ledger.
- Add `horary_credit_spends` ledger.
- Implement `subscription_weekly_free` lazy resolution.
- Keep old `horary_quotas` only as temporary migration artifact if needed, not as live business source.

---

## B2. Missing `horary_credits` and `horary_credit_spends` tables

TZ requires:

```text
horary_credits
- source: subscription_weekly_free / referral_bonus / gift / paid / adjustment
- amount
- used_amount
- access_week_start
- access_week_end
- expires_at
```

and:

```text
horary_credit_spends
- credit_id
- question_id
- amount
- idempotency_key
```

Current DB models have only:

- `HoraryQuestion`
- `HoraryAnswer`
- `HoraryQuota`

No credit ledger exists, so the following TZ rules cannot be implemented:

- weekly-free expiry;
- paid credits persistence;
- gift/referral expiry;
- deterministic spend order;
- atomic no-double-spend ledger;
- refund/compensation policy.

Required rework:

- Add ORM models:
  - `HoraryCredit`
  - `HoraryCreditSpend`
- Add Alembic migration for those tables.
- Add all constraints from TZ section 16.4.

---

## B3. API contract still exposes `left` / `nextInDays`

Current backend schema:

```python
class HoraryQuotaRead(CamelModel):
    left: int
    next_in_days: int
    can_purchase: bool = True
```

Current frontend Zod schema mirrors it:

```ts
export const HoraryQuotaSchema = z.object({
  left: z.number(),
  nextInDays: z.number(),
  canPurchase: z.boolean(),
})
```

TZ requires:

```ts
export type HoraryQuotaRead = {
  weeklyFreeAvailable: boolean
  weeklyFreeExpiresAt?: string
  nextWeeklyFreeAt?: string
  bonusCredits: number
  paidCredits: number
  canPurchase: boolean
}
```

Required rework:

- Replace backend `HoraryQuotaRead` shape.
- Regenerate OpenAPI and TS contracts.
- Replace frontend `HoraryQuotaSchema`.
- Remove `left` / `nextInDays` from primary horary balance logic.

---

## B4. Frontend is still driven by `left` / `nextInDays`

Current UI:

- `HoraryQuotaBar` destructures `{ left, nextInDays }`.
- `HoraryScreen` shows form only when `quota.left > 0`.
- `HoraryForm` accepts `left` and disables submit with `left > 0`.

This violates TZ section 16.8:

```text
Frontend must render quota from:
weeklyFreeAvailable
weeklyFreeExpiresAt
nextWeeklyFreeAt
bonusCredits
paidCredits
canPurchase
```

Required rework:

- Replace UI gating with computed `hasSpendableCredit`:

```ts
const hasSpendableCredit =
  quota.weeklyFreeAvailable || quota.bonusCredits > 0 || quota.paidCredits > 0
```

- Update quota bar copy:
  - weekly-free available / used / expires at;
  - paid credits;
  - bonus/gift/referral credits.

---

## B5. No idempotency implementation

TZ requires `idempotencyKey` in request and `request_hash` on `horary_questions`.

Current `HoraryQuestionCreate` has no `idempotency_key` / `idempotencyKey`.

Current `HoraryQuestion` model has no:

- `idempotency_key`
- `request_hash`
- unique `(user_id, idempotency_key)`

Current create flow cannot prevent double-spend on duplicate submit.

Required rework:

- Add `idempotency_key` and `request_hash` to `HoraryQuestion`.
- Add unique index on `(user_id, idempotency_key)`.
- Implement behavior:
  - same key + same request hash → return existing question;
  - same key + different request hash → `409 IDEMPOTENCY_CONFLICT`;
  - no second spend.
- Add tests for both cases.

---

## B6. Spend is not atomic and generation starts before API commit

Current service:

```python
quota.questions_used += 1
await self.db.flush()
asyncio.create_task(self._generate_answer_task(question_id))
```

The API commits only after `create_question()` returns.

That means background generation can start before the request transaction is committed.

TZ requires:

```text
1. Begin transaction.
...
10. Commit.
11. Start async generation only after commit.
```

Required rework:

- Move generation start outside the spend transaction.
- Ensure spend transaction commits before generation starts.
- Prefer route-level orchestration:

```python
question = await service.create_question_atomic(...)
await db.commit()
service.enqueue_generation_after_commit(question.id)
```

- If using background task in FastAPI, schedule only after commit.

---

## B7. No deterministic spend order

Current implementation only checks:

```python
quota.questions_used < quota.questions_limit
```

There is no concept of:

1. active `subscription_weekly_free`;
2. expiring `referral_bonus` / `gift` / `adjustment`;
3. `paid` oldest first.

Required rework:

- Implement `HoraryCreditService` with:
  - `resolve_current_weekly_free(user_id, now)`;
  - `get_spendable_credits(user_id, now)`;
  - `select_credit_for_spend(user_id, now)`;
  - `spend_credit_for_question(...)`.
- Lock candidate credits with `FOR UPDATE` where supported.
- For SQLite tests, keep semantics equivalent even if `FOR UPDATE` is ignored.

---

## B8. Paid credits without active Today access are not supported

TZ says paid/gift/referral/adjustment horary credits may be spent even if Today access is expired, as long as the credit itself is not expired.

Current model has no paid credits at all, so this rule cannot be satisfied.

Required rework:

- Add paid credit rows.
- Add tests:
  - no active access + paid credit → POST question succeeds;
  - no active access + no credits → `NO_HORARY_CREDITS`.

---

## B9. Failure/refund policy is not implemented

Current generation failure sets question to `expired`.

TZ requires:

- generation failure before answer → `failed`;
- paid/gift/referral/adjustment credit must be refunded/compensated;
- weekly-free restored only if the same access-week is still active;
- successful answer → no automatic refund.

Required rework:

- Add statuses `failed` and `refunded` to backend and frontend contracts.
- Add refund/compensating spend logic.
- Add tests for failure refund behavior.

---

# Major issues

## M1. Tests prove the old behavior, not the TZ behavior

Current tests assert old behavior:

```python
assert body["left"] == 3
assert body["nextInDays"] == 7
```

and quota drain with:

```python
quota.questions_used = 3
```

These tests are now harmful because they lock in forbidden behavior.

Required rework:

- Rewrite horary quota tests around `horary_credits`.
- Add all tests listed in TZ section 16.9.
- Remove tests that assert `left == 3` or `questions_used/questions_limit`.

---

## M2. Status contract is outdated

TZ API contract allows:

```text
pending / processing / answered / failed / refunded / expired
```

Current backend and frontend schemas only expose:

```text
pending / processing / answered / expired
```

Required rework:

- Update Pydantic schema.
- Update Zod schema.
- Update generated contracts.
- Update UI handling for `failed` / `refunded`.

---

## M3. `spentCreditSource` is missing from API response

TZ response includes:

```ts
spentCreditSource?: "subscription_weekly_free" | "referral_bonus" | "gift" | "paid" | "adjustment"
```

Current `HoraryQuestionRead` does not include it.

Required rework:

- Store `spent_credit_id` on question.
- Join/load spent credit source in API response.
- Add frontend display only if useful; at minimum keep it in contract.

---

## M4. `question_lat` / `question_lon` are accepted but frontend never sends them

Backend and schema accept `questionLat/questionLon`, but `HoraryScreen.handleSubmit()` sends only:

```ts
text
category
clientTimezone
clientLocalTime
```

Current behavior falls back to profile current/birth coordinates. That is acceptable for MVP only if explicitly intended, but the form does not expose or pass question location.

Required decision:

- Either document that MVP uses profile current location only;
- or add UI location capture / pass-through.

---

## M5. No clear migration found for current new tables

A direct fetch for `apps/api/alembic/versions/0012_add_horary.py` returned not found, and search did not show a horary migration file. The implementation may have a differently named migration, but this review could not verify it from repository search.

Required rework:

- Confirm actual migration file path/name.
- Ensure migration creates the new credit-ledger tables, not just `horary_quotas`.
- Use `batch_alter_table` where SQLite compatibility is needed.

---

# What is acceptable / already useful

These parts can be kept:

- Router is mounted in `apps/api/app/main.py`.
- Basic horary routes exist.
- Basic ownership check exists for `GET /api/horary/questions/{id}`.
- Pydantic and frontend block schemas include `verdict_card` and `timing`.
- Frontend route and polling flow exist.
- LLM narration is separated from deterministic engine directionally.
- Existing tests are useful as smoke tests after they are rewritten to the new quota model.

---

# Required rework plan

## Step 1. Replace quota model with credit ledger

Create:

- `HoraryCredit`
- `HoraryCreditSpend`

Remove live dependency on:

- `HoraryQuota.questions_used`
- `HoraryQuota.questions_limit`
- `HoraryQuota.reset_at`

## Step 2. Implement `HoraryCreditService`

Required methods:

```python
resolve_current_access_week(user_id, now) -> AccessWeek | None
get_or_create_current_weekly_free(user_id, now) -> HoraryCredit | None
get_balance(user_id, now) -> HoraryQuotaRead
select_spendable_credit(user_id, now) -> HoraryCredit | None
spend_for_question(user_id, question_id, idempotency_key, now) -> HoraryCreditSpend
refund_spend(spend_id, reason) -> None
```

## Step 3. Rewrite `POST /api/horary/questions`

Required flow:

```text
1. Validate idempotency.
2. Begin transaction.
3. Resolve/create current weekly-free if active access exists.
4. Lock spendable credits.
5. Select by spend order.
6. If no credit: 402 NO_HORARY_CREDITS.
7. Create question(status=processing, request_hash, idempotency_key).
8. Create credit spend.
9. Increment used_amount.
10. Commit.
11. Start generation after commit.
```

## Step 4. Rewrite API/TS quota contract

Backend and frontend must use:

```ts
weeklyFreeAvailable
weeklyFreeExpiresAt
nextWeeklyFreeAt
bonusCredits
paidCredits
canPurchase
```

No `left` / `nextInDays` as primary model.

## Step 5. Rewrite frontend gating

Use:

```ts
const hasSpendableCredit =
  quota.weeklyFreeAvailable || quota.bonusCredits > 0 || quota.paidCredits > 0
```

## Step 6. Rewrite tests

Remove tests asserting:

- `left == 3`
- `nextInDays == 7`
- `questions_used/questions_limit`

Add mandatory TZ tests:

1. weekly-free created only for current access-week;
2. future weeks do not pre-create credits;
3. unused weekly-free expires at `access_week_end`;
4. boundary at exactly `access_week_end`;
5. next week has exactly one new weekly-free, not accumulated;
6. paid credits can be spent without active Today access;
7. paid credit is not spent while weekly-free is available;
8. expired gift/referral credits are ignored;
9. nearest `expires_at` bonus credit is spent before paid;
10. duplicate idempotency key does not double-spend;
11. same idempotency key with different request hash returns 409;
12. generation failure refunds paid credit;
13. generation failure restores weekly-free only if access-week is still active;
14. frontend does not use `left` / `nextInDays` as primary balance.

---

# Suggested acceptance gate before saying "done"

Do not accept the feature until all are true:

```text
- grep -R "questions_used\|questions_limit\|HoraryQuota\|left\|nextInDays" apps/api lib components packages/contracts
  returns no live primary quota usage for horary.

- grep -R "subscription_weekly_free" apps/api
  finds model, service, tests, and migration usage.

- tests include idempotency, spend order, weekly expiry, paid-without-access, and failure refund cases.

- API response for /api/horary/quota contains weeklyFreeAvailable, bonusCredits, paidCredits.

- frontend gating uses weeklyFreeAvailable || bonusCredits > 0 || paidCredits > 0.
```

---

# Review verdict

Current state: **not compliant with docs/16_Horary_questions_TZ.md**.

The feature is functionally present, but it implements the previous quota concept. The next coder pass should be a focused rework from quota-counter model to credit-ledger model.
