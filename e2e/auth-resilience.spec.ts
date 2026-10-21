// ############################################################################
// AI_HEADER: MODULE_E2E_AUTH_RESILIENCE
// ROLE: Auth resilience e2e — slow auth, blocked telegram.org, backend error + retry.
// DEPENDENCIES: @playwright/test, __tests__/fixtures/today_convergence_v2
// GRACE_ANCHORS: [AUTH_RESILIENCE]
// WAVE: W-AUTH-TIMEOUT-RACE-FIX
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-AUTH-RESILIENCE
// purpose: Prove three auth-resilience scenarios strictly through the public DOM
//   contract (auth-loading/auth-error/auth-retry/today-screen):
//   1. a 4.5 s auth response stays inside the 12 s budget and reaches content;
//   2. blocking https://telegram.org/** does not break login via the self-hosted
//      /telegram-web-app.js SDK;
//   3. a 500 auth response exposes auth-error + auth-retry, and retry reaches content.
// owns:
//   - e2e/auth-resilience.spec.ts
// inputs: E2E_BASE_URL dev server, page.route API fixtures, addInitScript Telegram stub.
// outputs: Playwright pass/fail assertions.
// dependencies:
//   - @playwright/test
//   - M-TODAY-CONVERGENCE fixture barrel (quietSteady day payload, test-only)
// side_effects:
//   - registers test-only page.route handlers (no product runtime mocks)
//   - sets localStorage lumen:onboarded in the browser context
// emitted_logs: none
// invariants:
//   - every API call is intercepted; an unmocked API path is a test failure (501 + recorder)
//   - assertions use only data-testid / data-* public contract, never CSS classes or LLM copy
//   - at every settled checkpoint exactly one of auth-loading | auth-error | today-screen is visible
//   - no product/runtime file is imported for mocking
// failure_policy: fail on timeout, empty window, unexpected API call or leaked auth surface
// END_MODULE_CONTRACT: M-E2E-AUTH-RESILIENCE

// START_MODULE_MAP: M-E2E-AUTH-RESILIENCE
// public_entrypoints:
//   - slow auth scenario
//   - blocked telegram.org scenario
//   - backend 500 + retry scenario
// semantic_blocks:
//   - TELEGRAM_STUB: window.Telegram.WebApp injection (no real SDK)
//   - API_MOCKS: strict page.route fixture layer
//   - AUTH_SURFACE: exactly-one-visible public auth/content contract
//   - SLOW_AUTH: 4.5 s response inside the 12 s budget
//   - BLOCKED_TELEGRAM: self-hosted SDK with telegram.org aborted
//   - ERROR_RETRY: 500 -> auth-error -> retry -> content
// owned_tests:
//   - self
// END_MODULE_MAP: M-E2E-AUTH-RESILIENCE

import { test, expect, type Page, type Request } from '@playwright/test';

import { quietSteady } from '../__tests__/fixtures/today_convergence_v2';

const AUTH_OK = { userId: 4242, expiresAt: '2099-01-01T00:00:00Z', isNewUser: true };

/** Fake initData accepted by every page.route mock; the backend never sees it. */
const INIT_DATA = 'auth_date=1730000000&hash=e2e_auth_resilience_hash&user=%7B%22id%22%3A4242%7D';

// START_BLOCK: TELEGRAM_STUB
/**
 * Inject the Telegram WebApp global before any app script runs (same shape as
 * e2e/fixtures.ts). The provider detects it and skips the SDK script load.
 */
