# Report 002 — latency and positioning package (2026-07-18)

Status: implemented per `001_TZ_LATENCY_POSITIONING.md`. Source-only; no production actions, no Bot API calls, no service restarts, no commits/pushes. tmux alive.

## A. Default LLM model — done

- Official OpenRouter `/api/v1/models` verified live: `openai/gpt-4.1-nano` exists with `canonical_slug: openai/gpt-4.1-nano-2025-04-14`, context 1,047,576, pricing $0.1/M prompt + $0.4/M completion (cheaper than gpt-4o-mini).
- Replaced the active default in: `apps/api/app/core/config.py` (`Field("openai/gpt-4.1-nano", alias="LLM_MODEL")`), `infra/production/docker-compose.app.yml` (`LLM_MODEL: ${LLM_MODEL:-openai/gpt-4.1-nano}`), `apps/api/tests/test_llm_service.py` (2 assertions), `docs/PRODUCTION_RUNBOOK.md` (E2E low-cost model note), `.github/workflows/e2e.yml` (`export LLM_MODEL=...`).
- `LLM_MODEL` env override preserved (pydantic alias + compose `${LLM_MODEL:-...}`). rg: zero active `gpt-4o-mini` refs left.

## B. Cold-day latency — done

- `today_service.py`: all deterministic contexts (why_evidence_packet, important_items, day_chart, planet_influences, sphere_scores) are computed first; then ONE `asyncio.gather` runs headline + reading + notes + why_sections + `interpretation_service.build(...)` concurrently. DB session ops (semantic-layer cache write) stay sequential before the gather. Fallback placeholders and payload order unchanged. Module contract updated.
- `today_interpretation_service.py`: planets_context computed up-front; ONE `asyncio.gather` runs the concrete-advice 12-sphere batch and the planet-interpretations batch concurrently. Application/validation/fallback logic byte-preserved (`has_planet_context` gate; `asyncio.sleep(0, result=None)` for the absent branch). Concrete advice remains ONE batch — never split per row.
- Focused proof `apps/api/tests/test_today_llm_gather_overlap.py`: ONE shared barrier over all six calls (headline, reading, notes, why, advice, planets). Passing requires ALL six to start before any ends — a sequential executor, and even a partially-parallel one (e.g. inner pair awaited only after the outer four complete), deadlocks and fails. Asserts full cross-overlap, `elapsed < barrier_timeout`, preserved placeholder/batch/planet semantics, and zero leaked coroutines (all_tasks qualname scan). 1 passed. (Strengthened from the initial two independent group barriers, which did not prove cross-group overlap — see the final-review section.)
- Regression handling: `test_today_preview_transport.py` prefetch guard updated precisely — background `create_task`, `_prefetch_week`, `_TODAY_PREFETCH_TASKS`, `SessionLocal` stay forbidden; foreground request-local same-day gather explicitly allowed. Anti-prefetch invariant NOT weakened.
- Full pytest from repo root: 1474 passed, 4 skipped, 0 failed. (3 apparent failures when run from `apps/api` are pre-existing cwd-path artifacts — `horizon_pipeline_service` relative path and `scripts` import — both pass from repo root; verified 17 passed.)

## C. Frontend latency and prefetch cost — done

- `lib/grace/hooks/useDay.ts`: artificial `await 100ms` removed; contract updated (request starts immediately once auth is ready). Test `__tests__/hooks/useDay.test.ts` +1: with fake timers and NO time advance, `fetchDay` fires in the first microtask flush and `getTimerCount() === 0` — hard proof the delay is gone. 10/10.
- `app/(grace)/day/[date]/page.tsx`: artificial 600 ms `CosmicLoader` hold removed; loader shows only while `!ready`. Accessible states kept (`CosmicLoader` status + `ErrorBoundary` alert). Test `__tests__/app/day-page.test.tsx` +1: ready payload renders `TodayScreen` immediately with fake timers and zero advance, loader absent, `getTimerCount() === 0`. 3/3.
- `components/today/week-strip.tsx`: mount-time `Promise.all` 7-day load deleted. New idempotent `warmDay(d, accessible, active)`: fires only on `onPointerEnter`/`onFocus` of an accessible, inactive, unlocked day; max one request per date per mount (requestedDates set); locked and active days never warm; `disableRemoteStatusFetch` disables entirely. Uses existing `getDayStatus` (warms day cache); no new backend endpoint, no router prefetch needed. GRACE contract updated.
- `__tests__/components/WeekStrip.test.tsx` rewritten to the intent contract: 0 calls on mount; exactly 1 on first intent (applied to aria-label); no duplicate on hover+focus repeats; 2 distinct days → 2 calls; active day → 0; locked day → 0; disabled flag → 0; failed warmup → that day only shows "статус недоступен". 8/8.
- Full vitest: 1095 passed, 1 failed — the failure is PRE-EXISTING and unrelated: `no-yookassa-live-credentials.test.ts` hits ENOENT on `e2e/mock-visual/.../01-human-first-overview-mobile-mobile-linux.png`, a git-tracked PNG deleted from the worktree before this package (visible in the initial `git status` as `D`). Not touched per boundaries.

