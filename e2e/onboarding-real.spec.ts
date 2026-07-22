// AI_HEADER
// module: M-TEST-ONBOARDING-REAL
// wave: W-TEST-3
// purpose: Complete onboarding flow test with real Telegram auth (no mocks)

import { test, expect, waitForTodayState } from './fixtures';

test.describe('Onboarding Flow - Real Telegram Auth', () => {
  test.use({ uniqueTelegramUser: true });

  test('should complete all steps and redirect to /day/today', async ({ page }) => {
    // Outer budget honestly covers the real GeoNames/form path plus the
    // 90s inner terminal-day wait (observed real /api/day up to 67.5s in
    // candidates) + onboarding form work; outer must exceed both.
    test.setTimeout(150000);

    // Clear onboarding state so we start fresh
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    // Navigate to onboarding directly (bypass home redirect)
    await page.goto('/onboarding');

    // Step 1 → Step 2
    const continueBtn = page.getByRole('button', { name: 'Продолжить' });
    await expect(continueBtn).toBeVisible({ timeout: 10000 });
    await continueBtn.click();

    // Step 2: Birth date/time — should be visible
    await expect(page.getByText('Дата и время рождения')).toBeVisible({ timeout: 5000 });

    // Fill birth fields
    const dayInput = page.getByRole('textbox', { name: 'День' });
    const monthInput = page.getByRole('textbox', { name: 'Месяц' });
    const yearInput = page.getByRole('textbox', { name: 'Год' });
    const hoursInput = page.getByRole('textbox', { name: 'Часы' });
    const minutesInput = page.getByRole('textbox', { name: 'Минуты' });

    await dayInput.fill('15');
    await monthInput.fill('01');
    await yearInput.fill('1990');
    await hoursInput.fill('12');
    await minutesInput.fill('00');

    // Click "Далее" → Step 3
    const step2Next = page.getByRole('button', { name: 'Далее' });
    await expect(step2Next).toBeEnabled({ timeout: 5000 });
    await step2Next.click();

    // Step 3: Place — select Moscow via search
    await expect(page.getByText('Место рождения')).toBeVisible({ timeout: 5000 });

    // Type city to trigger search (scoped to the birth-city wrapper —
    // StepPlace can render two pickers when "same as birth" is unchecked)
    const birthCityField = page.getByTestId('onboarding-birth-city-field');
    const cityInput = birthCityField.getByTestId('city-picker-input');
    await cityInput.fill('Москва');

    // Click first search result (real GeoNames latency needs headroom)
    const cityResult = birthCityField.getByTestId('city-picker-suggestion').first();
    await expect(cityResult).toBeVisible({ timeout: 15000 });
    await cityResult.click();

    // Check "Сейчас живу там же" to satisfy currentCity requirement
    const sameAsBirth = page.getByText(/сейчас живу там же/i);
    await sameAsBirth.click();

    // Click "Далее" → Step 4
    const step3Next = page.getByRole('button', { name: 'Далее' });
    await expect(step3Next).toBeEnabled({ timeout: 5000 });
    await step3Next.click();

    // Step 4: Birthday city
    await expect(page.getByRole('heading', { name: /день рождения/i })).toBeVisible({ timeout: 5000 });
    const step4Next = page.getByRole('button', { name: 'Далее' });
    await expect(step4Next).toBeEnabled({ timeout: 5000 });
    await step4Next.click();

    // Step 5: Gender
    await expect(page.getByRole('heading', { name: /мужчина или женщина/i })).toBeVisible({ timeout: 5000 });
    await page.getByRole('button', { name: 'Мужчина' }).click();

    // Step 6: Done
    await expect(page.getByText('Готово', { exact: true })).toBeVisible({ timeout: 5000 });
    const finishBtn = page.getByRole('button', { name: /Открыть мой день|Открыть/i });
    await expect(finishBtn).toBeEnabled({ timeout: 5000 });
    await finishBtn.click();

    // Should redirect to /day/...
    await page.waitForURL('**/day/**', { timeout: 15000 });
    expect(page.url()).toMatch(/\/day\/(today|\d{4}-\d{2}-\d{2})/);

    // The day landing must reach the exact locked state — this standalone
    // flow always creates a fresh user with no access ledger.
    await waitForTodayState(page, 'locked');

    // localStorage should be set
    const onboarded = await page.evaluate(() =>
      localStorage.getItem('lumen:onboarded')
    );
    expect(['true', '1']).toContain(onboarded);

    console.log('Onboarding completed successfully');
  });

  test('should validate birth date before allowing next', async ({ page }) => {
    test.setTimeout(30000);

    await page.addInitScript(() => localStorage.clear());

    await page.goto('/onboarding');
    await page.waitForTimeout(2000);

    // Step 1 → Step 2
    await page.locator('button:has-text("Продолжить")').click();
    await page.waitForTimeout(1000);

    await expect(page.locator('text=/Дата и время рождения/i')).toBeVisible({ timeout: 5000 });

    // "Далее" should be disabled without valid date
    const nextBtn = page.locator('button:has-text("Далее")').first();
    await expect(nextBtn).toBeDisabled({ timeout: 3000 });

    // Fill invalid day
    const dayInput = page.getByRole('textbox', { name: 'День' });
    await dayInput.fill('32');
    await expect(nextBtn).toBeDisabled({ timeout: 3000 });

    console.log('Validation works correctly');
  });
});
