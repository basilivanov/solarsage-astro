// AI_HEADER
// module: M-TEST-ONBOARDING-COMPLETE
// wave: W-2.7
// purpose: Complete onboarding flow test (all 5 steps)

import { test, expect } from '@playwright/test'

test.describe('Complete Onboarding Flow', () => {
  test.use({ baseURL: 'https://dev.astro.vasiliy-ivanov.ru' })

  test('should complete all 5 steps and redirect to /day/today', async ({ page }) => {
    // Mock Telegram + Auth
    await page.addInitScript(() => {
      (window as any).Telegram = {
        WebApp: {
          initData: 'query_id=test&user=%7B%22id%22%3A999999%7D&auth_date=1622559000&hash=test',
          initDataUnsafe: { user: { id: 999999, first_name: 'Test' } },
          ready: () => {},
          expand: () => {},
          close: () => {},
          MainButton: {
            text: '',
            color: '#3390ec',
            textColor: '#ffffff',
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
        }
      }
      localStorage.clear()
    })

    await page.route('**/api/auth/telegram', route => {
      route.fulfill({ status: 200, body: JSON.stringify({ ok: true }) })
    })

    await page.goto('/')
    await page.waitForURL('**/onboarding', { timeout: 10000 })

    // Step 1: Welcome
    console.log('=== Step 1: Welcome ===')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: '/tmp/onboarding-auto-step1.png', fullPage: true })

    const step1Button = page.locator('button:has-text("Продолжить"), button:has-text("Далее"), button:has-text("Начать")').first()
    await expect(step1Button).toBeVisible({ timeout: 5000 })
    await step1Button.click()

    // Step 2: Birth
    console.log('=== Step 2: Birth ===')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: '/tmp/onboarding-auto-step2.png', fullPage: true })

    // Verify step 2 is visible
    await expect(page.locator('text=/дата и время рождения/i')).toBeVisible({ timeout: 5000 })

    // Fill birth date using NumField inputs (type="text", inputMode="numeric")
    const dayInput = page.getByRole('textbox', { name: 'День' })
    const monthInput = page.getByRole('textbox', { name: 'Месяц' })
    const yearInput = page.getByRole('textbox', { name: 'Год' })
    const hoursInput = page.getByRole('textbox', { name: 'Часы' })
    const minutesInput = page.getByRole('textbox', { name: 'Минуты' })

    await dayInput.fill('15')
    await monthInput.fill('01')
    await yearInput.fill('1990')
    await hoursInput.fill('12')
    await minutesInput.fill('00')

    await page.waitForTimeout(500)

    const step2Button = page.locator('button:has-text("Далее")').first()
    await expect(step2Button).toBeEnabled({ timeout: 5000 })
    await step2Button.click()

    // Step 3: Place
    console.log('=== Step 3: Place ===')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: '/tmp/onboarding-auto-step3.png', fullPage: true })

    // Verify step 3 is visible
    await expect(page.locator('text=/место рождения/i')).toBeVisible({ timeout: 5000 })

    // Click on "Москва" from popular cities (birth place)
    const moscowButton = page.locator('button:has-text("Москва")').first()
    await moscowButton.click()
    await page.waitForTimeout(500)

    // Check "Сейчас живу там же" checkbox to use birth place as current city
    const sameAsBirthCheckbox = page.locator('text=/сейчас живу там же/i')
    await sameAsBirthCheckbox.click()
    await page.waitForTimeout(500)

    const step3Button = page.locator('button:has-text("Далее")').first()
    await expect(step3Button).toBeEnabled({ timeout: 5000 })
    await step3Button.click()

    // Step 4: Birthday
    console.log('=== Step 4: Birthday ===')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: '/tmp/onboarding-auto-step4.png', fullPage: true })

    // Verify step 4 is visible
    await expect(page.locator('text=/где встретишь свой день рождения/i')).toBeVisible({ timeout: 5000 })

    const step4Button = page.locator('button:has-text("Далее")').first()
    await step4Button.click()

    // Step 5: Done
    console.log('=== Step 5: Done ===')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: '/tmp/onboarding-auto-step5.png', fullPage: true })

    // Verify step 5 is visible
    await expect(page.locator('text=/готовим первый день/i')).toBeVisible({ timeout: 5000 })

    // Wait for the button to become enabled (after 1.5s animation)
    const finishButton = page.locator('button:has-text("Открыть мой день")')
    await expect(finishButton).toBeVisible({ timeout: 5000 })
    await expect(finishButton).toBeEnabled({ timeout: 5000 })
    await finishButton.click()

    // Verify redirect to /day/today (or /day/YYYY-MM-DD)
    await page.waitForURL('**/day/**', { timeout: 10000 })
    await page.screenshot({ path: '/tmp/onboarding-auto-complete.png', fullPage: true })

    // Verify we're on a day page
    expect(page.url()).toMatch(/\/day\/(today|\d{4}-\d{2}-\d{2})/)

    // Verify localStorage (can be "true" or "1")
    const onboarded = await page.evaluate(() => localStorage.getItem('lumen:onboarded'))
    expect(['true', '1']).toContain(onboarded)

    console.log('✅ Complete onboarding flow passed')
  })
})