## D. Positioning / share / bot copy — done (with one honest blocker)

- Share default (`lib/hooks/use-share-invite.ts`, exported `SHARE_TEXT`): «Слушай, жутко точно: тут считают день по моей натальной карте — сфера за сферой всё про меня. Глянь свой, это 30 секунд:\n\nПо моей ссылке мы оба получим по 14 дней полного доступа.» Contract updated (tone invariants; inviteUrl keeps `startapp=` form). `navigator.share` fallback aligned.
- Referral truth: `apps/api/app/api/referral.py` grants `grant_referral_bonus` to BOTH invitee and referrer with `days_granted=14`/`daysPerInvite=14`. Existing endpoint test extended with `test_claim_referral_grants_both_users_exactly_14_days` — exactly two ledger entries, both `days_granted == 14`, one per user. 9/9 referral tests.
- `__tests__/hooks/use-share-invite.test.ts`: exact accepted copy + motivator; «гороскоп» only with negation; ты-form, no esoteric pathos; share URL keeps `t.me/vi_astro_bot/app?startapp={id}` and never `start=ref_`. 4/4.
- Bot profile: `scripts/telegram/bot-profile.json` (bio/short description, description, menu button «Открыть мой день ✨» → canonical `https://astro.vasiliy-ivanov.ru/day/today`, canonical `start_copy`) + `scripts/telegram/sync_bot_profile.py`: `--check` default (validate + print intended ops, NO HTTP), `--apply --manual-confirm` (exact three POSTs: setMyShortDescription, setMyDescription, setChatMenuButton). Token only from `TELEGRAM_BOT_TOKEN` env or explicit `--env-file`; never printed. Length limits enforced (120/512/64/4096). Tone rule enforced. start_copy validated + reported but NOT synced. (WebApp URL form finalized in the follow-up section below.)
- `apps/api/tests/test_sync_bot_profile.py`: 13/13 — config validity, check-mode no-HTTP, apply-without-confirm → 78, exact 3 calls with exact payloads, zero token leak, limit failures, tone violation failure, start_copy never synced, env-file-only token, canonical WEBAPP_URL + /day/today CTA contract.
- `/start` Ductor audit (read-only): pipx `ductor_bot.messenger.telegram.app._on_start` is hardcoded to `_show_welcome` → `build_welcome_text` from package-internal i18n TOML; the i18n loader reads only package dirs; `~/.ductor/config/config.json` has no welcome/start override fields. **Supported override: ABSENT.** Per TZ, no monkeypatch/sitecustomize/vendor/fork/pipx changes were made.
- **Blocker (honest):** canonical /start copy cannot be deployed to the current Ductor bot through a supported path. It lives ready in `scripts/telegram/bot-profile.json` (`start_copy` + CTA composed as canonical WEBAPP_URL + `/day/today`) with tests, for a future dedicated product-bot handler. Ductor's generic /start is untouched.

## Changed files

- `apps/api/app/core/config.py`, `apps/api/app/services/today_service.py`, `apps/api/app/services/today_interpretation_service.py`, `infra/production/docker-compose.app.yml`, `.github/workflows/e2e.yml`, `docs/PRODUCTION_RUNBOOK.md`
- `apps/api/tests/test_llm_service.py`, `test_referral_endpoints.py`, `test_today_preview_transport.py`, + new `test_today_llm_gather_overlap.py`, `test_sync_bot_profile.py`
- `lib/grace/hooks/useDay.ts`, `app/(grace)/day/[date]/page.tsx`, `components/today/week-strip.tsx`, `lib/hooks/use-share-invite.ts`
- `__tests__/hooks/useDay.test.ts`, `__tests__/app/day-page.test.tsx`, `__tests__/components/WeekStrip.test.tsx`, + new `__tests__/hooks/use-share-invite.test.ts`
- `scripts/telegram/bot-profile.json`, `scripts/telegram/sync_bot_profile.py`

## Verification (final battery)

- Full pytest (repo root): 1474 passed, 4 skipped, 0 failed.
- Full vitest: 1095 passed, 1 pre-existing unrelated failure (tracked-but-deleted PNG, see C).
- `python3.12 -m py_compile` changed Python files: 0. `sync_bot_profile.py --check`: rc 0, no HTTP.
- `npx eslint` changed TS/TSX files: 0.
- `git diff --check`: 0.

