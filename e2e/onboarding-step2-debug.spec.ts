// AI_HEADER
// module: M-TEST-ONBOARDING-STEP2-DEBUG
// wave: W-2.7
// purpose: Debug test for onboarding step 2 (birth date/time)

import { test, expect } from '@playwright/test'

test.describe('Onboarding Step 2 Debug', () => {
  test.use({ baseURL: 'https://dev.astro.vasiliy-ivanov.ru' })

  test('should complete step 2 without errors', async ({ page }) => {
    // Mock Telegram Web App
    await page.addInitScript(() => {
      (window as any).Telegram = {
        WebApp: {
          initData: 'query_id=test&user=%7B%22id%22%3A999999%7D&auth_date=1622559000&hash=test',
          initDataUnsafe: { user: { id: 999999, first_name: 'Test User' } },
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

    // Mock auth
    await page.route('**/api/auth/telegram', route => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({ ok: true }),
      })
    })

    const errors: string[] = []
    const consoleMessages: string[] = []

    page.on('console', msg => {
      consoleMessages.push(`[${msg.type()}] ${msg.text()}`)
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })

    page.on('pageerror', error => {
      errors.push(`PAGE ERROR: ${error.message}`)
    })

    await page.goto('/onboarding')

    // Wait for step 1 (welcome)
    await page.waitForTimeout(2000)

    // Screenshot step 1
    await page.screenshot({ path: '/tmp/onboarding-debug-step1.png', fullPage: true })

    console.log('=== Step 1 (Welcome) ===')

    // Find and click "Next" button (step 1 → step 2)
    const nextButton = page.locator('button:has-text("Далее"), button:has-text("Продолжить"), button:has-text("Next"), button:has-text("Начать")')

    const buttonVisible = await nextButton.first().isVisible({ timeout: 5000 }).catch(() => false)
    console.log('Next button visible:', buttonVisible)

    if (!buttonVisible) {
      console.error('❌ Next button not found on step 1')
      await page.screenshot({ path: '/tmp/onboarding-debug-step1-error.png', fullPage: true })
    }

    await nextButton.first().click()

    // Wait for step 2 to load
    await page.waitForTimeout(2000)

    // Screenshot step 2
    await page.screenshot({ path: '/tmp/onboarding-debug-step2.png', fullPage: true })

    console.log('=== Step 2 (Birth) ===')

    // Check if step 2 is visible
    const step2Indicators = [
      'text=/дата рождения|birth date|когда вы родились/i',
      'input[type="date"]',
      'input[type="time"]',
      '[data-step="2"]',
      '[data-testid="step-birth"]',
    ]

    let step2Visible = false
    for (const selector of step2Indicators) {
      const visible = await page.locator(selector).first().isVisible().catch(() => false)
      console.log(`Selector "${selector}" visible:`, visible)
      if (visible) {
        step2Visible = true
        break
      }
    }

    console.log('Step 2 visible:', step2Visible)

    // Print all console messages
    console.log('=== Console Messages ===')
    consoleMessages.forEach(msg => console.log(msg))

    // Print errors
    console.log('=== Errors ===')
    errors.forEach(err => console.log(err))

    // Filter critical errors
    const criticalErrors = errors.filter(e =>
      !e.includes('Download the React DevTools') &&
      !e.includes('favicon') &&
      !e.includes('404 (Not Found)')
    )

    if (criticalErrors.length > 0) {
      console.error('❌ CRITICAL ERRORS FOUND:', criticalErrors)
    }

    // Check for specific error patterns
    const hasRuntimeError = errors.some(e =>
      e.includes('TypeError') ||
      e.includes('ReferenceError') ||
      e.includes('Cannot read') ||
      e.includes('undefined')
    )

    if (hasRuntimeError) {
      console.error('❌ Runtime error detected on step 2')
    }

    // Assertions
    expect(criticalErrors).toEqual([])
    expect(hasRuntimeError).toBe(false)
    expect(step2Visible).toBe(true)

    console.log('✅ Step 2 loaded successfully without critical errors')
  })

  test('should navigate through all steps', async ({ page }) => {
    // Mock Telegram Web App
    await page.addInitScript(() => {
      (window as any).Telegram = {
        WebApp: {
          initData: 'query_id=test&user=%7B%22id%22%3A999998%7D&auth_date=1622559000&hash=test',
          initDataUnsafe: { user: { id: 999998, first_name: 'Test User 2' } },
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
      route.fulfill({
        status: 200,
        body: JSON.stringify({ ok: true }),
      })
    })

    await page.goto('/onboarding')
    await page.waitForTimeout(1000)

    // Step 1: Welcome
    console.log('=== Step 1: Welcome ===')
    await page.screenshot({ path: '/tmp/onboarding-all-step1.png', fullPage: true })

    const step1Button = page.locator('button:has-text("Далее"), button:has-text("Продолжить"), button:has-text("Next"), button:has-text("Начать")').first()
    await step1Button.click()
    await page.waitForTimeout(1000)

    // Step 2: Birth
    console.log('=== Step 2: Birth ===')
    await page.screenshot({ path: '/tmp/onboarding-all-step2.png', fullPage: true })

    // Fill birth date and time
    const dateInput = page.locator('input[type="date"]').first()
    const timeInput = page.locator('input[type="time"]').first()

    const dateVisible = await dateInput.isVisible().catch(() => false)
    const timeVisible = await timeInput.isVisible().catch(() => false)

    console.log('Date input visible:', dateVisible)
    console.log('Time input visible:', timeVisible)

    if (dateVisible) {
      await dateInput.fill('1990-01-15')
    }
    if (timeVisible) {
      await timeInput.fill('14:30')
    }

    await page.waitForTimeout(500)

    const step2Button = page.locator('button:has-text("Далее"), button:has-text("Продолжить"), button:has-text("Next")').first()
    const step2ButtonEnabled = await step2Button.isEnabled().catch(() => false)
    console.log('Step 2 button enabled:', step2ButtonEnabled)

    if (step2ButtonEnabled) {
      await step2Button.click()
      await page.waitForTimeout(1000)

      // Step 3: Place
      console.log('=== Step 3: Place ===')
      await page.screenshot({ path: '/tmp/onboarding-all-step3.png', fullPage: true })
    } else {
      console.warn('⚠️ Step 2 button is disabled, cannot proceed to step 3')
    }
  })
})
