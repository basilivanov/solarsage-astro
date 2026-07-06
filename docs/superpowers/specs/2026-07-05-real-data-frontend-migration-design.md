# Real Data Frontend Migration Design

## Goal

Migrate the full visual product experience currently visible in the mock-preview frontend into the real SolarSage Astro application without carrying over mock APIs, fabricated astrology, or local-only state as product behavior.

The target user-visible scope is:

- Day screen.
- Calendar.
- Profile.
- Readings list.
- Natal preview/report surfaces.
- Horary.
- Check-in.
- Paywall/payment surfaces only after the payment backend is real.

The operational target is an atomic cutover:

- Port `3001` from mock-preview to a real-data preview branch derived from `main`.
- Keep `3002` on stable `main` until every migrated surface is tested against real API data.
- Merge the preview branch back to `main` only after the full acceptance suite is green.
- Keep the canonical Telegram bot URL pointed at the stable public host until final cutover.

## Current State

Production-like runtime:

- Frontend: `solarsage-frontend.service` on port `3002`.
- API: FastAPI `solarsage-api.service` on port `8000`.
- Sidecar: `solarsage-sidecar.service` on port `18091`.
- Nginx: `/api/*` routes to port `8000`, all other paths route to port `3002`.
- Telegram WebApp auth is the canonical production auth path.

Mock-preview runtime:

- `/opt/solarsage-astro-mock-preview` runs on port `3001`.
- It contains valuable presentation work.
- It also contains a Next.js mock catch-all API and several client-side astrology/payment/check-in simulations.

Main conclusion: `archive/demo-origin-main` must not be merged or cherry-picked wholesale. The migration must selectively port presentation components and rebuild their data sources on top of real contracts.

## Non-Goals

- Do not port `app/api/[...path]/route.ts` from mock-preview.
- Do not replace main `next.config.mjs` or remove the FastAPI `/api/*` rewrite.
- Do not replace main Telegram auth, `TelegramProvider`, or production auth boundaries.
- Do not make the UI calculate real astrology from local approximations.
- Do not parse display text such as `topFlags.summary` as data.
- Do not enable payment or paid access copy before the backend enforces payment/access semantics.
- Do not expose dev auth or demo behavior on public Telegram hosts.
- Do not use port `8001` as API.
- Do not start manual `uvicorn` processes.

## Architecture Choice

Use a contract-first migration.

SolarSage sidecar owns deterministic astronomical calculation. The FastAPI backend owns orchestration, normalization, scoring, access control, persistence, and read-model shaping. The LLM may phrase or interpret already-computed facts, but it must not be the source of deterministic facts. The frontend owns rendering, navigation, loading states, and user interactions.

Frontend production code must consume real HTTP contracts only. If sample data is needed for tests, it belongs in test fixtures, not runtime app modules.

## Frontend Layering

The migrated frontend should use these boundaries:

- `lib/api/*`: HTTP calls only. No mock branching and no embedded domain derivations.
- `lib/contracts/*`: TypeScript shims generated from backend OpenAPI/Pydantic contracts.
- `lib/adapters/*`: pure functions converting API contracts into view models.
- `components/*`: presentation components that accept typed props and do not fetch data.
- `app/(grace)/*`: route orchestration, auth-aware loading, error states, and redirects.

Runtime imports from `lib/demo-data`, `lib/demo-mode`, and `lib/mocks/*` must be removed from product paths. Test-only fixtures may remain under test directories.

## Backend Contract Principles

Each migrated UI block must have a real backend read model before it is shown as real product UI.

Required contract practice:

- Add or extend Pydantic schemas first.
- Regenerate `packages/contracts/openapi.json` and `packages/contracts/_generated.ts`.
- Export feature shims from `lib/contracts/*`.
- Add adapter tests before wiring the UI.
- Keep nullable fields explicit when a feature is intentionally unavailable.
- Hide or degrade UI blocks when a contract field is absent instead of inventing fallback facts.

## Error Handling

No production error path may fall back to mock/demo data.

Frontend behavior:

- `401`: run the existing auth/session recovery flow and show the established auth loading/error state.
- `403`: show the access-locked or entitlement state returned by the backend.
- `404`: show the route-specific empty state for missing date, report, or horary question.
- `422`: show validation feedback using backend field errors when available.
- `5xx` or network failure: show a retryable service error and keep stale cached data visually marked as stale only when the screen already has real cached data.

Backend behavior:

- Return stable error codes/messages for expected domain failures.
- Log sidecar, LLM, payment, and contract-shaping failures with enough context to debug the failing user/date/request without logging secrets.
- Do not mask sidecar or payment failures by fabricating successful astrology/payment data.

## Product Areas

### Day

