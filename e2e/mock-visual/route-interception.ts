// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_ROUTE_INTERCEPTION - Playwright-only API route fixtures for mock visual e2e.
// ROLE: Provides a fail-fast page.route helper for future visual parity tests without adding runtime mocks to product code.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-ROUTES
// purpose: Install test-only Playwright API route interception for future mock visual e2e specs.
// owns:
//   - e2e/mock-visual/route-interception.ts
// inputs: Playwright Page, route fixture map, optional route pattern/strict mode.
// outputs: Registered Playwright route handlers for the calling test page.
// dependencies: @playwright/test types only.
// side_effects: Registers page.route handlers in the current Playwright test page.
// emitted_logs: none.
// invariants:
//   - Product code never imports this module.
//   - API mocking stays inside Playwright tests.
//   - Unmatched API calls fail fast by default.
// failure_policy: Fulfills unmatched strict-mode API requests with HTTP 501 JSON.
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-ROUTES

// START_MODULE_MAP: M-E2E-MOCK-VISUAL-ROUTES
// public_entrypoints:
//   - installMockApiRoutes
// semantic_blocks:
//   - TYPES: test fixture shape for route interception.
//   - ROUTE_INSTALLATION: Playwright page.route registration.
// owned_tests:
//   - future e2e/mock-visual/*.spec.ts
// END_MODULE_MAP: M-E2E-MOCK-VISUAL-ROUTES

import type { Page, Request } from "@playwright/test";

// START_BLOCK: TYPES
export type MockApiRouteFixture = {
  status?: number;
  contentType?: string;
  headers?: Record<string, string>;
  body?: unknown;
  text?: string;
};

export type MockApiRouteFixtureFactory = (
  request: Request,
) => MockApiRouteFixture | Promise<MockApiRouteFixture>;

export type MockApiRouteFixtures = Record<
  string,
  MockApiRouteFixture | MockApiRouteFixtureFactory
>;

export type MockApiRouteOptions = {
  routePattern?: string;
  strict?: boolean;
};
// END_BLOCK: TYPES

function serializeFixture(fixture: MockApiRouteFixture): {
  status: number;
  contentType: string;
  body: string;
  headers?: Record<string, string>;
} {
  const contentType = fixture.contentType ?? "application/json";
  const body = fixture.text ?? JSON.stringify(fixture.body ?? {});

  return {
    status: fixture.status ?? 200,
    contentType,
    body,
    headers: fixture.headers,
  };
}

// START_BLOCK: ROUTE_INSTALLATION
export async function installMockApiRoutes(
  page: Page,
  fixtures: MockApiRouteFixtures,
  options: MockApiRouteOptions = {},
): Promise<void> {
  // START_FUNCTION_CONTRACT: F-M-E2E-MOCK-VISUAL-ROUTES.installMockApiRoutes
  // purpose: Register Playwright route interception for mocked API responses in visual e2e tests.
  // inputs: page - Playwright Page; fixtures - exact API pathname map; options - route pattern and strict-mode override.
  // returns: Promise<void> after route handler registration.
  // side_effects: Adds a route handler to the provided Playwright page.
  // emitted_logs: none.
  // error_behavior: In strict mode, unmatched API requests receive HTTP 501 instead of reaching the real backend.
  // END_FUNCTION_CONTRACT: F-M-E2E-MOCK-VISUAL-ROUTES.installMockApiRoutes
  const routePattern = options.routePattern ?? "**/api/**";
  const strict = options.strict ?? true;

  await page.route(routePattern, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    const fixtureOrFactory = fixtures[pathname];

    if (fixtureOrFactory) {
      const fixture =
        typeof fixtureOrFactory === "function"
          ? await fixtureOrFactory(request)
          : fixtureOrFactory;

      return route.fulfill(serializeFixture(fixture));
    }

    if (!strict) {
      return route.fallback();
    }

    return route.fulfill({
      status: 501,
      contentType: "application/json",
      body: JSON.stringify({
        error: "missing_mock_visual_fixture",
        path: pathname,
      }),
    });
  });
}
// END_BLOCK: ROUTE_INSTALLATION
