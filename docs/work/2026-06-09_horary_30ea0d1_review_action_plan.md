# Review / action plan: Horary credit ledger after commit 30ea0d1

Date: 2026-06-09
Reviewed commit: `30ea0d1416da92ae857a48d7c4e25f2c27ebefb9`
Source TZ: `docs/16_Horary_questions_TZ.md`

## Verdict

Status: **NOT ACCEPTED YET**.

Commit `30ea0d1` is a major improvement over the previous implementation. The old primary quota API (`left / nextInDays`) was replaced by the new credit-ledger-facing API, the frontend gating was moved to `weeklyFreeAvailable || bonusCredits > 0 || paidCredits > 0`, and the backend now has `HoraryCreditService` with spend-order logic.

However, the implementation still has several acceptance blockers. The remaining issues are not cosmetic: they can cause duplicate background generations, wrong idempotency behavior for horary-specific timing changes, and credit refund races.

Do not announce this feature as complete until blockers B1–B3 are fixed and covered by tests.

---

# What is now good

## G1. New quota response shape exists

`HoraryQuotaRead` now uses the TZ shape:

```python
weekly_free_available: bool
weekly_free_expires_at: str | None
next_weekly_free_at: str | None
bonus_credits: int
paid_credits: int
can_purchase: bool
```

This matches the direction from `docs/16_Horary_questions_TZ.md`.

## G2. Credit ledger service exists

`HoraryCreditService` exists and covers:

- resolving current access week;
- lazy creation of current `subscription_weekly_free`;
- balance calculation;
- spendable credit selection;
- spend order: weekly-free → bonus/gift/adjustment → paid.

## G3. Frontend no longer gates by `left`

The horary screen computes:

```ts
const hasSpendableCredit =
  quota.weeklyFreeAvailable || quota.bonusCredits > 0 || quota.paidCredits > 0
```

This matches the required frontend model.

## G4. Idempotency primitives were added

`HoraryQuestionCreate` now requires `idempotencyKey` and `HoraryQuestion` stores `idempotency_key` and `request_hash`.

## G5. Generation is now started after commit

The router commits the create/spend transaction before enqueueing the background generation task. This fixes the earlier issue where generation could start before the DB transaction was committed.

---

# Blockers

## B1. Repeated idempotent submit can enqueue duplicate generation

### Problem

`HoraryService.create_question()` returns an existing question when the same user submits the same `idempotency_key` and the same `request_hash`.

That is correct.

But the router then does:

```python
if question.status == "processing":
    asyncio.create_task(service._generate_answer_task(question.id))
```

This means a repeated idempotent submit of an already-processing question will enqueue a second background generation task for the same question.

### Why this is dangerous

Possible outcomes:

- duplicate calls to SolarSage / LLM;
- race on `horary_answers.question_id` unique constraint;
- one task succeeds, another fails and may mark the same question as failed;
- confusing logs and credit/refund edge cases.

### Required fix

Change `create_question()` to return whether the question was newly created.

Recommended shape:

```python
@dataclass(frozen=True)
class CreateHoraryQuestionResult:
    question: HoraryQuestion
    created: bool
```

or simpler:

```python
return question, created
```

Expected logic:

```python
existing = ...
if existing and existing.request_hash == request_hash:
    return CreateHoraryQuestionResult(question=existing, created=False)

# new question path
return CreateHoraryQuestionResult(question=question, created=True)
```

Router must enqueue generation only for new rows:

```python
result = await service.create_question(user_id, body, now)
await db.commit()

if result.created and result.question.status == "processing":
    asyncio.create_task(service._generate_answer_task(result.question.id))

return _to_question_read(result.question)
```

### Required test

Add endpoint/service test:

```text
Given user has a paid credit
When POST /api/horary/questions is called twice with same idempotencyKey and same payload
Then both responses return the same question id
And only one credit spend row exists
And background generation is enqueued only once
```

Implementation hint for enqueue test:

- patch `asyncio.create_task` in `app.api.horary`;
- call the endpoint twice;
- assert `create_task.call_count == 1`.

---

## B2. `request_hash` is incomplete and ignores horary-critical fields

### Problem

