# W9 legacy-removal manifest

Это allowlist удаления после успешного W8 atomic cutover. Он фиксирует решение
владельца: старые Today-контракты не становятся compatibility layer новой
модели. До W8 этот список только документирует blast radius; текущий production
runtime не удаляем посреди rewrite.

## Удаляем после cutover

### API/schema surface

- старые `TodayFocus`/`DayStatus`/`RelativeDayStatus` и их Pydantic/OpenAPI/Zod
  shapes;
- `single_impulses`, `background_only`, `no_accent`, legacy
  `dayStatus`/`relativeStatus`, `dayStatusBreakdown`;
- V1/V2/V2.1/V2.2 valence/scoring/semantic response fields, winning-group и
  compatibility adapters;
- old Today cache-key branches and serializers that emit either old shape or
  dual-read/dual-write payload.

### Backend implementation

- legacy `DayValence*`, `ScoringV2*`, `SemanticV2*` product path and its
  Today-specific fallback mapping;
- old `today_focus_builder` presentation path once W2 deterministic pipeline is
  live and W8 rollback image is pinned;
- old LLM prompt/response adapters and template fallback copy. The only allowed
  failure result in the new path remains `contentState=unavailable`, with LLM
  fields null.

### Frontend/fixtures

- Today/Calendar/Yesterday components that read legacy fields;
- old `data-testid` and structural selectors owned exclusively by those
  components;
- mock payloads, visual baselines, e2e fixtures and generated contract entries
  for V1/V2/V2.1/V2.2;
- adapters in `lib/adapters/today-payload.ts` and equivalent calendar/readings
  bridges that translate the new envelope back to a legacy enum.

## Не удаляем

- users, profiles, Telegram auth/session data;
- access ledger, payments, subscriptions, paid reports;
- `EveningCheckin`, `DayFeedback`, streak constraints and snapshot-linked
  check-ins;
- natal inputs and birth-time mode (`exact|bucket|unknown`);
- the new convergence canon, replay harness, snapshots, audit lineage and
  `formulaVersion`/`CALCULATION_VERSION` history.

## Execution gates

1. W8 deploys API + frontend + sidecar as one immutable release and passes real
   e2e against the new envelope.
2. Previous OCI release is recorded for whole-release rollback; no mixed old/new
   payloads are served.
3. DB dump + restore rehearsal completes on dev; protected-data denylist is
   checked before any derived-row cleanup.
4. `rg` legacy gate in master §10 returns only this manifest, supersession notes
   and Git-archive references.
5. Cleanup is a separate allowlisted W9 release. If it fails, rollback the
   release; do not restore old schema or delete protected rows.