async function installTelegramStub(page: Page, initData: string): Promise<void> {
  await page.addInitScript((data: string) => {
    localStorage.setItem('lumen:onboarded', '1');
    (window as any).Telegram = {
      WebApp: {
        initData: data,
        initDataUnsafe: { user: { id: 4242 } },
        ready: () => {},
        expand: () => {},
        close: () => {},
        platform: 'web',
        version: '9.5',
        colorScheme: 'light',
        themeParams: {},
        isExpanded: true,
        viewportHeight: 812,
        viewportStableHeight: 812,
        headerColor: '#ffffff',
        backgroundColor: '#ffffff',
        MainButton: {
          text: '',
          color: '',
          textColor: '',
          isVisible: false,
          isActive: true,
          isProgressVisible: false,
          setText: () => {},
          onClick: () => {},
          offClick: () => {},
          show: () => {},
          hide: () => {},
          enable: () => {},
          disable: () => {},
          showProgress: () => {},
          hideProgress: () => {},
        },
        BackButton: {
          isVisible: false,
          onClick: () => {},
          offClick: () => {},
          show: () => {},
          hide: () => {},
        },
        HapticFeedback: {
          impactOccurred: () => {},
          notificationOccurred: () => {},
          selectionChanged: () => {},
        },
        onEvent: () => {},
        offEvent: () => {},
        sendData: () => {},
        switchInlineQuery: () => {},
        openLink: () => {},
        openTelegramLink: () => {},
        openInvoice: () => {},
        showPopup: () => {},
        showAlert: () => {},
        showConfirm: () => {},
      },
    };
  }, initData);
}
// END_BLOCK: TELEGRAM_STUB

// START_BLOCK: API_MOCKS
type AuthReply = { status: number; body: unknown };
type AuthHandler = (request: Request, callNumber: number) => Promise<AuthReply>;

interface MockState {
  authCalls: Array<{ body: Record<string, unknown> }>;
  unmatched: string[];
}

/**
 * Strict test-only API layer: every /api/** request is fulfilled locally.
 * An unknown path is recorded and answered with 501 so the test fails closed.
 */
async function installApiMocks(page: Page, authHandler: AuthHandler): Promise<MockState> {
  const state: MockState = { authCalls: [], unmatched: [] };

  const fixtures: Record<string, unknown> = {
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

    // Frontend log shipping is not part of this contract.
    if (pathname === '/api/_log') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true }),
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

// START_BLOCK: AUTH_SURFACE
type AuthSurface = 'loading' | 'error' | 'content';

async function visibleAuthSurfaces(page: Page): Promise<AuthSurface[]> {
  const [loading, error, content] = await Promise.all([
    page.getByTestId('auth-loading').first().isVisible(),
    page.getByTestId('auth-error').first().isVisible(),
    page.getByTestId('today-screen').first().isVisible(),
  ]);
  const visible: AuthSurface[] = [];
  if (loading) visible.push('loading');
  if (error) visible.push('error');
  if (content) visible.push('content');
  return visible;
}

/** No empty window and no overlap: exactly one public surface is visible. */
async function expectSingleAuthSurface(page: Page): Promise<AuthSurface> {
  let surface: AuthSurface | undefined;
  await expect
    .poll(
      async () => {
        const visible = await visibleAuthSurfaces(page);
        if (visible.length === 1) surface = visible[0];
        return visible.length;
      },
      { timeout: 15_000 },
    )
    .toBe(1);
  return surface as AuthSurface;
}
// END_BLOCK: AUTH_SURFACE