Current hash is based only on:

```python
payload_str = f"{data.text}:{data.category or ''}"
request_hash = sha256(payload_str).hexdigest()
```

But for horary, the exact time and place of the question are core business inputs.

The request schema includes:

```python
text
category
client_timezone
client_local_time
question_lat
question_lon
idempotency_key
```

At minimum, the business payload hash must include all fields except `idempotency_key`.

### Broken scenario

1. User submits:

```json
{
  "text": "Will I get the job?",
  "category": "career",
  "clientTimezone": "Europe/Moscow",
  "clientLocalTime": "2026-06-09T10:00:00",
  "idempotencyKey": "abc"
}
```

2. Client retries incorrectly with the same key but different time:

```json
{
  "text": "Will I get the job?",
  "category": "career",
  "clientTimezone": "Europe/Moscow",
  "clientLocalTime": "2026-06-09T10:30:00",
  "idempotencyKey": "abc"
}
```

Current code treats it as the same request because only text/category are hashed.

For horary, this is wrong: the moment of the question matters.

### Required fix

Use canonical JSON hashing:

```python
payload_for_hash = {
    "text": data.text,
    "category": data.category,
    "client_timezone": data.client_timezone,
    "client_local_time": data.client_local_time,
    "question_lat": data.question_lat,
    "question_lon": data.question_lon,
}
request_hash = hashlib.sha256(
    json.dumps(payload_for_hash, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
).hexdigest()
```

Do not include `idempotency_key` in the payload hash. It is the lookup key, not business payload.

### Required tests

```text
Same idempotencyKey + same full payload returns existing question.
Same idempotencyKey + different clientLocalTime returns 409 IDEMPOTENCY_CONFLICT.
Same idempotencyKey + different questionLat/questionLon returns 409 IDEMPOTENCY_CONFLICT.
Same idempotencyKey + different clientTimezone returns 409 IDEMPOTENCY_CONFLICT.
```

---

## B3. TTL failure/refund can race with late successful generation

### Problem

`_check_lazy_ttl()` marks a processing question as `failed` after 5 minutes and refunds the credit.

But `_generate_answer_task()` does not re-check the current question status before writing the answer.

A late generator can still save an answer and set the question back to `answered` after the credit has already been refunded.

### Broken scenario

```text
1. Question is processing.
2. Generator is slow.
3. User opens question after 5 minutes.
4. _check_lazy_ttl() marks question failed and refunds credit.
5. Old generator finishes successfully.
6. It creates HoraryAnswer and sets status=answered.
7. User got answer, but the credit was refunded.
```

### Required fix

Before saving `HoraryAnswer`, reload and lock the question row inside the generator session:

```python
fresh = (
    await db.execute(
        select(HoraryQuestion)
        .where(HoraryQuestion.id == question_id)
        .with_for_update()
    )
).scalar_one_or_none()

if not fresh or fresh.status != "processing":
    logger.info("Skipping horary answer save because question is no longer processing")
    await db.rollback()
    return
```

Then save answer against `fresh`, not a stale earlier object.

### Required test

Service-level test:

```text
Given a processing question with a spent paid credit
And _check_lazy_ttl marks it failed and refunds the credit
When a stale generation task later attempts to save an answer
Then no HoraryAnswer is created
And question remains failed
And credit remains refunded
```

Simpler first-pass test is acceptable: mock/patch the generator save boundary and assert it refuses to save when status is already `failed`.

---

# Major issues

## M1. Legacy `HoraryQuota` table/model still exists

### Problem

`HoraryQuota` still exists in ORM:

```python
class HoraryQuota(Base):
    __tablename__ = "horary_quotas"
    questions_used
    questions_limit = 3
    reset_at
```

Migration also creates `horary_quotas` as a legacy table with `questions_limit = 3`.

The TZ explicitly forbids live reliance on:

```text
HoraryQuota.questions_used
HoraryQuota.questions_limit
default 3 free questions
```

### Current risk

Even if no current service uses it, its presence invites future coder agents to reuse it and reintroduce old behavior.

### Required fix options

Preferred:

- remove `HoraryQuota` ORM model;
- remove `horary_quotas` table from migration if there is no production data dependency.