Current real API is enough for the existing main day screen: headline, status, top flags, reading paragraphs, why sections, important-today data, access, and week strip.

Mock-preview has valuable presentation:

- Day chart renderer.
- Day energy meter.
- Feed-style day summary.
- Evening check-in reminder.
- Some CSS/animation classes.

Required backend additions before full visual parity:

- `dayChart`: real transit planets, natal houses/cusps, computed transit houses, aspects, orb, strength, and chart metadata.
- Structured influence data: top signals, sphere scores, planet influences, or a populated `dayQuality`.
- Lunar facts: phase, illumination, moon sign, lunar day, void-of-course window, and major lunar events when shown.
- Backend-owned concrete guidance facts. UI may render guidance, but must not select personalized advice from static heuristic pools.

Rejected mock logic:

- Static natal houses/planets.
- Date-offset pseudo planet motion.
- Client lunar/retrograde/planetary-day approximations as product truth.
- Parsing `topFlags.summary` for strength.

### Calendar

Current calendar contract supports a basic grid. The frontend currently discards some per-day information that already exists.

Required changes:

- Consume full `CalendarPayload.days[]`, including per-day access.
- Replace backend neutral rotation status with real day scoring.
- Add lunar fields for the lunar strip/toggle before porting that UI.
- Preserve locked/unlocked day behavior through backend access decisions.

The mock lunar strip UI can be ported only after real lunar fields exist.

### Profile

Current issue: the frontend profile hook is localStorage-first and has fake default profile data. The backend profile read/write API is mostly sufficient.

Required changes:

- Make profile hydration real-data-first via `/api/profile`.
- Persist edits through `PUT /api/profile`.
- Preserve coordinates, timezone, and birth details, not only display city names.
- Replace synthetic `use-access` state with a real access summary endpoint or a profile meta extension.
- Keep Telegram auth/provider behavior from main.

Mock-preview widgets can be ported only after real data exists:

- Check-in statistics require `/api/checkin/metrics`.
- Lunar node widget requires real natal special points.
- Transit timeline requires backend/sidecar-derived transit data, not simplified client ephemeris.

### Readings And Natal

Current main natal preview already consumes real `GET /api/natal/preview` data. The mock `NatalChartWheel` is valuable, but the mock page feeds it fake chart data.

Required changes:

- Extend `NatalPreviewRead` with a real `chart` payload from `NatalContextData`: planets, houses, aspects, angles, and house system.
- Port `NatalChartWheel` only as a pure renderer of `preview.chart`.
- Add backend-computed planet strength data before porting the radar. Do not compute dignity/aspect scores in the client.
- Align full-report UI with the real `NatalReportRead` contract.
- Resolve report access/payment semantics before presenting paid report CTAs as enforced purchases.
- Handle invalid report IDs safely on the backend.

Synastry and celebrity compatibility remain coming-soon surfaces until real partner/person data and real endpoints exist.

### Horary

Horary core API already supports quota, list, create, and get flows. The missing real-data contract is chart persistence.

Required changes:

- Persist the immutable horary chart snapshot generated for the question.
- Return that chart snapshot in `HoraryQuestionRead`.
- Port the horary chart UI only after it consumes the persisted real chart.
- Refresh quota after purchase or credit changes.
- Avoid payment success checks based only on existing credits.

Rejected mock logic:

- Deriving pseudo chart positions from `createdAt`.
- Ignoring real time, coordinates, houses, and sidecar output.

### Check-In

Current backend check-in is MVP: `target_date`, `mood`, and `notes`. Mock-preview UI expects richer structured data.

Required changes:

- Extend storage and schemas for numeric mood, accuracy, energy, tags, note, filled-at timestamp, and local target-date semantics.
- Add `/api/checkin/yesterday`.
- Add `/api/checkin/metrics` for streaks, aggregates, and profile stats.
- Use profile/local timezone for date targeting. Do not derive local day with UTC `toISOString().split("T")[0]`.
- Port check-in screen, selectors, reminders, and profile stats only after the contract is real.

### Payment And Paywall

Payment is the highest-risk area. Main backend currently has only an MVP create-intent/webhook shape, while mock-preview expects product catalog, purchase, subscription status, cancel, and confirmation flows.

Required changes before enabling paywall UI:

- Product catalog endpoint.
- YooKassa client integration with confirmation URL/token.
- Subscription start/status/cancel endpoints.
- One-time purchase flow for horary credits or other products.
- Webhook signature verification.
- Idempotency for webhook and fulfillment.
- Fulfillment into access ledger and horary credits.
- Credential hygiene: remove any real-looking credentials from tracked docs and rotate exposed payment credentials before payment work.

Until this exists, paywall/payment UI may be present only as disabled or hidden surfaces, not as a live purchase path.