test.describe('Auth resilience', () => {
  test.setTimeout(60_000);

  test('slow auth: 4.5 s response stays inside the 12 s budget and reaches content', async ({ page }) => {
    await installTelegramStub(page, INIT_DATA);
    const state = await installApiMocks(page, async () => {
      await new Promise((resolve) => setTimeout(resolve, 4_500));
      return { status: 200, body: AUTH_OK };
    });

    await page.goto('/day/today', { waitUntil: 'domcontentloaded' });

    expect(await expectSingleAuthSurface(page)).toBe('loading');
    await expect(page.getByTestId('auth-loading')).toBeVisible();

    // Inside the 4.5 s window the app must stay in loading, never in auth-error.
    await page.waitForTimeout(3_000);
    expect(await expectSingleAuthSurface(page)).toBe('loading');
    await expect(page.getByTestId('auth-error')).toHaveCount(0);

    await expect(page.getByTestId('today-screen')).toHaveAttribute('data-screen-state', 'ready', {
      timeout: 15_000,
    });
    await expect(page.getByTestId('auth-loading')).toHaveCount(0);
    await expect(page.getByTestId('auth-error')).toHaveCount(0);
    expect(await expectSingleAuthSurface(page)).toBe('content');

    expect(state.authCalls).toHaveLength(1);
    expect(state.authCalls[0].body.initData).toBe(INIT_DATA);
    expect(state.unmatched).toEqual([]);
  });

  test('blocked telegram.org: self-hosted SDK still authenticates and renders content', async ({ page }) => {
    // No Telegram stub: the provider must load /telegram-web-app.js itself.
    // initData arrives through the #tgWebAppData hash, exactly like a real
    // Telegram webview URL.
    const hash = new URLSearchParams({ tgWebAppData: INIT_DATA }).toString();
    const requests: string[] = [];
    const scriptStatuses: number[] = [];
    page.on('request', (request) => requests.push(request.url()));
    page.on('response', (response) => {
      if (response.url().endsWith('/telegram-web-app.js')) scriptStatuses.push(response.status());
    });

    await page.route('https://telegram.org/**', (route) => route.abort('blockedbyclient'));
    const state = await installApiMocks(page, async () => ({ status: 200, body: AUTH_OK }));

    await page.goto(`/day/today#${hash}`, { waitUntil: 'domcontentloaded' });

    await expect(page.getByTestId('today-screen')).toHaveAttribute('data-screen-state', 'ready', {
      timeout: 15_000,
    });
    await expect(page.getByTestId('auth-loading')).toHaveCount(0);
    expect(await expectSingleAuthSurface(page)).toBe('content');

    // The auth went through the Telegram endpoint (not dev auth), with initData
    // resolved from the hash after the self-hosted SDK load.
    expect(state.authCalls).toHaveLength(1);
    expect(state.authCalls[0].body.initData).toBe(INIT_DATA);
    expect(state.unmatched).toEqual([]);

    // Prove the self-hosted script was the SDK source and telegram.org was
    // never contacted (a regression to the external CDN would fail here).
    expect(requests.some((url) => url.includes('/telegram-web-app.js'))).toBe(true);
    expect(scriptStatuses.length).toBeGreaterThan(0);
    expect(scriptStatuses.every((status) => status === 200)).toBe(true);
    expect(requests.some((url) => url.startsWith('https://telegram.org/'))).toBe(false);
  });

  test('backend 500: auth-error + auth-retry, then retry reaches content', async ({ page }) => {
    await installTelegramStub(page, INIT_DATA);
    const state = await installApiMocks(page, async (_request, callNumber) => {
      if (callNumber === 1) {
        return { status: 500, body: { detail: 'auth temporarily unavailable' } };
      }
      return { status: 200, body: AUTH_OK };
    });

    await page.goto('/day/today', { waitUntil: 'domcontentloaded' });

    await expect(page.getByTestId('auth-error')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId('auth-retry')).toBeVisible();
    await expect(page.getByTestId('auth-loading')).toHaveCount(0);
    expect(await expectSingleAuthSurface(page)).toBe('error');

    await page.getByTestId('auth-retry').click();

    // Retry re-enters loading with a fresh attempt.
    await expect(page.getByTestId('auth-loading')).toBeVisible();
    await expect(page.getByTestId('auth-error')).toHaveCount(0);

    await expect(page.getByTestId('today-screen')).toHaveAttribute('data-screen-state', 'ready', {
      timeout: 15_000,
    });
    await expect(page.getByTestId('auth-error')).toHaveCount(0);
    await expect(page.getByTestId('auth-loading')).toHaveCount(0);
    expect(await expectSingleAuthSurface(page)).toBe('content');

    expect(state.authCalls).toHaveLength(2);
    expect(state.authCalls[0].body.initData).toBe(INIT_DATA);
    expect(state.authCalls[1].body.initData).toBe(INIT_DATA);
    // One fresh authAttemptId per attempt (SLICE-04 correlation contract).
    expect(state.authCalls[0].body.authAttemptId).not.toBe(state.authCalls[1].body.authAttemptId);
    expect(state.unmatched).toEqual([]);
  });
});