Acceptable temporary option:

- rename comments to `LEGACY_DO_NOT_USE`;
- add a code comment above model and migration table;
- add a test or grep gate that no service/API/frontend imports or queries `HoraryQuota`.

Recommended grep gate:

```bash
grep -R "HoraryQuota\|questions_used\|questions_limit\|horary_quotas" apps/api \
  --exclude-dir=.venv --exclude-dir=__pycache__
```

Allowed hits only:

- migration legacy block, if kept;
- explicit deprecated comment, if kept.

## M2. Weekly-free uniqueness is regular unique, not partial unique

### Problem

TZ asked for:

```text
UNIQUE(user_id, source, access_week_start, access_week_end)
WHERE source = 'subscription_weekly_free'
```

Current migration/model uses a regular unique constraint:

```python
UniqueConstraint("user_id", "source", "access_week_start", "access_week_end")
```

### Why it matters

PostgreSQL allows multiple NULLs, so paid/gift rows with null week fields probably still work. But the DB shape is not exactly the TZ and may behave differently across DBs.

### Required fix

For PostgreSQL:

```python
Index(
    "uq_horary_credits_weekly_free",
    "user_id",
    "source",
    "access_week_start",
    "access_week_end",
    unique=True,
    postgresql_where=text("source = 'subscription_weekly_free'"),
)
```

For SQLite test compatibility:

- either keep an equivalent regular unique only in SQLite migrations;
- or accept the current regular unique with a comment explaining why.

At minimum document the intentional SQLite/Postgres compromise.

## M3. Access-week resolution uses date-only `AccessLedger`

### Problem

TZ says access weeks are based on access period start time, e.g. `2026-06-01 12:00 → 2026-06-08 12:00`.

Current `AccessLedger` appears date-based (`start_date`, `end_date`), and `HoraryCreditService.resolve_current_access_week()` turns dates into midnight UTC intervals.

### Risk

If access is actually date-only across the product, this may be acceptable for current MVP. But it does not fully implement the TZ examples where trial starts at an exact timestamp.

### Required decision

Pick one:

1. Update TZ to explicitly say current implementation uses date-based access days at UTC midnight.
2. Change `access_ledger` to timestamp-based access windows for horary weekly-free.

Do not leave this ambiguous.

## M4. Failure/refund ledger audit is weak

### Problem

Refund deletes `HoraryCreditSpend` after decrementing `used_amount`.

Functionally this restores credit, but audit trail is lost.

### Recommendation

Not a blocker for MVP, but better ledger model:

- keep spend row;
- add `reversed_at`, `reversal_reason`, or a separate `horary_credit_refunds` table.

For now, if keeping deletion, document it as MVP simplification.

---

# Required implementation packet

## Packet title

`W-HORARY-FIX-30EA0D1: close idempotency/generation/refund gaps`

## Goal

Bring commit `30ea0d1` from “mostly rewritten” to acceptable MVP compliance with `docs/16_Horary_questions_TZ.md`.

## Scope

Allowed files:

```text
apps/api/app/services/horary_service.py
apps/api/app/services/horary_credit_service.py
apps/api/app/api/horary.py
apps/api/app/db/models.py
apps/api/alembic/versions/0011_add_horary.py
apps/api/tests/test_horary_endpoints.py
apps/api/tests/test_horary_credit_service.py
```

Touch frontend only if backend contract changes unexpectedly. Frontend is mostly aligned after `30ea0d1`.

## Required changes

### 1. Return created flag from `create_question`

Implement:

```python
@dataclass(frozen=True)
class CreateHoraryQuestionResult:
    question: HoraryQuestion
    created: bool
```

or equivalent tuple.

Rules:

```text
existing same idempotency key + same request hash => created=False
new question => created=True
same key + different hash => raise IDEMPOTENCY_CONFLICT
```

### 2. Start generation only for newly created questions

In router:

```python
result = await service.create_question(user_id, body, now)
await db.commit()

if result.created and result.question.status == "processing":
    asyncio.create_task(service._generate_answer_task(result.question.id))

return _to_question_read(result.question)
```

### 3. Use full canonical request hash

