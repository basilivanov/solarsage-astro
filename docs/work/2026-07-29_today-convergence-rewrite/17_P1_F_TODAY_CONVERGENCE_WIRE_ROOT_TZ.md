# P1-F — New Today Convergence wire root

Phase / Wave: `today-convergence-2 / P1 (W2-S0)`

## Goal

Создать отдельный strict Pydantic root `TodayConvergencePayload`, сгенерировать
из него OpenAPI/TypeScript/Zod и добавить feature shim. Это только wire contract:
endpoint, расчётный pipeline, persistence и frontend не реализуются в пакете.

Новый root не импортирует и не встраивает legacy `TodayPayload`, `TodayFocus`,
`dayStatus`, `relativeStatus`, `v2` или valence-поля.

## Normative sources

- `04_W2_W3_RUNTIME_CONTRACT_TZ.md` §§2–3;
- `grace/canon/today_convergence.v1.yml` (`frozen_w1`);
- `AGENTS.md` — GRACE и generated-contract policy.

## Exact write scope

- `apps/api/app/schemas/today_convergence.py` (new);
- `apps/api/app/schemas/contract_registry.py`;
- `apps/api/tests/test_today_convergence_contract.py` (new);
- `apps/api/tests/test_contract_registry.py`;
- `apps/api/tests/fixtures/contracts/today-convergence-full-hero-ready.json`;
- `apps/api/tests/fixtures/contracts/today-convergence-full-quiet-not-needed.json`;
- `apps/api/tests/fixtures/contracts/today-convergence-preview.json`;
- `apps/api/tests/fixtures/contracts/today-convergence-locked.json`;
- `apps/api/tests/fixtures/contracts/today-convergence-unavailable.json`;
- generated only through `pnpm contracts:generate`:
  `packages/contracts/openapi.json`, `packages/contracts/_generated.ts`,
  `packages/contracts/_generated.zod.ts`;
- `packages/contracts/today-convergence.ts` (new generated re-export shim);
- `__tests__/contracts/today-convergence-contract.test.ts` (new);
- this packet document.

## Frozen / out of scope

- legacy schemas and barrels: `schemas/today.py`, `schemas/today_focus.py`,
  `packages/contracts/today.ts`, existing `TodayConvergence` nested legacy type;
- API routers/services, DB models/migrations, cache, LLM, pregen and frontend UI;
- other W2/W3 roots (`TodayCalendarPayload`, drilldown, history, retry,
  impression, check-in);
- manual edits to generated artifacts or handwritten wire/Zod definitions;
- commits and push.

## Required schema

All models inherit `CamelModel` (`extra="forbid"`, camelCase wire). Use
feature-prefixed class names so generated components cannot collide with the
legacy `TodayConvergence` type:

- `TodayConvergenceBirthCapabilities`;
- `TodayConvergenceBirthTime`;
- `TodayConvergencePreviewTeaser`;
- `TodayConvergenceNarrativeClaim` and a summary form with `text.max_length=220`;
- `TodayConvergenceEventTime`;
- `TodayConvergenceEvent`;
- `TodayConvergenceGroup`;
- `TodayConvergenceMainEvent`;
- `TodayConvergenceImpulse`;
- `TodayConvergencePeriodContext`;
- `TodayConvergenceLookahead`;
- public root `TodayConvergencePayload`.

Root fields and aliases must match `04` §3.1 exactly:

```text
schemaVersion: Literal[1]
snapshotId: str | null
targetDate: ISO date
timezone: IANA string
publishedAt: ISO datetime | null
access: ContentAccessState
birthTime: object
state: convergence_today | quiet_day | unavailable | null
dayTone: steady | supportive | mixed | tense | null
personal: boolean | null
previewTeaser: object | null
convergences: 0..3
mainEvent: object | null
impulses: 0..3
periodContext: object | null
lookahead: object | null
events: array
contentState: ready | pending | unavailable | not_needed
formulaVersion: Literal["today-convergence-2"]
calculationVersion: non-empty string
```

Canonical sphere keys are the closed 12-value Literal from canon:
`work, money, documents, relationships, sport, communication, health,
decisions, travel, creativity, study, shopping`. Define it once in the new
module and use it for all public sphere fields.

Nested shapes, caps and timing modes follow `04` §§3.3 verbatim. In particular:

- public polarity is only `supportive|tense|mixed`; `steady` is day tone only;
- evidence level is only `high|medium`;
- `previewTeaser.spheres` has maximum three unique values;
- `ConvergenceGroup.eventIds` has at least two unique IDs;
- every non-null narrative field is `{text, sourceEventIds}`; source IDs are
  non-empty and unique; summary text max is 220;
- `events[].id`, `convergences[].id`, each ID array and `sourceIds` are unique;
- IDs are opaque non-empty strings in this packet; hash construction belongs
  to W2-S1.

## Cross-field validators

Implement deterministic `model_validator` checks with stable, testable reason
tokens in error messages. Required matrix:

1. `access.state=locked`: `state/dayTone/personal/snapshotId/publishedAt` null,
   `contentState=not_needed`, teaser and all content/evidence null or empty.