## Explicit non-actions

No production actions, no Bot API calls (`--apply` never executed), no service restarts, no Ductor/pipx changes, no commits/pushes, no new backend endpoints, no new harness/framework. Unrelated dirty worktree, `.grace/`, artifacts and historical docs untouched.

## Follow-up review (audit fixes, pre-final)

### 1. Ignored env model refs — aligned (intentionally NOT committed)

`rg -uu` found three live model pins outside git tracking:

- `.env:53` and `.env.production:51`: `OPENROUTER_MODEL_NATAL=openai/gpt-4o-mini`
- `apps/api/.env:9`: `LLM_MODEL=openai/gpt-4o-mini`

All three aligned to `openai/gpt-4.1-nano` via anchored sed on the exact value line only; no other lines touched; re-grep confirms 0 remaining `gpt-4o-mini` in all three files (values verified, secrets never printed). Notes:

- `OPENROUTER_MODEL_NATAL` has **no code references** anywhere in `apps/api/app`, `infra`, `docs` (rg verified) — a stale/unused variable; aligned anyway so no future consumer picks up the old model.
- `LLM_MODEL` in `apps/api/.env` is the live local-dev override of the config default; it now matches the new code default, so dev behavior is identical to a fresh clone.
- **Intentionally not committed:** `.env`, `.env.production`, `apps/api/.env` are gitignored secret-bearing runtime files. This was a local runtime config alignment only — no service restart, no production action.

### 2. Bot WebApp CTA — canonical WEBAPP_URL + /day/today (decision: yes)

Decision: replaced the `t.me` deep-link form with the canonical absolute `WEBAPP_URL` + `/day/today`. Rationale:

- `WEBAPP_URL` is the repo's canonical webapp base (`.env.production` → `https://astro.vasiliy-ivanov.ru`; the domain is public — same value in `docs/PRODUCTION_RUNBOOK.md` and `infra/nginx/astro.vasiliy-ivanov.ru.conf`).
- Route validity verified: `app/(grace)/day/` has only the dynamic `[date]` segment; literal `today` reaches `NormalDayPage` where `fromDateParam(dateStr) ?? TODAY` resolves it. The root page `/` and legacy `/today` both redirect to `/day/today`, so the target is canonical, not invented.

Implementation:

- `bot-profile.json` now stores `webapp_url` + `day_path` (single source); per-field URLs removed from `menu_button` and `start_copy.cta`.
- `sync_bot_profile.py` new `load_webapp_url(config, env_file)`: `WEBAPP_URL` env → `WEBAPP_URL=` in `--env-file` → config default; trailing slash normalized; https enforced (exit 78 otherwise). Menu payload and reported CTA use the composed URL. Token handling unchanged.
- Contract tests (13/13 in `test_sync_bot_profile.py`): composed default is exactly `https://astro.vasiliy-ivanov.ru/day/today`, https, never `t.me`, ends with `day_path`, menu payload carries it; env override honored (`https://dev.astro.vasiliy-ivanov.ru/day/today`); env-file override honored; `--check` output contains the canonical URL and no `t.me`.

### 3. Module-map path mismatch — fixed

`sync_bot_profile.py` `START_MODULE_MAP` `owned_tests` pointed at the non-existent `scripts/telegram/test_sync_bot_profile.py`; corrected to the real `apps/api/tests/test_sync_bot_profile.py`. Test module contract header also extended with the WebApp URL invariant.

### 4. Overlap proof — honest limitations

The six-call overlap test (`test_today_llm_gather_overlap.py`) is sound for what it proves; its limits, stated plainly:

- It proves **scheduling overlap under mocks**: ONE shared barrier blocks every mocked call until ALL six (headline, reading, notes, why, advice, planets) have started, so a sequential — or only partially-parallel — executor deadlocks and fails via the 3 s timeout. It does **not** measure wall-clock latency improvement; real gain depends on OpenRouter response times.
- `llm_service.py` creates a **fresh `httpx.AsyncClient` per call** (two call sites), so parallel calls are NOT serialized behind a shared connection pool — real overlap is not capped by a shared client. Cost: each call pays its own connection setup and there is no keep-alive reuse across the six calls. Left as-is (possible future optimization, out of scope).
- The inner gather (concrete advice + planet interpretations) starts inside `interpretation.build` after its deterministic preamble, while `build` itself is one of the five outer gather participants — intended ordering, and the single shared release proves the inner calls overlap the still-in-flight outer ones.
- The sequential-detector relies on the 3 s barrier timeout, i.e. it assumes calls are not instantaneous. True for real network LLM calls; a hypothetical executor that serializes instant calls would evade it — accepted, documented.
- `asyncio.gather` without `return_exceptions` — precise semantics: the first exception is propagated immediately to the awaiting coroutine; the sibling awaitables are **NOT cancelled by gather** — they keep running in the background and their results are discarded (children are cancelled only if the gather future itself is cancelled). Sequential code would simply never have started the later calls. Impact here is minimal because per-call fallback wrappers catch expected LLM/validation errors before they reach gather; a truly unexpected error can therefore leave sibling requests running detached until completion — standard asyncio semantics, accepted and documented. (An earlier draft of this section wrongly claimed gather cancels siblings on first exception — corrected in the final review.)
- Leak check: the test asserts no leftover `_mock` tasks in `asyncio.all_tasks()` after completion — no coroutine leaks observed.