Hash all horary business input fields:

```text
text
category
clientTimezone / client_timezone
clientLocalTime / client_local_time
questionLat / question_lat
questionLon / question_lon
```

Do not hash `idempotencyKey`.

Use canonical JSON with `sort_keys=True`.

### 4. Guard answer save against stale generation

Before creating `HoraryAnswer`, reload/lock question and require status `processing`.

If status is not `processing`, skip save and return without changing status.

### 5. Decide and document legacy `HoraryQuota`

Preferred: remove it.

If kept, add explicit `LEGACY_DO_NOT_USE` comment and make sure no service imports/queries it.

### 6. Add missing tests

Must add these tests:

```text
1. same idempotencyKey + same full payload returns same question id.
2. same idempotencyKey + same full payload does not enqueue second generation.
3. same idempotencyKey + different clientLocalTime returns 409.
4. same idempotencyKey + different questionLat/questionLon returns 409.
5. TTL failure refunds credit and late generator completion cannot set answered.
6. at exactly access_week_end, old weekly-free is unavailable.
7. future access weeks do not pre-create weekly-free credits.
8. paid credit can be spent without active access.
9. expired gift/referral credit is ignored.
10. nearest expires_at bonus/gift/adjustment credit is spent before paid.
```

Tests 1–5 are mandatory for this fix packet. Tests 6–10 may be grouped into `test_horary_credit_service.py`.

---

# Suggested exact tests

## T1. Duplicate same idempotency key does not enqueue twice

```python
async def test_duplicate_same_payload_returns_existing_and_does_not_enqueue_twice(...):
    # arrange user + paid credit
    # patch app.api.horary.asyncio.create_task
    # POST same payload twice with same idempotencyKey
    # assert both responses have same id
    # assert create_task called once
    # assert one HoraryCreditSpend row exists
    # assert credit.used_amount == 1
```

## T2. Different clientLocalTime conflicts

```python
async def test_same_idempotency_key_different_client_time_returns_409(...):
    # first POST with clientLocalTime A
    # second POST with same key and clientLocalTime B
    # assert 409 IDEMPOTENCY_CONFLICT
```

## T3. Different coordinates conflict

```python
async def test_same_idempotency_key_different_location_returns_409(...):
    # first POST with questionLat/Lon A
    # second POST with same key and questionLat/Lon B
    # assert 409 IDEMPOTENCY_CONFLICT
```

## T4. Late generator cannot overwrite failed/refunded question

```python
async def test_late_generation_does_not_answer_failed_refunded_question(...):
    # create processing question with paid spend
    # call _check_lazy_ttl with old created_at so it fails/refunds
    # simulate generator save boundary / call helper
    # assert status remains failed
    # assert no HoraryAnswer row created
    # assert credit.used_amount == 0
```

If the current generator is too hard to test, extract a helper:

```python
async def _save_answer_if_processing(db, question_id, answer_payload, now) -> bool:
    ...
```

and test that directly.

## T5. Weekly boundary

```python
async def test_weekly_free_expires_at_exact_access_week_end(...):
    # create access ledger covering week 1 and week 2
    # resolve quota at week_end - 1 second => weeklyFreeAvailable true/false depending used
    # resolve quota exactly at week_end => old credit is not spendable
```

---

# Acceptance checklist

Feature can be accepted only when all checks pass:

```text
[ ] Repeated same idempotent POST does not enqueue a second generator.
[ ] request_hash includes time, timezone, and coordinates.
[ ] Same idempotency key with changed time/location returns 409.
[ ] Late generator cannot turn failed/refunded question into answered.
[ ] No service uses HoraryQuota/questions_used/questions_limit as live business logic.
[ ] /api/horary/quota returns weeklyFreeAvailable/bonusCredits/paidCredits only.
[ ] Frontend gating does not use left/nextInDays.
[ ] Required tests for idempotency, refund race, boundary, and spend order are present.
```

---

# Final reviewer note

`30ea0d1` is the right architectural direction and fixes the biggest previous mismatch. The remaining work is mostly about correctness under retries, timing changes, and async races.

After B1–B3 and the mandatory tests are fixed, this can likely pass MVP acceptance.
