# Technical Pre-Mortem: синастрия / React adaptation

Дата: 2026-07-25. Анализ выполнен до реализации по фактическому `main`,
прототипу PR #11 и `01_TZ_REACT_ADAPTATION.md`.

## 1. Summary

```text
Affected: ≥30 runtime/canon files + tests / ≥9 wire contracts / DB schema: yes
Reversibility: app rollback без schema rollback, только через dark launch
Initial risks: 7 Tigers (blocking: 7) · 3 Paper Tigers · 7 Elephants
Initial verdict: NO-GO
Verdict after TZ hardening: GO WITH CONDITIONS for implementation;
                             NO-GO for Release B activation until all gates pass
```

Первоначальный NO-GO был вызван не объёмом фичи, а отсутствующей численной
формулой, противоречивым unknown-time contract, двумя LLM paths, неописанным
generation lifecycle и конфликтом существующего `synastry` с предлагаемым
`synastry_1`. Эти design ambiguity закрыты в обновлённом `01` и нормативном
`03_SCORING_AND_TONE_CONTRACT.md`; реализационные риски остаются merge gates.

## 2. Blast radius

Что меняется:

- sidecar: request/response schemas, `/v1/synastry`, partner chart и cross aspects;
- API/DB: partner/report/detail/feedback/spend tables, scoring, LLM, routes;
- shared billing: product catalog, PurchaseStart literal, metadata, credits;
- frontend: Readings entry, `/synastry`, components, generated contracts;
- operations: migrations, reconciliation job, events/metrics, staged rollout.

Зависимые соседи:

- horary и election используют тот же `HoraryCredit` и ordering;
- payment product listing и webhook fulfillment читают общий catalog;
- owner facts принадлежат `NatalContextService`;
- production активирует один immutable SHA сразу для API/sidecar/frontend.

Shared state: PostgreSQL, partner PII, report cache, credit pool, product rows,
LLM providers, sidecar и feature flags.

## 3. Risk registry

| # | Failure symptom | Class | Urgency | Detection | Resolution |
|---|---|---|---|---|---|
| 1 | Score зависит от догадки исполнителя | 🐘 Correctness | decision blocker | formula review | численный `03`, versioned fixtures |
| 2 | Unknown report теряет валидные overlays или выдумывает houses | 🐘 Contract | decision blocker | directional fixtures | owner/partner precision + API overlay owner |
| 3 | Report зависает после process restart, credit остаётся spent | 🐘 Reliability | decision blocker | stale gauge | DB lease + reconcile job |
| 4 | `synastry` и `synastry_1` расходятся | 🐘 Product/data | decision blocker | catalog assertion | один `synastry`, 399 ₽, inactive dark launch |
| 5 | Agent расширяет legacy LLM stack | 🐘 Implementer | decision blocker | import/body trap | canonical client + pure `synastry_llm.py` |
| 6 | Новый tab ломает Chat/5-column navigation | 🐘 Coupling | decision blocker | navigation test | MVP остаётся внутри Readings |
| 7 | Partner PII невозможно удалить | 🐘 Lifecycle | decision blocker | deletion drill | owner hard delete + anonymized spend audit |
| 8 | Frontend fixture проходит, production wire расходится | 🐅 Contract | merge-blocking | `contracts:check` | Pydantic roots + generated TS/Zod |
| 9 | POST не имеет timezone/coords или дедуплицирует разных людей | 🐅 Correctness | merge-blocking | request/concurrency tests | structured City + idempotency key |
| 10 | Чужой UUID раскрывает partner/report | 🐅 Security | merge-blocking | two-user matrix | owner-scoped queries, 404 |
| 11 | Concurrent spend/refund портит `used_amount` | 🐅 Concurrency | merge-blocking | PostgreSQL acceptance | locks + unique transition + adjustment refund |
| 12 | Migrate/rollback показывает unsupported active product | 🐅 Operations | merge-blocking | old-app/rollback smoke | Release A dark launch, Release B activation |
| 13 | Fallback сохраняет malformed text или отправляет PII | 🐅 LLM/security | merge-blocking | prompt/validator traps | two-call budget + fail-closed validation |
| 14 | Shared credit change ломает horary/election | 🐅 Regression | merge-blocking | cross-feature acceptance | общий ordering/race suite |
| 15 | Additive endpoint ломает natal/transits | 🐯 Paper Tiger | observation | sidecar regression | изолированные files/router |
| 16 | Новые таблицы блокируют production DB | 🐯 Paper Tiger | observation | prod-dump rehearsal | no backfill, short catalog update |
| 17 | SVG wheel перегружает mobile browser | 🐯 Paper Tiger | observation | trace | bounded body-pair set |

## 4. Merge-blocking Tigers

### T8 — Wire contract drift

- **Symptom:** mock UI ready, real response rejected or silently misread.
- **Mechanism:** repository SoT is Pydantic CamelModel → OpenAPI → TS/Zod;
  hand-written JSON/TS would bypass it.
