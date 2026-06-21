# SolarSage Astro — Worklog / Handover Document

Source repository: https://github.com/basilivanov/solarsage-astro
Local clone: `/home/z/solarsage-astro`
Active project: `/home/z/my-project` (Next.js 16, runs on port 3000)

---

## Task ID: 1
Agent: Z.ai Code (main)
Task: Clone the solarsage-astro repository, lift the server in the sandbox, verify it runs, and create a recurring web-dev-review cron job.

Work Log:
- Cloned `https://github.com/basilivanov/solarsage-astro.git` (main branch) to `/home/z/solarsage-astro` using the provided GitHub PAT.
- Inspected the project: Next.js 16 (App Router) frontend + FastAPI backend (`apps/api`) + SolarSage Python sidecar (`apps/solarsage`) + PostgreSQL + Redis + Telegram WebApp auth. Canonical ports (per `AGENTS.md`): 5433 PG, 8000 API, 3000 frontend, 18091 sidecar.
- Sandbox constraint: only port 3000 is externally exposed via the Caddy gateway; no Python / Postgres / Redis available. Decided to run the Next.js frontend standalone and serve mock data for the backend.
- The project ships with a built-in demo mode (`NEXT_PUBLIC_DEMO_MODE=true` → `lib/demo-data.ts` fixtures, `IS_DEMO_MODE` short-circuits most `lib/api/*` and `lib/grace/api/client.ts` fetches). Used this as the primary data source.
- Migrated the frontend into the active `/home/z/my-project` workspace:
  - Removed the previous scaffold (`src/`, `prisma/`, `tailwind.config.ts`, etc.).
  - Copied `app/`, `components/`, `lib/`, `hooks/`, `types/`, `packages/contracts/`, `public/`, `next.config.mjs`, `postcss.config.mjs`, `eslint.config.mjs`, `components.json`, `tsconfig.json`, `next-env.d.ts` from solarsage-astro.
  - Rewrote `package.json`: kept bun-based scripts, added `@vercel/analytics`, **downgraded `zod` to `^3.24.1`** (solarsage uses the zod 3 API in `lib/contracts/*`; zod 4 has breaking changes), added a no-op `db:push` script (no Prisma in this project).
  - `bun install` → 209 packages, zod resolved to 3.25.76.
- Adapted `next.config.mjs`: removed the `rewrites()` proxy to `http://127.0.0.1:8000` (no FastAPI in sandbox) and added `allowedDevOrigins` for `127.0.0.1`, `localhost`, `*.space-z.ai`, `*.preview.chat` (without this, Next.js dev blocks the HMR websocket and fonts with cross-origin 403s → client hydration silently fails → page stuck on the "Авторизация…" spinner).
- Created `.env.local` with `NEXT_PUBLIC_DEMO_MODE=true`, `ALLOW_DEMO_MODE_IN_PREVIEW=true`, `NEXT_PUBLIC_APP_ENV=dev`, `NEXT_PUBLIC_DEV_AUTH=true`, `NEXT_PUBLIC_GRACE_LOG_SHIPPING=false`.
- Added a single catch-all mock API route: `app/api/[...path]/route.ts` that serves demo data for every backend endpoint the frontend calls (`/api/profile`, `/api/day/:date`, `/api/calendar`, `/api/horary/*`, `/api/natal/*`, `/api/chat/*`, `/api/geo/*`, `/api/checkin/*`, `/api/payment/*`, `/api/referral/*`, `/api/auth/dev`, `/api/auth/telegram`, `/api/_log`). This covers the code paths that bypass the demo-mode guard (e.g. `useOnboarded` polls `GET /api/profile` directly, the root layout ships `POST /api/_log`).
- Hit a Turbopack hang: with the default `next dev` (Turbopack), compiling `/day/today` pegged the CPU at ~80% for 5+ minutes and never produced a response. Switched the `dev` script to `next dev -p 3000 --webpack` — `/day/today` now compiles in ~2.1 s. Webpack is more memory-stable for this project's large import graph.
- Started the server via the canonical `.zscripts/dev.sh` (which `bun install` → `bun run db:push` → `bun run dev &` + `disown`, then a health check). This is the environment's expected mechanism and the process survives across tool calls.
- Verified end-to-end with `agent-browser`:
  - `GET /` → 200, client redirects to `/day/<today>`.
  - `/day/today` renders the full Today screen: date header, trial banner ("14 дней бесплатного доступа"), "Сегодня важно" accordion (3 expandable items), "Разбор дня" reading, "Почему так у меня" section, week strip (ПН–ВС), 5-tab bottom navigation (Сегодня / Календарь / Разборы / Спросить / Профиль).
  - Accordion expand/collapse works.
  - `/calendar` renders June 2026 month grid with per-day status badges (ровный / поддерживающий / напряжённый).
  - `/readings` renders "Глубокие разборы" landing.
  - `/profile` renders "Гость" / "Telegram mini-app" / "ДОСТУП" section.
  - Screenshots saved: `screenshot-today.png`, `screenshot-calendar.png`, `screenshot-readings.png`, `screenshot-profile.png`.
- Known non-blocking dev warning: React hydration-mismatch on first load (the Telegram WebApp bootstrap script mutates the DOM before React hydrates). React auto-recovers; the app renders and is fully interactive. This is expected behaviour when running a Telegram-WebApp outside Telegram and does not need fixing for the demo.

Stage Summary:
- Server is live on port 3000, demo mode enabled, all main routes (Today / Calendar / Readings / Profile) verified interactive via agent-browser.
- Architecture decision: Next.js frontend runs standalone; the FastAPI/SolarSage/Postgres backend is replaced by `app/api/[...path]/route.ts` (mock) + `lib/demo-data.ts` (fixtures). The original backend code is preserved in `/home/z/solarsage-astro/apps/` for reference but not executed.
- Key config gotchas for the next agent: (1) must use `--webpack` not Turbopack, (2) `allowedDevOrigins` must include `127.0.0.1`/`localhost`, (3) `zod` must stay on v3, (4) start the server via `.zscripts/dev.sh` so the process is disowned properly.

Unresolved issues / risks:
- Hydration-mismatch dev warning (cosmetic, expected outside Telegram).
- The "Спросить" (chat) and horary flows are mocked with static replies — real LLM/astrology engine not wired.
- YooKassa payment routes return mock `confirmationUrl: /profile` — no real checkout.
- Next steps the recurring webDevReview cron should consider: polish the demo experience (e.g. make the chat tab return a richer canned response, surface the natal report demo), tighten the hydration mismatch if feasible by guarding Telegram WebApp calls behind `typeof window` checks, and add more visual detail / micro-interactions per the recurring task mandate.

