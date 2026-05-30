// AI_HEADER
// module: M-TEST-ONBOARDING-VALIDATION
// wave: W-2.7
// purpose: Test onboarding validation (birth date, required fields)

import { test, expect } from '@playwright/test'

test.describe('Onboarding Validation', () => {
  test.use({ baseURL: 'https://dev.astro.vasiliy-ivanov.ru' })

  test('should validate birth date and show error for invalid input', async ({ page }) => {
    // Setup
    await page.addInitScript(() => {
      (window as any).Telegram = {
        WebApp: {
          initData: 'query_id=test&user=%7B%22id%22%3A999999%7D&auth_date=1622559000&hash=test',
          initDataUnsafe: { user: { id: 999999 } },
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

    await page.goto('/onboarding')
    await page.waitForTimeout(1000)

    // Step 1 → Step 2
    console.log('=== Step 1: Welcome ===')
    const step1Button = page.locator('button:has-text("Продолжить"), button:has-text("Далее"), button:has-text("Начать")').first()
    await step1Button.click()
    await page.waitForTimeout(1000)

    console.log('=== Step 2: Birth (validation test) ===')
    await page.screenshot({ path: '/tmp/validation-step2-empty.png', fullPage: true })

    // Try to proceed without entering date
    const step2Button = page.locator('button:has-text("Далее")').first()

    // Button should be disabled when fields are empty
    const isDisabled = await step2Button.isDisabled()
    console.log('Button disabled (empty fields):', isDisabled)
    expect(isDisabled).toBe(true)

    await page.screenshot({ path: '/tmp/validation-button-disabled.png', fullPage: true })

    // Enter invalid date (e.g., 32.13.2025)
    console.log('=== Enter invalid date ===')
    const dayInput = page.getByRole('textbox', { name: 'День' })
    const monthInput = page.getByRole('textbox', { name: 'Месяц' })
    const yearInput = page.getByRole('textbox', { name: 'Год' })

    await dayInput.fill('32') // Invalid day
    await monthInput.fill('13') // Invalid month
    await yearInput.fill('2025')

    await page.waitForTimeout(500)

    // Button should still be disabled
    const stillDisabled = await step2Button.isDisabled()
    console.log('Button disabled (invalid date):', stillDisabled)
    expect(stillDisabled).toBe(true)

    await page.screenshot({ path: '/tmp/validation-invalid-date.png', fullPage: true })

    // Enter valid date
    console.log('=== Enter valid date ===')
    await dayInput.fill('15')
    await monthInput.fill('01')
    await yearInput.fill('1990')

    // Enter time or check "unknown time"
    const hoursInput = page.getByRole('textbox', { name: 'Часы' })
    const minutesInput = page.getByRole('textbox', { name: 'Минуты' })

    await hoursInput.fill('12')
    await minutesInput.fill('00')

    await page.waitForTimeout(500)

    // Button should now be enabled
    const isEnabled = await step2Button.isEnabled()
    console.log('Button enabled (valid date):', isEnabled)
    expect(isEnabled).toBe(true)

    await page.screenshot({ path: '/tmp/validation-valid-date.png', fullPage: true })

    // Should be able to proceed
    await step2Button.click()
    await page.waitForTimeout(1000)

    // Should be on Step 3
    await expect(page.locator('text=/место рождения|где ты родился/i')).toBeVisible({ timeout: 5000 })
    await page.screenshot({ path: '/tmp/validation-success.png', fullPage: true })

    console.log('✅ Validation test passed')
  })

  test('should allow "unknown time" checkbox', async ({ page }) => {
    // Setup
    await page.addInitScript(() => {
      (window as any).Telegram = {
        WebApp: {
          initData: 'query_id=test&user=%7B%22id%22%3A999998%7D&auth_date=1622559000&hash=test',
          initDataUnsafe: { user: { id: 999998 } },
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

    await page.goto('/onboarding')
    await page.waitForTimeout(1000)

    // Step 1 → Step 2
    const step1Button = page.locator('button:has-text("Продолжить"), button:has-text("Далее"), button:has-text("Начать")').first()
    await step1Button.click()
    await page.waitForTimeout(1000)

    console.log('=== Step 2: Test "unknown time" checkbox ===')

    // Enter valid date
    const dayInput = page.getByRole('textbox', { name: 'День' })
    const monthInput = page.getByRole('textbox', { name: 'Месяц' })
    const yearInput = page.getByRole('textbox', { name: 'Год' })

    await dayInput.fill('15')
    await monthInput.fill('01')
    await yearInput.fill('1990')

    await page.waitForTimeout(500)

    // Check "unknown time" checkbox
    const unknownTimeCheckbox = page.locator('text=/не знаю точное время/i')
    await unknownTimeCheckbox.click()

    await page.waitForTimeout(500)
    await page.screenshot({ path: '/tmp/validation-unknown-time.png', fullPage: true })

    // Button should be enabled (date is valid, time is optional)
    const step2Button = page.locator('button:has-text("Далее")').first()
    const isEnabled = await step2Button.isEnabled()
    console.log('Button enabled (unknown time):', isEnabled)
    expect(isEnabled).toBe(true)

    // Should be able to proceed
    await step2Button.click()
    await page.waitForTimeout(1000)

    // Should be on Step 3
    await expect(page.locator('text=/место рождения|где ты родился/i')).toBeVisible({ timeout: 5000 })

    console.log('✅ Unknown time checkbox test passed')
  })

  test('should validate place fields on step 3', async ({ page }) => {
    // Setup
    await page.addInitScript(() => {
      (window as any).Telegram = {
        WebApp: {
          initData: 'query_id=test&user=%7B%22id%22%3A999997%7D&auth_date=1622559000&hash=test',
          initDataUnsafe: { user: { id: 999997 } },
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

    await page.goto('/onboarding')
    await page.waitForTimeout(1000)

    // Step 1 → Step 2
    const step1Button = page.locator('button:has-text("Продолжить"), button:has-text("Далее"), button:has-text("Начать")').first()
    await step1Button.click()
    await page.waitForTimeout(1000)

    // Fill Step 2
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
    await step2Button.click()
    await page.waitForTimeout(1000)

    console.log('=== Step 3: Place (validation test) ===')
    await page.screenshot({ path: '/tmp/validation-step3-empty.png', fullPage: true })

    // Try to proceed without entering place
    const step3Button = page.locator('button:has-text("Далее")').first()

    // Button should be disabled when place is empty
    const isDisabled = await step3Button.isDisabled()
    console.log('Button disabled (empty place):', isDisabled)
    expect(isDisabled).toBe(true)

    // Click on "Москва" from popular cities
    const moscowButton = page.locator('button:has-text("Москва")').first()
    await moscowButton.click()

    await page.waitForTimeout(500)

    // Check "Сейчас живу там же" checkbox
    const sameAsBirthCheckbox = page.locator('text=/сейчас живу там же/i')
    await sameAsBirthCheckbox.click()

    await page.waitForTimeout(500)

    // Button should now be enabled
    const isEnabled = await step3Button.isEnabled()
    console.log('Button enabled (place filled):', isEnabled)
    expect(isEnabled).toBe(true)

    await page.screenshot({ path: '/tmp/validation-step3-valid.png', fullPage: true })

    console.log('✅ Place validation test passed')
  })
})
