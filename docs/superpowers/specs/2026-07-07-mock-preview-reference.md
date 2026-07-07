# Mock Preview Visual Reference Package

## Purpose

This package makes the old `/opt/solarsage-astro-mock-preview` visual oracle portable through git for the future frontend migration agent.

The old preview on port `3001` remains a temporary visual reference only. It is not canonical runtime, not a data-contract source, and not approval to port mock APIs or fabricated astrology into `main`.

Canonical runtime remains:

- Frontend: `solarsage-frontend.service` on port `3002`.
- API: FastAPI on port `8000`.
- Auth: Telegram WebApp HMAC -> `/api/auth/telegram`.
- Mock visual tests: Playwright `page.route("**/api/**", ...)` only.
- MSW: not used.

## Captured Source

- Source URL base: `http://127.0.0.1:3001`
- Capture date: `2026-07-07`
- Viewport: mobile `390x844`
- Browser: Playwright Chromium
- Capture method: Playwright page screenshots from the locally available mock-preview, with Next.js dev-only overlay hosts hidden before capture.
- Artifact directory: `docs/superpowers/specs/assets/2026-07-07-mock-preview/`

Capture command shape used for the corrected oracle:

```js
await page.addInitScript((css) => {
  const style = document.createElement("style");
  style.setAttribute("data-solarsage-hide-dev-overlay", "true");
  style.textContent = css;
  document.documentElement.appendChild(style);
}, overlayCss);

await page.goto("http://127.0.0.1:3001/<route>", { waitUntil: "networkidle" });
await page.addStyleTag({ content: overlayCss });
await page.waitForTimeout(2500);
await page.screenshot({
  path: "docs/superpowers/specs/assets/2026-07-07-mock-preview/<name>.png",
  fullPage: false,
});
```

The overlay CSS targeted only Next.js development UI hosts/selectors such as `nextjs-portal`, `next-route-announcer`, `[data-nextjs-dev-tools-button]`, and `[data-nextjs-toast]`. Product UI selectors and source files were not changed.

## Captured Routes

| Route | HTTP result | Artifact |
| --- | --- | --- |
| `/day/2026-07-05` | `200 text/html` | `assets/2026-07-07-mock-preview/day-2026-07-05.png` |
| `/calendar` | `200 text/html` | `assets/2026-07-07-mock-preview/calendar.png` |
| `/profile` | `200 text/html` | `assets/2026-07-07-mock-preview/profile.png` |
| `/readings` | `200 text/html` | `assets/2026-07-07-mock-preview/readings.png` |
| `/readings/natal` | `200 text/html` | `assets/2026-07-07-mock-preview/readings-natal.png` |
| `/readings/horary` | `200 text/html` | `assets/2026-07-07-mock-preview/readings-horary.png` |

## Gaps And Notes

- No route-open gaps were observed during preflight; all six required routes returned `200`.
- The captured calendar oracle shows right-edge horizontal overflow on the mobile viewport. Treat this as a property of the old oracle, not as a requirement to reproduce overflow.
- The screenshots contain mock-preview demo state such as guest profile, subscription/trial copy, natal badges, and sample location text. Use them for visual composition only. Do not treat their facts, access state, dates, counters, payments, chart data, or astrology text as production truth.
- Next.js dev-only overlay UI was excluded from the PNG oracle. The black circular Next dev indicator is not product UI and must not be used as a visual baseline element.
- The screenshots were visually checked for obvious secrets. They do not show Telegram initData, cookies, bot tokens, or raw API credentials.

## How The Future Agent Should Use This

Use these artifacts as a visual comparison aid while migrating presentation into `main`:

1. Open the screenshots beside the current `main` route.
2. Port only presentation patterns after the corresponding real backend/frontend contract exists.
3. Preserve the public DOM contract from `AGENTS.md`: stable `data-testid`, `data-state`, `data-status`, accessible roles, and ARIA state.
4. Add mock visual e2e under `e2e/mock-visual/` using Playwright route interception and contract-valid fixtures.
5. Keep real e2e on Telegram HMAC and the real API. Mock visual e2e does not prove auth, backend, sidecar, cache, nginx, or systemd behavior.

Do not:

- Port `/opt/solarsage-astro-mock-preview/app/api/[...path]/route.ts`.
- Add MSW or a runtime mock mode.
- Import `lib/mocks/*`, `lib/demo-data.ts`, or mock-preview data into product paths.
- Change systemd, nginx, bot config, port `3002`, or FastAPI port `8000` as part of UI migration.

## External Agent Clean-Clone Handoff

From a clean git clone, first install repository dependencies:

```bash
pnpm install
pnpm exec playwright install --with-deps
```

For frontend-only development and unit checks, a local dev server may run on `3000`:

```bash
pnpm dev
```

For backend test dependencies:

```bash
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Real local API/frontend runtime needs environment values supplied out of band. Never commit `.env`, Telegram initData, bot tokens, cookies, API keys, or production database credentials. On the canonical server, use the existing systemd services instead of manual `uvicorn`. In an external clone, use an isolated local equivalent only after confirming ports and env with the current repo docs.

Recommended gates for migration work:

```bash
git diff --check
pnpm exec tsc --noEmit --pretty false
npx vitest run
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
E2E_BASE_URL=http://localhost:3002 pnpm exec playwright test --project=chromium
```

Mock visual e2e should stay explicit until it is intentionally added to the default suite:

```bash
E2E_BASE_URL=http://localhost:3002 pnpm exec playwright test e2e/mock-visual --project=mobile
```

At preflight time, `python3 scripts/check_docs_manifest.py` failed with a pre-existing `SyntaxError` in `scripts/check_docs_manifest.py`. This task did not repair that guard script.
