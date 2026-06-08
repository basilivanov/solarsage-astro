---
id: doc-16-horary-questions-tz
status: active
wave: PHASE-HORARY
last_review: 2026-06-08
---
# 16. Horary questions TZ

## Purpose

This document fixes the product and backend rules for horary question credits: weekly free questions, paid questions, bonus/gift questions, expiration, and spend order.

Horary questions are a separate product format. They are not part of TodayPayload. Today explains the selected day; horary answers a specific user question.

---

# Product rule

Active access grants **1 free horary question per access week**.

Active access may come from:

- trial;
- referral extension;
- gift access;
- paid subscription;
- manual admin adjustment.

There is no permanent free tier. The weekly free horary question exists only while the user has active access.

---

# Weekly free question

The weekly free question must be named `subscription_weekly_free`.

Rules:

- exactly 1 question per active access week;
- does not accumulate;
- does not roll over into the next week;
- expires at the end of its access week if unused;
- is spent before any bonus or paid credits.

Deprecated name: `weekly_bonus`.

Reason: `weekly_bonus` is ambiguous because it mixes the weekly access-based free question with real bonus/gift credits.

---

# Paid and bonus credits

Paid horary credits:

- accumulate;
- do not expire by default;
- are not reduced when weekly free credits expire.

Referral, gift, and adjustment credits:

- may accumulate;
- may expire if `expires_at` is set by the campaign/admin rule;
- are spent before paid credits when they expire earlier.

---

# Spend order

When the user submits a horary question, spend credits in this order:

```text
1. current subscription_weekly_free
2. referral_bonus / gift / adjustment by nearest expires_at
3. paid credits, oldest first
```

Backend invariants:

- never spend paid credit while an active weekly free credit is available;
- never spend expired credits;
- spend atomically;
- one submitted question must not spend more than one credit;
- duplicate submit with the same idempotency key must not double-spend.

---

# Data model

```text
horary_credits
- id
- user_id
- source: subscription_weekly_free / referral_bonus / gift / paid / adjustment
- amount
- used_amount
- access_week_start nullable
- access_week_end nullable
- created_at
- expires_at nullable
- metadata_json nullable
```

`subscription_weekly_free` rows must have:

- amount = 1;
- access_week_start set;
- access_week_end set;
- expires_at = access_week_end.

Paid rows usually have `expires_at = null`.

---

# Access week definition

For MVP, an access week is counted from the start of the user's active access window, not from calendar Monday.

Example:

```text
Trial starts: 2026-06-01 12:00
Week 1: 2026-06-01 12:00 → 2026-06-08 12:00
Week 2: 2026-06-08 12:00 → 2026-06-15 12:00
```

Each week gives at most one `subscription_weekly_free` credit.

If the user extends access through referral or subscription, future weeks become available as time reaches them. The user does not receive all future weekly free questions immediately.

---

# Profile API summary

Weekly free credit must be shown separately from bonus credits.

Recommended shape:

```ts
export type HoraryInfo = {
  weeklyFreeAvailable: boolean
  weeklyFreeExpiresAt?: string
  paidCredits: number
  bonusCredits: number
  nextWeeklyFreeAt?: string
  description: string
}
```

`bonusCredits` must not include the current weekly free question.

---

# Acceptance tests

## Weekly free expires

Given the user has an unused `subscription_weekly_free` in week 1, when week 1 ends, then this credit is expired and is not available in week 2.

## New week grants new free question

Given the user has continuous active access for 14 days, when week 2 starts, then the user has exactly 1 free question for week 2, not 2.

## Paid credits persist

Given the user bought paid credits, when weekly free credits expire, then paid credits remain unchanged.

## Spend order

Given the user has 1 active weekly free question and 2 paid credits, when the user asks a horary question, then the weekly free question is spent and paid credits remain 2.

## No double spend

Given the user submits the same question twice with the same idempotency key, then only one credit is spent.

---

# Final rule

```text
Active access grants 1 free horary question per access week.
This weekly free question does not accumulate and expires at the end of the access week.
Paid horary questions accumulate and do not expire by default.
Gift/referral/adjustment credits follow their own expires_at rule.
Spend order: weekly free → expiring bonus/gift/referral/adjustment → paid.
```