2. `state=unavailable` with full/preview access: no snapshot/published content,
   `dayTone/personal` null, `contentState=unavailable`, teaser null, arrays empty,
   `mainEvent/periodContext/lookahead` null.
3. `access.state=preview` + calculated state: published snapshot required,
   `dayTone/personal/previewTeaser` non-null, `contentState=not_needed`; hidden
   arrays empty and all narrative/context/lookahead fields null.
4. `access.state=full` + calculated state: published snapshot, day tone and
   personal required; `previewTeaser=null`.
5. `convergence_today`: 1..3 convergences; no `mainEvent`, impulses or
   lookahead.
6. `quiet_day`: no convergences; at least one of mainEvent/impulses/
   periodContext; mainEvent and impulses mutually exclusive. Lookahead is
   allowed only here.
7. `pending|unavailable|not_needed` content state: every narrative claim in
   group/mainEvent/impulse is null. `contentState=unavailable` must preserve the
   deterministic calculated snapshot.
8. Event ledger: event IDs equal the set referenced by deterministic selected
   blocks (groups, main event, impulses and period context); no dangling or
   unused event. Narrative source IDs must be a subset of the selected event
   IDs and present in `events`.
9. One convergence group: `primarySphere != secondarySphere`; max one
   secondary sphere; the union of presentation spheres across selected groups
   is at most three.

Birth-time validation:

- exact: bucket null, equal real `HH:MM` range endpoints, all four capabilities
  true;
- bucket: selected bucket, canonical half-open range, all capabilities false;
- unknown: bucket null, `[00:00,24:00)`, all capabilities false;
- `24:00` is accepted only as the unknown/evening exclusive birth range end.

Event-time validation:

- exact: `partOfDay=null`; populated clock fields are valid `HH:MM` and never
  `24:00`;
- partofday: `partOfDay=night|morning|day|evening`, clock fields null;
- date: all clock/part-of-day fields null;
- bucket birth mode permits only partofday event times; unknown permits only
  partofday/date; exact permits all three presentation precisions.

Period context validation:

- `no_strong_accent`: sphere/dates null and event IDs empty;
- `active_period`: sphere, title, activeFrom and activeUntil required;
- no LLM fallback fields are added.

## Registry and generated shim

- Add only `TodayConvergencePayload` as a public root, alphabetically before
  `TodayPayload`; update the registry's exact-name test.
- Run `pnpm contracts:generate`; never edit generated files by hand.
- `packages/contracts/today-convergence.ts` may only alias types from
  `./_generated` and re-export generated Zod values from `./_generated.zod`.
  It must export the root and every nested feature-prefixed type/schema needed
  by later W2–W7 code. No local object/interface/union or `z.object`.
- Do not add the new feature to legacy `packages/contracts/today.ts`.

## Fixtures and tests

The five JSON fixtures represent: full hero ready, full quiet not-needed,
preview calculated, locked, and calculation unavailable. Python must parse and
round-trip each fixture by alias. TypeScript must parse the same files through
the generated root Zod schema exported by the feature shim.

Python/Pydantic negative tests must cover every numbered validator rule above plus:

- all three birth-time modes and invalid capability/range combinations;
- all EventTime modes and birth-mode precision restrictions;
- extra unknown field rejection;
- summary >220 chars;
- duplicate/dangling/unused IDs;
- legacy fields (`dayStatus`, `focus`, `v2`) rejected.

Tests assert stable reason tokens, not the full Pydantic error prose.

Generated Zod preserves the repository's deliberate rolling/forward-
compatibility policy: an unknown additive response field is accepted and
stripped. The TypeScript test must prove that legacy/unknown keys are absent
from parsed output; it must not require `.strict()` or redefine a handwritten
schema. This does not permit legacy fields in the producer: Pydantic remains
`extra="forbid"`, and the generated TypeScript type contains no such keys.

## Verification

```bash
cd apps/api
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_convergence_contract.py \
  tests/test_contract_registry.py -q
/opt/solarsage-astro/apps/api/.venv/bin/ruff check \
  app/schemas/today_convergence.py \
  app/schemas/contract_registry.py \
  tests/test_today_convergence_contract.py \
  tests/test_contract_registry.py
cd ../..
pnpm contracts:generate
pnpm contracts:check
npx vitest run __tests__/contracts/today-convergence-contract.test.ts
npx tsc --noEmit
python3 scripts/grace_lint.py apps/api/app --quiet
python3 scripts/check_logging_guardrails.py
git diff --check
```

## Expected evidence

- root and nested Pydantic models validate the five fixtures and reject the
  negative matrix;
- generated OpenAPI/TS/Zod contain `TodayConvergencePayload` as an isolated
  component/root;
- feature shim contains only generated aliases/re-exports;
- no production endpoint or legacy Today schema changed;
- coder does not commit or push.

## Escalation

If the generated toolchain cannot express a required structural invariant in
Zod, do not add a handwritten replacement. Keep Pydantic as authoritative,
record the exact generator gap, and stop for reviewer decision. Unknown-field
stripping is not a gap: it is the existing forward-compatibility contract in
`__tests__/contracts/generated-runtime.test.ts`.
