# W9 legacy-removal manifest

Это allowlist удаления после успешного W8 atomic cutover. Он фиксирует решение
владельца: старые Today-контракты не становятся compatibility layer новой
модели. До W8 этот список только документирует blast radius; текущий production
runtime не удаляем посреди rewrite. Исключение — test-only fixtures: W7 обязан
атомарно заменить активные V1/V2 Today/Calendar/Yesterday fixtures новыми
contract fixtures; Git остаётся архивом, `__tests__/legacy/` не создаётся.

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
- оставшиеся после W7 mock payloads и visual baselines V1/V2/V2.1/V2.2;
- generated legacy contract roots удаляются уже в W8 перед сборкой нового
  frontend; W9 удаляет их недостижимые Pydantic/adapter implementations;
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

## Staged test-removal manifest

Правило для всех стадий: тест не удаляется только потому, что мешает CI.
Удаление допустимо, когда в том же changeset либо удалён owning legacy module,
либо добавлено равноценное покрытие нового публичного контракта. Каталог
`__tests__/legacy/` не создаётся — архивом остаётся Git.

### W7 — удалить вместе с новым frontend и 16 fixtures

Следующие тесты принадлежат старому Today Focus/V2 presentation и удаляются
атомарно с новыми convergence component/contract tests:

```text
__tests__/components/ActivationEvidenceCard.downstream.test.tsx
__tests__/components/ActivationEvidenceCard.personal.test.tsx
__tests__/components/FocusEventSheet.test.tsx
__tests__/components/TodayFocus.test.tsx
__tests__/components/TodayImportantAccordion.test.tsx
__tests__/components/TodayScreen.v2-downstream.test.tsx
__tests__/contracts/today-fixture-roundtrip.test.ts
__tests__/contracts/today-focus-canary-roundtrip.test.tsx
__tests__/contracts/today-v2-wire-identity.test.ts
__tests__/lib/presentation/today-v2.test.ts
__tests__/today/day-summary-card.test.tsx
e2e/real-v2-preview.spec.ts
e2e/dev-timing-fixture.spec.ts
e2e/dev-visible-sphere-status.spec.ts
e2e/mock-visual/day-v2.spec.ts
e2e/mock-visual/day.spec.ts
```

Удаляются также их exclusive fixtures/snapshots:

```text
e2e/mock-visual/fixtures/day-2026-07-05.ts
e2e/mock-visual/fixtures/day-v2-2026-07-08.ts
e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json
e2e/mock-visual/day-v2.spec.ts-snapshots/
```

`e2e/mock-visual/acceptance-day.spec.ts` пока сохраняется: он участвует в
текущем production artifact-acceptance и заменяется только в W8 тем же SHA,
который переводит deploy workflow на новый envelope.

### W7 — переписать, а не просто удалить

Имена этих tests/consumers остаются полезны, но assertions и fixtures полностью
заменяются новым contract:

```text
__tests__/components/TodayScreen.test.tsx
__tests__/components/CalendarScreen.test.tsx
__tests__/app/day-page.test.tsx
__tests__/app/checkin-page.test.tsx
__tests__/hooks/useDay.test.ts
__tests__/hooks/useCalendar.test.ts
__tests__/api/calendar.test.ts
__tests__/api/checkin.test.ts
__tests__/contracts/today.test.ts
__tests__/contracts/calendar.test.ts
__tests__/contracts/generated-runtime.test.ts
__tests__/contracts/today-redeclaration-guard.test.ts
e2e/today.spec.ts
e2e/calendar.spec.ts
e2e/profile-city-checkin.spec.ts
e2e/mock-visual/calendar.spec.ts
```

Новые проверки используют `TodayConvergencePayload`, `hero|ordinary|
not-computed`, snapshot recap и DOM attributes из `AGENTS.md`; старые
`DayStatus`, `TodayFocus`, `relativeStatus`, `today.v2` assertions исчезают.

### W8 — generated/public acceptance cleanup

При удалении legacy roots из `PUBLIC_CONTRACT_ROOTS` удаляются или заменяются
тесты wire identity старого payload, старый `acceptance-day.spec.ts`, его V2
fixture/proof scripts и связанные production-workflow assertions. Новый
artifact acceptance доказывает один и тот же convergence payload через API,
generated schema и UI; source SHA/ephemeris identity gates сохраняются.

### W9 — удалить backend legacy runtime tests вместе с owning code

Allowlisted семейства:

```text
apps/api/tests/test_scoring_v2_*.py
apps/api/tests/test_day_valence_*.py
apps/api/tests/test_today_focus_*.py
apps/api/tests/test_horizon_*.py
apps/api/tests/test_today_horizon_*.py
apps/api/tests/test_today_horizons_contract.py
apps/api/tests/test_day_horizon_exact_at_regression.py
apps/api/tests/test_semantic_v2_service.py
apps/api/tests/test_today_v2_payload.py
apps/api/tests/test_payload_v2_downstream_mapping.py
apps/api/tests/test_downstream_v2_audit.py
apps/api/tests/test_audit_downstream_v2.py
apps/api/tests/test_calendar_v2_dual_run.py
apps/api/tests/test_real_today_v2_api_proof.py
apps/api/tests/test_basil_2026_07_08_v2_golden.py
apps/api/tests/test_today_cache_v2_key.py
apps/api/tests/test_wave3_day_pipeline_reuse.py
apps/api/tests/test_day_relative_status.py
apps/api/tests/test_focus_event_drilldown.py
```

Тесты `test_day_endpoints.py`, `test_calendar_endpoints.py`,
`test_profile_endpoints.py`, `test_checkin_endpoints.py`,
`test_contract_registry.py`, ownership/access/security, astronomy oracle,
sidecar parity и migration tests не удаляются по совпадению имени. Они
переписываются/расширяются под новый путь или остаются общими инвариантами.

Финальный gate после W9:

```bash
rg -n 'DayStatus|TodayFocus|relativeStatus|ScoringV2|DayValence|SemanticV2|today\.v2' \
  apps/api/tests __tests__ e2e \
  --glob '!**/audit/**'
# expected: 0 active legacy matches; только явно разрешённые supersession docs
```