## Preview And Cutover Plan

1. Create an integration branch from current `main`.
2. Point port `3001` at that integration branch as real-data preview.
3. Keep port `3002` on stable `main`.
4. Remove the mock-preview Next catch-all API from the runtime path.
5. Build each product area as a vertical slice:
   - backend schema/contract,
   - backend service logic,
   - generated contracts,
   - frontend adapter tests,
   - presentation port,
   - Playwright smoke against real auth/API.
6. Run the full acceptance suite on `3001`.
7. Merge the integration branch into `main`.
8. Build and restart `solarsage-frontend.service` on `3002`.
9. Keep rollback as reverting the merge and restarting `3002` from the previous known-good build.

The old mock-preview worktree remains a visual reference only. It must not remain the source of any production runtime.

Manual Telegram WebView testing before cutover requires a separate preview web_app URL routed to `3001` through HTTPS, or a separate preview bot/button. The canonical public Telegram URL must not be repointed from stable `3002` during preview validation. If no preview Telegram URL exists, pre-cutover Telegram coverage is limited to generated real-HMAC initData E2E against `3001`, and one manual Telegram smoke must run immediately after `3002` cutover with rollback ready.

## Decomposition For Implementation

This design should be implemented as separate reviewable plans, not as one giant patch:

1. No-mock foundation and preview environment.
2. Day and calendar real-data visual migration.
3. Profile and access real-data migration.
4. Check-in contract and UI migration.
5. Readings and natal chart migration.
6. Horary chart migration.
7. Payment/paywall backend and UI migration.
8. Final integration, Telegram smoke, and main cutover.

Each plan must be independently testable and must leave the integration branch green. `main` remains stable until the final reviewed merge.

## Testing Strategy

Required test layers:

- Contract generation check: `npm run contracts:check`.
- Frontend unit tests for API clients and adapters.
- Backend pytest for every new schema/service/endpoint.
- Guardrail tests proving product paths do not import runtime demo/mock modules.
- Playwright smoke for Telegram-authenticated routes on `3001`.
- Visual smoke for chart renderers with non-empty SVG/canvas output.
- Payment tests for webhook signature verification, idempotency, and fulfillment before live UI.
- Production smoke after cutover on `3002` before declaring the Telegram issue fixed.

Minimum route smoke set:

- `/day/2026-07-05`
- `/calendar`
- `/profile`
- `/readings`
- `/readings/natal`
- `/horary`
- `/checkin`

When payment is enabled:

- product catalog,
- purchase start,
- return/status,
- webhook fulfillment,
- quota/access refresh.

## Acceptance Criteria

The migration is complete when:

- Port `3001` runs the migrated UI against the real API on port `8000`.
- No product route uses runtime mock/demo data.
- The old mock catch-all API is not present in the production app.
- Day, calendar, profile, readings, natal, horary, and check-in load through Telegram WebApp auth.
- Chart and astrology widgets render only from backend/sidecar facts.
- Calendar statuses and access locks come from backend read models.
- Profile data comes from the backend and edits persist.
- Natal and horary chart visuals use real chart contracts.
- Check-in writes use local/profile date semantics.
- Payment surfaces are either backed by real YooKassa/access fulfillment or hidden/disabled.
- `main` has green unit, backend, contract, and Playwright smoke checks before `3002` is restarted.

## Review Notes

The key architectural rule is stricter than "copy the new frontend": presentation may move from mock-preview, but all facts must come from real contracts. This means some mock-preview UI should be delayed until backend read models exist. That delay is intentional because otherwise `3002` would show polished fake data as production truth.

## Final Preview Runtime Acceptance Notes

Task 10 adds the real-data preview runtime artifact for final integration acceptance:

- `infra/systemd/solarsage-frontend-preview-3001.service` is the repo-tracked template for running `/opt/solarsage-astro-real-data-preview` on `127.0.0.1:3001`.
- The preview unit runs `npm run build` before `next start`, with `NODE_ENV=production`, `PORT=3001`, and `HOSTNAME=127.0.0.1`.
- `/api/*` remains owned by the application `next.config.mjs` rewrite to `http://127.0.0.1:8000/api/:path*`; the preview unit does not introduce mock API routes or point at port `8001`.
- `scripts/preview-3001-smoke.sh` is the final local runtime smoke. It checks `/day/2026-07-05`, `/calendar`, referenced `/_next/static/*` assets, and `/api/health` through `3001`, failing if the health payload is mock/demo.

Final acceptance for this branch requires the full local suite plus real-HMAC Playwright against `E2E_BASE_URL=http://127.0.0.1:3001`. Port `3002` remains production and must not be touched during preview acceptance.
