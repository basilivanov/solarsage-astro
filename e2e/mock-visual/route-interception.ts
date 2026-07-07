// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_ROUTE_INTERCEPTION - Playwright-only API route fixtures for mock visual e2e.
// ROLE: Provides a fail-fast page.route helper for visual parity tests without adding runtime mocks to product code.
//       Includes a missing-request recorder so tests can assert no unmocked API calls were made.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-ROUTES
// purpose: Install test-only Playwright API route interception for mock visual e2e specs.
//          Tracks unmatched API calls so tests can assert no missing fixtures.
// owns:
//   - e2e/mock-visual/route-interception.ts
// inputs: Playwright Page, route fixture map, optional route pattern/strict mode.
// outputs: Registered Playwright route handlers + a record of unmatched API paths.
// dependencies: @playwright/test types only.
// side_effects: Registers page.route handlers in the current Playwright test page.
// emitted_logs: none.
// invariants:
//   - Product code never imports this module.
//   - API mocking stays inside Playwright tests.
//   - Unmatched API calls fail fast by default and are recorded.
// failure_policy: Fulfills unmatched strict-mode API requests with HTTP 501 JSON.
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-ROUTES

// START_MODULE_MAP: M-E2E-MOCK-VISUAL-ROUTES
// public_entrypoints:
//   - installMockApiRoutes
//   - MissingRequestsTracker
// semantic_blocks:
//   - TYPES: test fixture shape for route interception.
//   - MISSING_TRACKER: missing-request recorder.
//   - ROUTE_INSTALLATION: Playwright page.route registration.
// owned_tests:
//   - e2e/mock-visual/*.spec.ts
// END_MODULE_MAP: M-E2E-MOCK-VISUAL-ROUTES

import { expect, type Page, type Request } from "@playwright/test";

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

// START_BLOCK: MISSING_TRACKER
/**
 * Tracks missing (unmatched) API requests during a mock visual test.
 * After navigation, assert `missingRequests.length === 0` to ensure
 * all API calls made by the page have fixture coverage.
 */
export class MissingRequestsTracker {
  readonly missing: string[] = [];

  add(path: string): void {
    this.missing.push(path);
  }

  get all(): readonly string[] {
    return this.missing;
  }

  get count(): number {
    return this.missing.length;
  }

  reset(): void {
    this.missing.length = 0;
  }
}
// END_BLOCK: MISSING_TRACKER

/**
 * Assert no missing API fixtures after waiting for late React effects.
 * Use at the end of each mock visual test, after all screen assertions.
 */
export async function expectNoMissingApiFixtures(
  page: Page,
  tracker: MissingRequestsTracker,
): Promise<void> {
  await page.waitForTimeout(800);
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(300);
  expect(tracker.all).toEqual([]);
}

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
): Promise<MissingRequestsTracker> {
  // START_FUNCTION_CONTRACT: F-M-E2E-MOCK-VISUAL-ROUTES.installMockApiRoutes
  // purpose: Register Playwright route interception for mocked API responses in visual e2e tests.
  // inputs: page - Playwright Page; fixtures - exact API pathname map; options - route pattern and strict-mode override.
  // returns: Promise<MissingRequestsTracker> — a tracker of unmatched API paths for test assertions.
  // side_effects: Adds a route handler to the provided Playwright page.
  // emitted_logs: none.
  // error_behavior: In strict mode, unmatched API requests receive HTTP 501 instead of reaching the real backend.
  //                 All unmatched requests are recorded in the returned tracker.
  // END_FUNCTION_CONTRACT: F-M-E2E-MOCK-VISUAL-ROUTES.installMockApiRoutes
  const routePattern = options.routePattern ?? "**/api/**";
  const strict = options.strict ?? true;
  const tracker = new MissingRequestsTracker();

  await page.route(routePattern, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    const search = new URL(request.url()).search;
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

    // Record missing fixture for test assertion
    const urlKey = pathname + search;
    tracker.add(urlKey);

    return route.fulfill({
      status: 501,
      contentType: "application/json",
      body: JSON.stringify({
        error: "missing_mock_visual_fixture",
        path: pathname,
        search: search,
      }),
    });
  });

  return tracker;
}
// END_BLOCK: ROUTE_INSTALLATION
