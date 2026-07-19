// AI_HEADER
// module: M-TEST-E2E-PROFILE-CITY-CHECKIN
// wave: W-TEST-3
// purpose: Real-API E2E (no route interception): profile "Где живу сейчас"
//   edit through the public CityPicker DOM contract, then the check-in
//   mood → energy → accuracy flow with a fresh-load read-back (P1-6 slice).

// START_MODULE_CONTRACT: M-TEST-E2E-PROFILE-CITY-CHECKIN
// purpose: Prove on the real stack that city suggestions work in the profile
//   edit sheet (production regression target) and that a check-in is saved
//   and read back from the real API.
// owns:
//   - e2e/profile-city-checkin.spec.ts
// inputs: real Telegram HMAC auth via e2e/fixtures.ts (uniqueTelegramUser),
//   real API/geo/checkin endpoints.
// outputs: Playwright pass/fail; created users are tracked for the acceptance
//   cleanup adapter via E2E_CREATED_USERS_FILE (fixtures default).
// dependencies: e2e/fixtures.ts (test, expect, completeOnboarding).
// side_effects: Creates one real user, updates its profile city, stores one
//   real check-in for the resolved target date.
// emitted_logs: none.
// invariants:
//   - No page.route/mock/interception; no conditional early returns or
//     expect(true) passes.
//   - Selectors use the public DOM contract only (data-testid, roles, saved
//     state text).
// failure_policy: any failed expectation fails the test.
// END_MODULE_CONTRACT: M-TEST-E2E-PROFILE-CITY-CHECKIN

// START_MODULE_MAP: M-TEST-E2E-PROFILE-CITY-CHECKIN
// public_entrypoints:
//   - Playwright test runner
// semantic_blocks:
//   - CITY_EDIT: profile current-city edit via CityPicker contract
//   - CHECKIN_FLOW: mood/energy/accuracy submit + read-back
// END_MODULE_MAP: M-TEST-E2E-PROFILE-CITY-CHECKIN

import { test, expect, completeOnboarding } from './fixtures';

test.describe('Profile city edit + check-in — Real API (P1-6)', () => {
  test.use({ uniqueTelegramUser: true });

  test('edits current city via suggestions and completes check-in with read-back', async ({ page }) => {
    test.setTimeout(120000);

    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    // Real onboarding (no skips, no conditional passes).
    await page.goto('/onboarding');
    await completeOnboarding(page);

    // --- CITY_EDIT: profile "Где живу сейчас" via the CityPicker contract ---
    await page.goto('/profile');
    const profileScreen = page.getByTestId('profile-screen');
    await expect(profileScreen).toHaveAttribute('data-state', 'ready', { timeout: 15000 });

    await page.getByTestId('profile-data-row-current-city').click();
    const sheet = page.getByTestId('profile-edit-sheet');
    await expect(sheet).toBeVisible({ timeout: 5000 });

    const cityInput = sheet.getByTestId('city-picker-input');
    await cityInput.fill('Казань');
    const suggestions = sheet.getByTestId('city-picker-suggestions');
    await expect(suggestions).toBeVisible({ timeout: 10000 });
    const firstSuggestion = suggestions.getByTestId('city-picker-suggestion').first();
    await expect(firstSuggestion).toBeVisible({ timeout: 10000 });
    await firstSuggestion.click();

    const saveButton = sheet.getByRole('button', { name: 'Сохранить' });
    await expect(saveButton).toBeEnabled({ timeout: 5000 });
    await saveButton.click();
    await expect(sheet).toBeHidden({ timeout: 10000 });

    // The profile row shows the new city.
    await expect(page.getByTestId('profile-data-row-current-city')).toContainText('Казань', { timeout: 10000 });

    // The real GET /api/profile carries the new city + coordinates + timezone.
    const profile = await page.evaluate(async () => {
      const res = await fetch('/api/profile', {
        credentials: 'include',
        headers: { Accept: 'application/json' },
      });
      if (!res.ok) throw new Error(`GET /api/profile failed: ${res.status}`);
      return res.json();
    });
    expect(profile.currentLocation?.city ?? '').toContain('Казань');
    expect(profile.currentLocation?.lat).toBeGreaterThan(55);
    expect(profile.currentLocation?.lat).toBeLessThan(56.5);
    expect(profile.currentLocation?.lon).toBeGreaterThan(48.5);
    expect(profile.currentLocation?.lon).toBeLessThan(50);
    expect(profile.currentLocation?.tz).toBe('Europe/Moscow');

    // --- CHECKIN_FLOW: mood → energy → accuracy, then saved read-back ---
    // "Today" in the profile timezone (Europe/Moscow), not UTC: near midnight
    // the UTC date can point at the wrong day.
    const today = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Moscow' }).format(new Date());
    await page.goto(`/checkin?target=${today}`);
    await expect(page.getByTestId('checkin-screen')).toBeVisible({ timeout: 10000 });

    await page.getByTestId('mood-4').click();
    await page.getByTestId('energy-3').click();
    await page.getByTestId('accuracy-2').click();

    // Accuracy auto-submits; completion navigates to the saved day page.
    await page.waitForURL(`**/day/${today}**`, { timeout: 15000 });

    // Read-back after a fresh load: the saved state comes from the real API.
    await page.goto(`/checkin?target=${today}`);
    await expect(page.getByText('Оценка уже сохранена')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Настроение: 4 / 5')).toBeVisible();
  });
});
