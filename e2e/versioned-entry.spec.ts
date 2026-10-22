// ############################################################################
// AI_HEADER: MODULE_E2E_VERSIONED_ENTRY
// ROLE: Versioned document entry e2e — proves middleware preserves Telegram
//       initData in the URL hash across the 307, guards against redirect loops,
//       and never redirects internal RSC navigation.
// DEPENDENCIES: @playwright/test, __tests__/fixtures/today_convergence_v2
// GRACE_ANCHORS: [VERSIONED_ENTRY_E2E, HASH_GATE, LOOP_GUARD, RSC_PASSTHROUGH]
// WAVE: W-CACHE-DELIVERY-HARDENING
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-VERSIONED-ENTRY
// purpose: Prove the release-versioned entry contract through a real Chromium
//   document navigation: one 307 with no-store, intact #tgWebAppData, one auth
//   POST carrying the hash initData, a loop-guarded already-versioned URL, and
//   unredirected client-side RSC navigation.
// owns:
//   - e2e/versioned-entry.spec.ts
// inputs: E2E_BASE_URL dev server started with NEXT_PUBLIC_RELEASE_SHA=e2e-test-sha
// outputs: Playwright pass/fail assertions
// dependencies:
//   - @playwright/test
//   - M-TODAY-CONVERGENCE fixture barrel (quietSteady, test-only)
// side_effects:
//   - registers test-only page.route API fixtures (no product runtime mocks)
//   - seeds localStorage lumen:onboarded
// emitted_logs: none
// invariants:
//   - assertions use only data-testid / data-* public DOM contract
//   - every /api/** request is intercepted; an unmocked path is a test failure
//   - the test server runs with a known non-unknown release sha
// failure_policy: fail on missing redirect, lost fragment, unexpected redirect,
//   unexpected API call or missing ready screen.
// END_MODULE_CONTRACT: M-E2E-VERSIONED-ENTRY

// START_MODULE_MAP: M-E2E-VERSIONED-ENTRY
// public_entrypoints:
//   - document entry with hash
//   - already-versioned loop guard
//   - client-side RSC navigation
// semantic_blocks:
//   - API_MOCKS: strict test-only /api/** fixture layer
//   - NAVIGATION_REDIRECTS: one-shot 307 observation
//   - HASH_ENTRY: document URL with #tgWebAppData
//   - LOOP_GUARD: current ?v is passed through
//   - RSC_PASSTHROUGH: client-side route transition stays 200
// owned_tests:
//   - self
// END_MODULE_MAP: M-E2E-VERSIONED-ENTRY

import { test, expect, type Page, type Request } from '@playwright/test';

import { quietSteady } from '../__tests__/fixtures/today_convergence_v2';

const VERSION_SHA = 'e2e-test-sha';
const AUTH_OK = { userId: 4242, expiresAt: '2099-01-01T00:00:00Z', isNewUser: true };
const INIT_DATA = 'auth_date=1730000000&hash=e2e_versioned_entry_hash&user=%7B%22id%22%3A4242%7D';

type AuthReply = { status: number; body: unknown };
type AuthHandler = (request: Request, callNumber: number) => Promise<AuthReply>;

interface MockState {
  authCalls: Array<{ body: Record<string, unknown> }>;
  devCalls: number;
  unmatched: string[];
}

// START_BLOCK: API_MOCKS
async function installApiMocks(page: Page, authHandler: AuthHandler = async () => ({
  status: 200,
  body: AUTH_OK,
})): Promise<MockState> {
  const state: MockState = { authCalls: [], devCalls: 0, unmatched: [] };

  const fixtures: Record<string, unknown> = {
    '/api/health': { release_sha: VERSION_SHA },
    '/api/day/today': quietSteady,
    '/api/profile': { isOnboarded: true },
    '/api/access': {
      user: 'trial',
      referralDaysLeft: 0,
      subscriptionActive: false,
      accessStart: '2026-01-01',
      accessUntil: '2026-12-31',
    },
    '/api/calendar': {},
    '/api/referral': {},
    '/api/payment/products': { products: [] },
  };
  if (quietSteady.snapshotId) {
    fixtures[`/api/day/snapshots/${quietSteady.snapshotId}/impression`] = { ok: true };
  }

  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;

    if (pathname === '/api/auth/telegram') {
      const body = (request.postDataJSON() ?? {}) as Record<string, unknown>;
      state.authCalls.push({ body });
      const reply = await authHandler(request, state.authCalls.length);
      return route.fulfill({
        status: reply.status,
        contentType: 'application/json',
        body: JSON.stringify(reply.body),
      });
    }

    if (pathname === '/api/auth/dev') {
      state.devCalls += 1;
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(AUTH_OK),
      });
    }

    if (pathname === '/api/_log') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true }),
      });
    }

    if (pathname === '/api/day/today' || /^\/api\/day\/\d{4}-\d{2}-\d{2}$/.test(pathname)) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(quietSteady),
      });
    }

    if (pathname in fixtures) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(fixtures[pathname]),
      });
    }

    state.unmatched.push(pathname);
    return route.fulfill({
      status: 501,
      contentType: 'application/json',
      body: JSON.stringify({ error: 'unmocked_api_route', path: pathname }),
    });
  });

  return state;
}
// END_BLOCK: API_MOCKS