- **Detection:** `pnpm contracts:check`, runtime boundary tests, `/quota` route trap.
- **Pre-flight:** enumerate list/create/status/report/detail/feedback/capabilities roots.
- **Test:** generated artifact diff must be committed and clean.
- **Mitigation:** no hand-written wire schemas or casts.

### T9 — Partner input/idempotency

- **Symptom:** city text cannot produce sidecar input; same-name people collide.
- **Mechanism:** sidecar requires lat/lon/IANA timezone; name+date is not identity.
- **Detection:** exact/unknown/unresolved-city and concurrent retry tests.
- **Pre-flight:** freeze `PartnerCreate` from `01`.
- **Mitigation:** selected City object, UUID idempotency key + payload hash.

### T10 — IDOR

- **Symptom:** partner/report/aspect belonging to another user returns 200.
- **Mechanism:** UUID and aspect slug do not prove ownership.
- **Detection:** two users × every endpoint, including delete/feedback/status.
- **Pre-flight:** one owner-scoped repository helper.
- **Mitigation:** query by user+partner+report at the DB boundary; 404, never 403.

### T11 — Credit atomicity/refund

- **Symptom:** double spend, double refund or lost weekly-free after timeout.
- **Mechanism:** external generation outlives request/week; existing refund examples
  do not all lock the same rows and disagree on expiry.
- **Detection:** real PostgreSQL process-death and parallel transaction tests.
- **Pre-flight:** state transition table and expiry behavior from `01`.
- **Mitigation:** report+spend commit together; locked idempotent refund; expired
  source becomes one seven-day adjustment credit.

### T12 — Deploy/rollback

- **Symptom:** migration exposes SKU to old API; rollback preserves broken DB row.
- **Mechanism:** production migrates before deploy and app rollback never downgrades
  schema.
- **Detection:** Release A/B rehearsal against a production dump.
- **Pre-flight:** previous active SHA for B must be proven Release A.
- **Mitigation:** schema/inactive product first; activation only in second release;
  feature flag filters catalog and write routes.

### T13 — LLM fail-closed/PII

- **Symptom:** malformed/fatalistic narrative persisted, or partner identity sent
  to provider.
- **Mechanism:** DeepSeek fallback has no provider schema; free-text names cannot
  be reliably redacted after construction.
- **Detection:** request-body spy, invalid JSON/blocklist/approximate trap fixtures,
  `synastry.llm_validation_failed`.
- **Pre-flight:** exact schemas and two-call budget.
- **Mitigation:** factor-only prompt; local validation after every provider;
  all-or-nothing base narrative persist.

### T14 — Shared credit regression

- **Symptom:** horary/election balance/order changes or weekly-free insert returns 500.
- **Mechanism:** all three features mutate the same rows and fulfillment path.
- **Detection:** PostgreSQL test with one credit and concurrent feature spends;
  purchase/start test for every active slug.
- **Pre-flight:** preserve weekly→bonus→paid ordering.
- **Mitigation:** IntegrityError recovery, locked re-read, common metadata contract.

## 5. Rollback plan

1. Release A ships schema/code with product inactive and flags false.
2. Release B activates only when Release A is the recorded previous SHA.
3. Incident: run fixed `prod-orchestrator synastry-disable --manual-confirm`,
   then `synastry-reconcile`.
4. Reconcile continues safe jobs or marks them failed and refunds once.
5. Run `prod-orchestrator rollback <release-a-sha> --manual-confirm`.
6. Keep Alembic at head; do not delete production tables or product purchases.
7. Verify product hidden, legacy flows green, zero stale reports and credit
   invariants. User PII stays deletable through Release A.

Rehearsed targets: writes disabled ≤2 min, app rollback ≤15 min, credit drain
≤30 min. Monetary YooKassa refund remains a separate manual operator process.

## 6. Pre-flight checklist

- [ ] `00`, `01`, `02`, `03` and prototype resolve from the same branch/SHA.
- [ ] Scoring fixtures prove formula, boundaries and unknown Moon exclusion.
- [ ] Sidecar exact/unknown snapshots use complete birth inputs.
- [ ] Pydantic registry/generated contracts pass `pnpm contracts:check`.
- [ ] IDOR matrix covers all read/write/delete paths.
- [ ] PostgreSQL tests prove idempotency, spend/refund and stale lease recovery.
- [ ] LLM provider-body, PII and validator traps are green.
- [ ] `synastry-reconcile` is installed, scheduled and observable.
- [ ] Migration upgrade/empty downgrade and Release A/B rollback are rehearsed.
- [ ] Prod-host smoke calls sidecar and LLM; empty list GET is insufficient.
- [ ] Catalog row/price/quota/flag match code after deploy.
- [ ] GRACE markers, event registry and verification matrix are updated.

## 7. Verdict

**GO WITH CONDITIONS для начала реализации по обновлённому ТЗ.**

**NO-GO для merge**, пока отсутствует evidence по Tigers T8–T14.
**NO-GO для production activation**, пока не доказаны Release A/B, rollback,
prod-host sidecar/LLM smoke и credit reconciliation.
