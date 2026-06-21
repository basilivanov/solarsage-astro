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


---
Task ID: 2
Agent: Z.ai Code (recurring webDevReview cron, round 1)
Task: Assess project status, QA via agent-browser, fix bugs, add features + styling polish, update worklog.

Work Log:
- Read previous worklog (Task ID: 1) to understand baseline: server live on port 3000, demo mode, all main routes 200, hydration-mismatch warning present, chat tab gated behind "Скоро" placeholder.
- QA pass with agent-browser on all 8 page routes + 6 API routes — all return 200, no runtime errors. Identified the single dev-overlay "1 Issue" badge: a React hydration-mismatch on `<html>` (root layout) caused by the external `telegram-web-app.js` script injecting `style="--tg-viewport-height:100vh;--tg-viewport-stable-height:100vh"` after SSR.
- **Bug fix #1 (hydration):** Added `suppressHydrationWarning` to `<html lang="ru" className="bg-background">` in `app/layout.tsx`. This is the canonical React solution for third-party DOM mutations. Verified: the "1 Issue" badge is gone and no hydration-mismatch warnings remain in console.
- **Feature #1 — Day Chart visualization** (`components/today/day-chart.tsx`, ~500 LOC): New SVG-based astrological wheel rendered on the Today screen between the "Сегодня важно" accordion and "Разбор дня". Shows:
  - 12 zodiac slices (♈–♓) with alternating tints on the outer ring.
  - 12 house cusps as spokes (ASC/1st house highlighted in plum), with house numbers 1–12 in the house ring.
  - 7 planets (Sun–Saturn) positioned by ecliptic longitude on a planet ring, each as a clickable colored disk with its traditional glyph (☉☽☿♀♂♃♄). Planet colors follow traditional astrological associations.
  - Aspect lines drawn between planets in close orb: conjunction (plum), opposition (red), trine (green), square (amber), sextile (blue) — with a legend below.
  - Center disk shows the date label (e.g. "21 июн") + "КАРТА ДНЯ", with a soft glow keyed to the day status color.
  - Click a planet → animated popover with the planet's glyph, name, sign+house, and a contextual description (e.g. "Venus · ♒ Aquarius · 5 дом — любовь, удовольствие, ценности. Сегодня акцент через 5 дом — творчество и романтика.").
  - Day-to-day variation: planet longitudes shift based on the selected date (Moon +13°/day, Sun +1°/day, others +0.3°/day) so the chart visually changes when navigating the week strip.
- **Feature #2 — Day Energy Meter** (`components/today/day-energy-meter.tsx`, ~155 LOC): New section below the Day Chart. Shows:
  - Status pill ("Ровный день" / "Поддерживающий день" / "Напряжённый день") with a pulsing accent dot and the dominant planet.
  - Stacked horizontal bar with shimmer animation, segments sized by each planet's strength.
  - Per-planet rows: glyph chip, name, individual progress bar, numeric strength (0–100). Strengths are parsed from the API `topFlags` summaries (regex on "сила: 0.94"). Sun + Moon are always included as baselines.
  - Contextual hint paragraph keyed to the day status.
- **Feature #3 — Chat unlocked + context-aware replies:** Replaced the `LockedFeatureCard` placeholder on `/chat` with the real `ChatScreen` (loads the demo profile via `getProfile()`, coerces API shape → local `Profile` contract). Enhanced `lib/api/chat.ts` demo mode with a `generateDemoReply()` keyword matcher (11 categories: greetings, relationships, career, money, health, evening plans, astrology meta, emotions, decisions, thanks, default) — each returns a rich, astrologically-themed Russian response referencing the day's actual aspects. Tested: sending "Что сегодня важно знать про отношения?" returns the love/relationships response about Venus-Jupiter conjunction.
- **Mock API enrichment** (`app/api/[...path]/route.ts`):
  - `GET /api/checkin/yesterday` now returns the full `CheckinResult` shape (`{hadCheckin, checkin:{id, targetDate, mood, accuracy, energy, tags, note, streak, filledAt, createdAt}}`) instead of the old minimal object.
  - `GET /api/checkin/:date` returns demo checkins for the last 3 days (with varied moods/tags), 404 for older dates — so the checkin screen shows real history.
  - `GET /api/checkin/metrics` returns aggregate stats (totalCheckins, currentStreak, longestStreak, averageMood, moodDistribution, tagFrequency) for future metrics UI.
  - `POST /api/checkin` returns a proper `CheckinResult` with `id`, `streak`, `createdAt` so the toast ("Streak: N дней подряд 🔥") works.
