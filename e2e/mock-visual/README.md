# Mock Visual E2E Harness + V2 Personal Day Preview

> **TEST-ONLY.** This directory is a visual/test harness. It must never be imported by product runtime paths (`app/`, `components/`, `lib/api`, etc.). Production does not depend on these fixtures.

## One-command V2 personal day preview

Start mock API + Next dev:

```bash
pnpm preview:v2
```

This will:

1. Fail fast if ports `18092` or `3003` are already occupied
2. Start a test-only Node mock API on `127.0.0.1:18092`
3. Start Next on `0.0.0.0:3003` with:
   - `NEXT_DIST_DIR=.next-v2-preview`
   - `DEV_API_REWRITE_BASE_URL=http://127.0.0.1:18092` (ignored when `NODE_ENV=production`)
4. Print: `http://127.0.0.1:3003/day/2026-07-08`
5. On `SIGINT` / `SIGTERM`, terminate both processes

Stop with `Ctrl+C` in the preview terminal.

### Mock API rules

- Serves rich V2 day payload for `/api/day/2026-07-08`
- Serves minimal day bodies for week neighbours `2026-07-05` … `2026-07-11`
- Serves test-shaped `/api/calendar`, `/api/auth/dev`, `/api/profile`, `/api/referral`, `/api/_log`
- Unknown `/api/*` → HTTP `501` JSON `{ "detail": "missing_mock_visual_fixture" }`
- **Never** falls through to the production API on port `8000`

## Playwright mock visual

Use Playwright `page.route("**/api/**", ...)` for API interception in specs.

```bash
E2E_BASE_URL=http://127.0.0.1:3003 pnpm exec playwright test e2e/mock-visual/day-v2.spec.ts --project=mobile
```

## Rules

- Keep fixtures contract-valid under `e2e/mock-visual/fixtures/`
- Do not add MSW
- Do not import `lib/mocks/*`, `lib/demo-data.ts`, or mock-preview modules into product paths
- Do not route unmatched mock visual API calls to production
