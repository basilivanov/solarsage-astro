// ############################################################################
// AI_HEADER: MODULE_E2E_HYDRATION_GUARD
// ROLE: E2E hydration guard — fails on React hydration console errors
// DEPENDENCIES: @playwright/test
// GRACE_ANCHORS: [E2E_HYDRATION_GUARD]
// ############################################################################
//
// This spec verifies that the application does NOT produce React hydration
// mismatch errors when rendering the day detail page.
//
// Hydration mismatches happen when server-rendered HTML differs from the
// first client-side render. Before this change the Telegram SDK was loaded
// via <Script strategy="beforeInteractive">, making window.Telegram
// available synchronously during hydration — causing a mismatch with SSR
// (where window.Telegram is always undefined).
//
// The fix moves Telegram SDK loading to a client-only provider that runs
// inside useEffect, so the first client render always matches SSR.
//
// If this test fails with `Expected 0 hydration errors, got N`, it means
// React detected a mismatch — the markup rendered on the server differs
// from the first client-side render.

import { test, expect } from '@playwright/test';

test.describe('Hydration Guard', () => {
  test('no React hydration errors on /day/2026-07-05', async ({ page }) => {
    test.setTimeout(30000);

    // ---- Collect hydration-related console errors ----
    const hydrationErrors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text();
        // React hydration errors use well-known message patterns
        if (
          /hydrat|did not match|Expected server HTML|Text content does not match/i.test(text)
        ) {
          hydrationErrors.push(text);
        }
      }
    });

    page.on('pageerror', (err) => {
      if (/hydrat|did not match|Expected server HTML/i.test(err.message)) {
        hydrationErrors.push(err.message);
      }
    });

    // ---- Provide Telegram stub for deterministic rendering ----
    // We deliberately set initData to empty so useTelegramAuth takes the
    // "not in Telegram" path and does NOT fire a real /api/auth/telegram
    // call.  The page will render the GraceLayout without auth, and the
    // day page will show its loading / error state — all without causing
    // hydration errors.
    await page.addInitScript(() => {
      (window as any).Telegram = {
        WebApp: {
          initData: '',                 // empty → no Telegram auth triggered
          initDataUnsafe: {},
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
            text: '', color: '', textColor: '', isVisible: false, isActive: true,
            isProgressVisible: false, setText: () => {}, onClick: () => {},
            offClick: () => {}, show: () => {}, hide: () => {},
            enable: () => {}, disable: () => {}, showProgress: () => {},
            hideProgress: () => {},
          },
          BackButton: {
            isVisible: false, onClick: () => {}, offClick: () => {},
            show: () => {}, hide: () => {},
          },
          HapticFeedback: {
            impactOccurred: () => {}, notificationOccurred: () => {},
            selectionChanged: () => {},
          },
          onEvent: () => {}, offEvent: () => {}, sendData: () => {},
          switchInlineQuery: () => {}, openLink: () => {},
          openTelegramLink: () => {}, openInvoice: () => {},
          showPopup: () => {}, showAlert: () => {}, showConfirm: () => {},
        },
      };

      // Mark as onboarded so the page tries to render content
      localStorage.setItem('lumen:onboarded', '1');
    });

    // ---- Navigate directly to the day page ----
    await page.goto('/day/2026-07-05', { waitUntil: 'networkidle' });

    // Give React time to hydrate fully
    await page.waitForTimeout(3000);

    // ---- Fail if any hydration errors occurred ----
    if (hydrationErrors.length > 0) {
      console.log('Hydration errors detected:', JSON.stringify(hydrationErrors, null, 2));
    }

    expect(
      hydrationErrors,
      `Expected 0 hydration errors, got ${hydrationErrors.length}. This means server-rendered HTML differs from the first client render — check the Telegram provider and client-only guarding.`,
    ).toHaveLength(0);
  });
});
