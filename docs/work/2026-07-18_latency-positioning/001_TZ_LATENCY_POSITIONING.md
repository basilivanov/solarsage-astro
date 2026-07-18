# TZ — latency and positioning package (2026-07-18)

Post-checkpoint `6b50261`. Work only in `/opt/solarsage-astro`. Do not touch `/home/astro/.ductor` or the pipx ductor install. No production actions, Bot API calls, service restarts, commits or pushes.

## A. Default LLM model

- Official OpenRouter `/api/v1/models` must confirm `openai/gpt-4.1-nano` (canonical slug `openai/gpt-4.1-nano-2025-04-14`); use the stable alias `openai/gpt-4.1-nano`.
- Replace active default `openai/gpt-4o-mini` in runtime/test/docs: `apps/api/app/core/config.py`, `infra/production/docker-compose.app.yml`, `apps/api/tests/test_llm_service.py`, `docs/PRODUCTION_RUNBOOK.md` and any other active refs found.
- `LLM_MODEL` env override must keep working.

## B. Cold-day latency / cost

- In `apps/api/app/services/today_service.py` and `today_interpretation_service.py`, parallelize the 6 independent LLM calls via `asyncio.gather` as early as deterministic contexts allow: headline, reading, notes, why, concrete advice (ONE 12-sphere batch), planet interpretations.
- Do not parallelize DB session operations. Preserve fallback/validation/error semantics and final payload order.
- Concrete advice stays one batch; never split into 12 requests.
- Focused async tests with Events/barrier/timing that prove real overlap, plus no coroutine leaks/cancellation regressions.

## C. Frontend latency and prefetch cost

- Remove the artificial 100 ms await in `lib/grace/hooks/useDay.ts` (+ GRACE contract/tests).
- Remove the artificial 600 ms CosmicLoader hold in `app/(grace)/day/[date]/page.tsx`; loader disappears at ready; accessible loading/error states stay.
- Remove the mount-time `Promise.all` 7-day status prefetch in `components/today/week-strip.tsx` (7× `/api/day`, LLM warm ×7).
- Replace with user-intent warmup only on hover/pointer-enter and keyboard focus for an accessible, inactive, unlocked day. Idempotent: max one request per date per mount; no hover+focus duplicates; never locked/active. Use current `getDayStatus` (warms day cache); no new backend endpoint.
- Tests: 0 status calls on mount; 1 on first intent; no duplicates; no locked/active prefetch; no 100/600 ms delays.

## D. Positioning / share / bot copy

- Tone: «не гороскоп для всех, а расчёт по твоей натальной карте», на ты, no esoteric pathos; «гороскоп» only with negation.
- Share default (variant 1): «Слушай, жутко точно: тут считают день по моей натальной карте — сфера за сферой всё про меня. Глянь свой, это 30 секунд:» + honest motivator «По моей ссылке мы оба получим по 14 дней полного доступа.» (referral.py + tests must prove BOTH get 14.)
- Keep working API inviteUrl `https://t.me/vi_astro_bot/app?startapp={tg_user_id}`; do NOT switch to `?start=ref_` without a project-owned `/start` handler + test.
- Bio, description, /start copy per accepted texts; menu button CTA «Открыть мой день ✨».
- Bot profile: repo-owned config + manual-gated sync script (`--check` default, `--apply --manual-confirm`) for setMyShortDescription, setMyDescription, setChatMenuButton. Token only from env/explicit env-file, never printed. No Bot API calls in this slice.
- /start: audit the supported Ductor override first. If absent (preliminary: yes), NO monkeypatch/sitecustomize/vendor/fork/pipx changes — record an honest blocker and keep canonical start copy in repo config + tests for a future dedicated product-bot handler. Implement all other copy/share changes.
- Update tests for share text, referral link/bonus truth, bot copy length limits, and the manual gate.

## E. Boundaries

- No new big harness/framework; focused tests only.
- GRACE headers/contracts for substantial changes; keep the UI test contract.
- Do not touch unrelated dirty snapshots / `.grace/` / artifacts.
- Run focused pytest/vitest/type checks; `git diff --check`.
- Full report and stop; tmux stays alive.