- **Styling polish** (`app/globals.css` + component classes):
  - New keyframes: `chart-fade-in`, `chart-glow` (center disk pulses), `energy-bar-shimmer`, `status-pulse-soft`, `section-rise`.
  - `.cosmic-header-bg` — multi-radial-gradient header backdrop (plum/amber/blue tints) on the DateHeader wrapper.
  - `.stardust-bg` — subtle 4-point star sprinkle pattern (available for day-reading section).
  - `.planet-chip` hover lift with plum shadow.
  - `.energy-stacked-bar` shimmer overlay on the energy meter's stacked bar.
  - `.section-rise-1..5` staggered entrance animations for Today screen sections (accordion → chart → energy → reading → why).
  - All animations respect `prefers-reduced-motion`.
- Wired the new components into `components/today/today-screen.tsx`: added `rawData` prop, `deriveChartAndEnergy()` helper that extracts planet strengths from `topFlags` and builds chart data from static natal houses + day-shifted planet longitudes. The day page (`app/(grace)/day/[date]/page.tsx`) now passes `rawData={data}` to `TodayScreen`.
- Lint: my new/modified files pass cleanly (`npx eslint` on the 6 files → 0 errors, 0 warnings). The remaining 165 project-wide lint errors are all pre-existing in the cloned solarsage-astro codebase (browser globals `Node`/`getComputedStyle`/`module` not configured, escape-character nits) and don't affect the running app.

Stage Summary:
- **Bugs fixed:** hydration-mismatch warning eliminated via `suppressHydrationWarning` on `<html>`.
- **Features added:** (1) Day Chart — interactive SVG astrological wheel with planets, houses, aspects, click-to-detail popover; (2) Day Energy Meter — planetary strength visualization with status pill and per-planet bars; (3) Chat tab unlocked with 11-category context-aware demo replies; (4) Checkin mock API now returns full `CheckinResult` shape + 3-day history + metrics.
- **Styling polish:** cosmic gradient header, stardust pattern, chart glow animation, energy bar shimmer, staggered section entrance animations, planet chip hover effects — all reduced-motion aware.
- **Verification:** all 14 routes (8 pages + 6 API) return 200; agent-browser confirms Day Chart, Energy Meter, and Chat all render and respond correctly; no dev-overlay issues remain. Screenshots: `screenshot-today-v3.png`, `screenshot-today-final.png`, `screenshot-chat-v2.png`.

Unresolved issues / risks:
- The 165 pre-existing lint errors in the cloned codebase (browser globals) — cosmetic, don't block the app. A future round could add a `globals` property to the ESLint config to resolve them, but that's a codebase-wide change.
- Chat replies are keyword-matched, not LLM-generated — good enough for the demo but a real backend (FastAPI + LLM provider) would be needed for production.
- The Day Chart uses static natal houses (from `DEMO_NATAL_RESPONSE`) with day-shifted planet longitudes as a visual approximation. Real transit calculation would require the SolarSage Python sidecar.
- Next round recommendations: (1) surface the checkin metrics in a new "Статистика" section on the Profile screen; (2) add a natal report preview using `DEMO_NATAL_PREVIEW` on the Readings screen; (3) consider adding a "Луна сегодня" (Moon today) widget showing the current moon phase + sign; (4) add dark-mode toggle wiring (the `.dark` CSS vars exist but no toggle UI in demo mode).
