// AI_HEADER
// module: M-TEST-ONBOARDING-REAL
// wave: W-TEST-3
// purpose: Complete onboarding flow test with real Telegram auth (no mocks)

import { test, expect } from './fixtures';

test.describe('Onboarding Flow - Real Telegram Auth', () => {
  test('should complete all steps and redirect to /day/today', async ({ page }) => {
    test.setTimeout(60000);

    // Clear onboarding state so we start fresh
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    // Navigate to onboarding directly (bypass home redirect)
    await page.goto('/onboarding');

    // Wait for step 1: Welcome
    await page.waitForTimeout(2000);

    // Step 1 → Step 2
    const continueBtn = page.locator('button:has-text("Продолжить")');
    await expect(continueBtn).toBeVisible({ timeout: 10000 });
    await continueBtn.click();
    await page.waitForTimeout(1000);

    // Step 2: Birth date/time — should be visible
    await expect(page.locator('text=/Дата и время рождения/i')).toBeVisible({ timeout: 5000 });

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
    await page.waitForTimeout(300);

    // Click "Далее" → Step 3
    const step2Next = page.locator('button:has-text("Далее")').first();
    await expect(step2Next).toBeEnabled({ timeout: 5000 });
    await step2Next.click();
    await page.waitForTimeout(1000);

    // Step 3: Place — select Moscow via search
    await expect(page.locator('text=/Место рождения/i')).toBeVisible({ timeout: 5000 });

    // Wait for Telegram auth to complete before API calls (city search needs auth)
    await page.waitForTimeout(3000);

    // Type city to trigger search
    const cityInput = page.locator('input[placeholder*="Например"], input[placeholder*="Начни"]').first();
    await cityInput.fill('Москва');
    await page.waitForTimeout(2000);

    // Click first search result
    const cityResult = page.locator('ul li button').first();
    await expect(cityResult).toBeVisible({ timeout: 5000 });
    await cityResult.click();
    await page.waitForTimeout(300);

    // Check "Сейчас живу там же" to satisfy currentCity requirement
    const sameAsBirth = page.locator('text=/сейчас живу там же/i');
    await sameAsBirth.click();
    await page.waitForTimeout(300);

    // Click "Далее" → Step 4
    const step3Next = page.locator('button:has-text("Далее")').first();
    await expect(step3Next).toBeEnabled({ timeout: 5000 });
    await step3Next.click();
    await page.waitForTimeout(1000);

    // Step 4: Birthday city
    await expect(page.getByRole('heading', { name: /день рождения/i })).toBeVisible({ timeout: 5000 });
    const step4Next = page.locator('button:has-text("Далее")').first();
    await expect(step4Next).toBeEnabled({ timeout: 5000 });
    await step4Next.click();
    await page.waitForTimeout(2000);

    // Step 5: Done
    await expect(page.locator('text=/первый день|мой день/i').first()).toBeVisible({ timeout: 5000 });

    const finishBtn = page.locator('button:has-text("Открыть")');
    await expect(finishBtn).toBeVisible({ timeout: 5000 });
    await expect(finishBtn).toBeEnabled({ timeout: 5000 });
    await finishBtn.click();

    // Should redirect to /day/...
    await page.waitForURL('**/day/**', { timeout: 15000 });
    expect(page.url()).toMatch(/\/day\/(today|\d{4}-\d{2}-\d{2})/);

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
