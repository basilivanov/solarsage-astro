# Mock Visual E2E Harness

This directory is a test-only staging area for future mock visual e2e coverage. It intentionally contains no `*.spec.ts` file yet, so the default Playwright suite does not gain a failing migration test during preflight.

## Rules

- Use Playwright `page.route("**/api/**", ...)` for API interception.
- Keep fixtures contract-valid and stored under `e2e/mock-visual/fixtures/`.
- Keep screenshots and parity expectations tied to stable `data-testid`, `data-state`, `data-status`, roles, and ARIA state.
- Do not add MSW.
- Do not import `lib/mocks/*`, `lib/demo-data.ts`, or mock-preview modules into product paths.
- Do not route unmatched mock visual API calls to production by default; fail fast so fixture gaps are visible.

## Reference Artifacts

The portable visual oracle lives in:

```text
docs/superpowers/specs/assets/2026-07-07-mock-preview/
```

The hand-off note is:

```text
docs/superpowers/specs/2026-07-07-mock-preview-reference.md
```

## Future Test Shape

After a route is migrated onto real contracts, add a dedicated spec in this directory and install route fixtures before navigation:

```ts
import { expect, test } from "@playwright/test";
import { installMockApiRoutes } from "./route-interception";
import { dayFixture } from "./fixtures/day-2026-07-05";

test("day route matches the visual contract", async ({ page }) => {
  await installMockApiRoutes(page, {
    "/api/day/2026-07-05": { body: dayFixture },
  });

  await page.goto("/day/2026-07-05");
  await expect(page.getByTestId("today-screen")).toHaveAttribute("data-state", "ready");
});
```

Run mock visual specs explicitly until the migration has a stable project/script:

```bash
E2E_BASE_URL=http://localhost:3002 pnpm exec playwright test e2e/mock-visual --project=mobile
```
