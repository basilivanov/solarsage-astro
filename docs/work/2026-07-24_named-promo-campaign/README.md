# Named promo campaign — coder-loop execution index

Этот каталог содержит архитектурный master и маленькие independently
verifiable coder tasks. `00_ARCHITECTURE_TZ.md` остаётся у
архитектора/ревьюера; кодеру передаётся только один очередной slice.

## Sequence

| Slice | Локальная цель | Depends on | Gate before next |
|---|---|---|---|
| 01 | start_param classifier, session-only promo intent, URL/log privacy | none | focused Vitest |
| 02 | PromoCampaign/PromoRedemption migration/models | none | model + Alembic tests |
| 03 | additive non-committing AccessLedger primitive | none | access service tests |
| 04 | reusable base+natal readiness helpers | none | profile readiness tests |
| 05 | closed promo event registry | none | logging guardrails |
| 06 | atomic preview/redemption domain service | 02–05 | promo service tests |
| 07 | Pydantic/OpenAPI/generated wire contracts | 06 shape stable | contracts check |
| 08 | safe authenticated promo HTTP routes | 06–07 | promo API tests |
| 09 | validated frontend promo client | 07–08 | focused client Vitest |
| 10 | generic named confirmation sheet | 07 offer type | focused component Vitest |
| 11 | post-auth gate + ALREADY recovery | 01,05,09,10 | gate Vitest |
| 12 | pure existing-profile onboarding prefill | none | reducer Vitest |
| 13 | campaign-aware base/natal onboarding mode | 04,12 | onboarding Vitest |
| 14 | secure operator CLI | 02,05,06 | CLI pytest |
| 15 | authenticated per-user attempt limiter | 08 | limiter/API pytest |
| 16 | Nginx query/referrer privacy + loose IP ceiling | 01,15 policy | static infra pytest |
| 17 | shared election/horary credit row lock | none | election pytest |
| 18 | honest non-enrollment access copy | existing billing status | component Vitest |
| 19 | real PostgreSQL concurrency/release gate | all backend slices | PostgreSQL acceptance |
| 20 | operator detection/canary/rollback runbook | 14–19 | runbook contract pytest |

## Non-negotiable merge gates

До merge/release всей feature должны быть доказаны:

```text
raw promo token absent from URL history and all logs
malformed API body never echoes token
unknown birth time cannot create onboarding loop or consume redemption
one transaction / one commit / success log after commit
ALREADY_REDEEMED recovers a lost successful response
real PostgreSQL concurrency exact counts
election and horary cannot double-spend one credit
promo access copy does not claim a paid recurring subscription
rollback never goes below Slice 01 privacy compatibility floor
```

## Coder-loop rule

1. Architect selects one slice whose dependencies are accepted.
2. Only that slice is pasted into `tmux astro2`.
3. Coder changes only allowed files and runs the one targeted command.
4. Architect reviews diff/contracts/tests and either accepts or writes one
   narrow rework TZ.
5. Commit/push/deploy are architect-owned; coder does none of them.

Не объединять «для скорости» registry, DB, service, HTTP, frontend и infra в
одну coder prompt. Если slice обнаруживает новый cross-cutting decision,
остановиться и вернуть его архитектору, а не расширять scope молча.
