// ############################################################################
// AI_HEADER: E2E_MOCK_VISUAL_SCREENSHOT — deterministic screenshot prep
// ROLE: Shared deterministic preparation for visual baselines in mock-visual.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-SCREENSHOT
// purpose: Make Playwright screenshots deterministic for visual baselines:
//   kill animations/transitions, hide the caret, and wait for webfonts.
// owns:
//   - e2e/mock-visual/screenshot.ts
// inputs: Playwright Page.
// outputs: resolved promise when the page is screenshot-stable.
// dependencies: @playwright/test.
// side_effects: injects one <style> tag into the tested page (test-only).
// emitted_logs: none.
// invariants:
//   - never masks or hides real UI content; only animation/caret noise and
//     the test-preview framework chrome (Next.js dev overlay/portal/toast/
//     build-watcher) are suppressed — the same selectors the day-v2 suite
//     already uses in hideNextOverlay.
// failure_policy: errors propagate to the calling test.
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-SCREENSHOT

// START_MODULE_MAP: M-E2E-MOCK-VISUAL-SCREENSHOT
// public_entrypoints:
//   - prepareForScreenshot
// semantic_blocks:
//   - SCREENSHOT_PREP: deterministic style injection + font readiness
// owned_tests:
//   - e2e/mock-visual/*.spec.ts
// END_MODULE_MAP: M-E2E-MOCK-VISUAL-SCREENSHOT

import type { Page } from "@playwright/test"

// START_BLOCK: SCREENSHOT_PREP
export async function prepareForScreenshot(page: Page): Promise<void> {
  // START_FUNCTION_CONTRACT: F-M-E2E-MOCK-VISUAL-SCREENSHOT.prepareForScreenshot
  // purpose: Make the current page deterministic for visual baseline
  //   screenshots: suppress animations/transitions, the text caret, and the
  //   test-preview framework chrome (Next.js dev overlay/portal/toast/
  //   build-watcher — the exact selectors hideNextOverlay uses), then wait
  //   for webfonts to finish loading.
  // inputs: page — Playwright Page under test.
  // returns: resolved when the page is screenshot-stable (void).
  // side_effects: injects one <style> tag into the tested page (test-only;
  //   real UI content is never hidden, only the framework dev chrome).
  // emitted_logs: none.
  // error_behavior: any page.evaluate/addStyleTag error propagates to the
  //   calling test and fails it.
  // END_FUNCTION_CONTRACT: F-M-E2E-MOCK-VISUAL-SCREENSHOT.prepareForScreenshot
  await page.addStyleTag({
    content: `
      nextjs-portal,
      [data-nextjs-dialog-overlay],
      #__next-build-watcher,
      [data-nextjs-toast],
      [data-next-mark-loading] {
        display: none !important;
      }
      *, *::before, *::after {
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
        caret-color: transparent !important;
      }
    `,
  })
  await page.evaluate(() => document.fonts.ready)
}
// END_BLOCK: SCREENSHOT_PREP