### Follow-up verification

- Focused pytest: 73 passed (`test_today_llm_gather_overlap.py` 1 — single-barrier version, `test_sync_bot_profile.py` 13, `test_today_preview_transport.py` 59).
- Focused vitest: 25 passed (`use-share-invite`, `WeekStrip`, `useDay`, `day-page`).
- `python3.12 -m py_compile` changed files: OK. `sync_bot_profile.py --check`: rc 0, no HTTP, canonical URL in output.
- New files are untracked (no commits per constraints); manual whitespace/EOF check on them: clean. `git diff --check`: 0.
- No Bot API calls, no production actions, no commits/pushes.

## Final review fixes (round 2)

Three concrete corrections, no new layers.

### 1. useDay no-delay proof — false proof fixed

The original test called `vi.runAllTimersAsync()`, which really advances virtual time — an old 100 ms `setTimeout` would have fired and the "proof" would still pass. Fixed: fake timers are active but **never advanced** (`await act(async () => {})` flushes only effects + promise microtasks); assertion requires `fetchDay` called AND `vi.getTimerCount() === 0`. A lingering 100 ms gate would now fail both clauses. Timer restore is guaranteed via `try/finally vi.useRealTimers()`. (Shipper-timer interference ruled out: `LogShipper` schedules its flush timer only when `NEXT_PUBLIC_GRACE_LOG_SHIPPING === "true"`, unset in tests.) 10/10.

### 2. Six-call overlap — single shared barrier

The initial two independent barriers (4 outer + 2 inner) did NOT prove cross-group overlap: the outer four could complete fully before the inner pair started and both groups would still pass. Replaced with ONE shared barrier over all six names — release fires only when headline, reading, notes, why, advice AND planets have all started, so no call may complete before all six are in flight. Sequential and partially-parallel executors deadlock into the 3 s timeout and fail. The real implementation passes, which now genuinely proves the inner pair starts while the outer calls are still blocked. The earlier draft's claim that "gather cancels siblings on first exception" was wrong and is corrected above (siblings are not cancelled; they run detached, results discarded).

### 3. Share invite — honest fallback without bonus promise

`DEFAULT_URL` (`https://t.me/vi_astro_bot?start=invite`) could be shared on API failure while the text still promised "мы оба получим по 14 дней" — an unattributed link cannot grant that bonus. Fixed in `lib/hooks/use-share-invite.ts`:

- New `buildFallbackInviteUrl()`: canonical attributed fallback `https://t.me/vi_astro_bot/app?startapp={id}` from `window.Telegram.WebApp.initDataUnsafe.user.id` — the same form the API returns and the frontend auto-claim consumes (`start_param`).
- New exported `SHARE_TEXT_GENERIC`: the variant-1 copy WITHOUT the bonus line.
- `share()` selects: API inviteUrl → `SHARE_TEXT`; else startapp fallback → `SHARE_TEXT` (attributed, promise honest); else generic `https://t.me/vi_astro_bot/app` → `SHARE_TEXT_GENERIC` (no promise). GRACE contract invariants/failure_policy updated.

Focused tests +2 (`__tests__/hooks/use-share-invite.test.ts`, 6/6 total): API failure + Telegram user id → shared URL is the canonical `?startapp=424242` link and the motivator is present; API failure + no user id → shared URL is the generic `/app` link, no `startapp`, and the decoded text contains no «мы оба получим». The old `?start=invite` form is gone everywhere.

### Final-review verification

- Targeted final vitest: 27 passed, 4 files (`useDay` 10, `day-page` 3, `use-share-invite` 6, `WeekStrip` 8 — includes the `lockedAccess.state` type fix to canonical `'none'` per the `AccessInfo` contract, confirmed by `npx tsc --noEmit` rc 0).
- Focused pytest: 73 passed (`test_today_llm_gather_overlap.py` 1 — single-barrier version, `test_sync_bot_profile.py` 13, `test_today_preview_transport.py` 59).
- `npx eslint` on changed TS files: 0. `python3.12 -m py_compile` changed test: OK.
- `git diff --check`: 0. No Bot API calls, no production actions, no commits/pushes.