// START_BLOCK: HASH_ENTRY
function telegramHash(): string {
  return new URLSearchParams({ tgWebAppData: INIT_DATA }).toString();
}

async function seedOnboarded(page: Page): Promise<void> {
  await page.addInitScript(() => {
    localStorage.setItem('lumen:onboarded', '1');
  });
}
// END_BLOCK: HASH_ENTRY

// START_BLOCK: NAVIGATION_REDIRECTS
interface RedirectRecord {
  status: number;
  url: string;
  location: string | undefined;
  cacheControl: string | undefined;
}

function observeNavigationRedirects(page: Page): RedirectRecord[] {
  const redirects: RedirectRecord[] = [];
  page.on('response', (response) => {
    if (!response.request().isNavigationRequest()) return;
    if (![301, 302, 303, 307, 308].includes(response.status())) return;
    redirects.push({
      status: response.status(),
      url: response.url(),
      location: response.headers()['location'],
      cacheControl: response.headers()['cache-control'],
    });
  });
  return redirects;
}
// END_BLOCK: NAVIGATION_REDIRECTS

test.describe('Versioned entry', () => {
  test.setTimeout(60_000);

  test('document entry with #tgWebAppData carries initData through one no-store 307', async ({ page }) => {
    await seedOnboarded(page);
    const state = await installApiMocks(page);
    const redirects = observeNavigationRedirects(page);
    const hash = telegramHash();

    const response = await page.goto(`/day/today#${hash}`, { waitUntil: 'domcontentloaded' });

    await expect(page.getByTestId('today-screen')).toHaveAttribute('data-screen-state', 'ready', {
      timeout: 15_000,
    });

    const finalUrl = new URL(page.url());
    expect(response?.status()).toBe(200);
    expect(finalUrl.searchParams.get('v')).toBe(VERSION_SHA);
    expect(finalUrl.hash).toBe(`#${hash}`);

    // The browser must carry the fragment across the 307 and the middleware
    // must emit exactly one redirect, not a chain.
    expect(redirects).toHaveLength(1);
    expect(redirects[0].status).toBe(307);
    expect(redirects[0].cacheControl).toBe('no-store');
    expect(redirects[0].location).toBeDefined();
    expect(new URL(redirects[0].location!, 'http://localhost').searchParams.get('v')).toBe(VERSION_SHA);

    expect(state.authCalls).toHaveLength(1);
    expect(state.authCalls[0].body.initData).toBe(INIT_DATA);
    expect(state.devCalls).toBe(0);
    expect(state.unmatched).toEqual([]);
  });

  test('already-versioned document entry is a loop-guarded no-op', async ({ page }) => {
    await seedOnboarded(page);
    const state = await installApiMocks(page);
    const redirects = observeNavigationRedirects(page);
    const hash = telegramHash();

    const response = await page.goto(`/day/today?v=${VERSION_SHA}#${hash}`, {
      waitUntil: 'domcontentloaded',
    });

    await expect(page.getByTestId('today-screen')).toHaveAttribute('data-screen-state', 'ready', {
      timeout: 15_000,
    });

    const finalUrl = new URL(page.url());
    expect(response?.status()).toBe(200);
    expect(redirects).toHaveLength(0);
    expect(finalUrl.searchParams.get('v')).toBe(VERSION_SHA);
    expect(finalUrl.hash).toBe(`#${hash}`);
    expect(state.authCalls).toHaveLength(1);
    expect(state.devCalls).toBe(0);
    expect(state.unmatched).toEqual([]);
  });

  test('client-side RSC navigation reaches /day/<date> without a redirect', async ({ page }) => {
    await seedOnboarded(page);
    const state = await installApiMocks(page);
    const hash = telegramHash();

    await page.goto(`/day/today#${hash}`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('today-screen')).toHaveAttribute('data-screen-state', 'ready', {
      timeout: 15_000,
    });

    const rscResponsePromise = page.waitForResponse((response) => {
      const requestHeaders = response.request().headers();
      const isRsc = requestHeaders['rsc'] === '1'
        || requestHeaders['next-router-state-tree'] !== undefined
        || requestHeaders['next-router-prefetch'] !== undefined;
      return isRsc && new URL(response.url()).pathname.startsWith('/day/');
    });

    await page.getByRole('button', { name: 'Следующий день' }).click();
    const rscResponse = await rscResponsePromise;

    expect(rscResponse.status()).toBe(200);
    expect(rscResponse.headers()['location']).toBeUndefined();
    await expect.poll(() => new URL(page.url()).pathname).toMatch(/^\/day\/\d{4}-\d{2}-\d{2}$/);

    expect(state.devCalls).toBe(0);
    expect(state.unmatched).toEqual([]);
  });
});
