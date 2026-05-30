// AI_HEADER
// module: M-TEST-ONBOARDING-PRODUCTION
// wave: W-2.7
// purpose: E2E test for onboarding flow via external domain

import { test, expect } from '@playwright/test'

test.describe('Onboarding - Production External Domain', () => {
  test.use({ baseURL: 'https://dev.astro.vasiliy-ivanov.ru' })

  test('should show onboarding for new user', async ({ page }) => {
    // Mock Telegram Web App
    await page.addInitScript(() => {
      (window as any).Telegram = {
        WebApp: {
          initData: 'query_id=test&user=%7B%22id%22%3A999999%7D&auth_date=1622559000&hash=test',
          initDataUnsafe: { user: { id: 999999, first_name: 'New User' } },
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
        },
      }

      // Mock localStorage — новый пользователь
      localStorage.clear()
    })

    // Mock успешную авторизацию
    await page.route('**/api/auth/telegram', (route) => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({ ok: true }),
        headers: { 'Set-Cookie': 'session_id=test-new-user; Path=/; HttpOnly' },
      })
    })

    const errors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })

    await page.goto('/')

    // Ждём редиректа на /onboarding
    await page.waitForURL('**/onboarding', { timeout: 10000 })

    // Скриншот онбординга
    await page.screenshot({ path: '/tmp/onboarding-step1.png', fullPage: true })

    // Проверяем, что нет критических ошибок
    const criticalErrors = errors.filter(
      (e) => e.includes('localhost') || e.includes('ERR_CONNECTION_REFUSED')
    )
    expect(criticalErrors).toEqual([])

    // Проверяем, что есть контент онбординга (welcome screen)
    const hasOnboarding = await page
      .locator('text=/астрология|личная практика|продолжить|персональный/i')
      .first()
      .isVisible()
      .catch(() => false)
    expect(hasOnboarding).toBe(true)

    console.log('✅ Onboarding loaded successfully!')
  })

  test('should skip onboarding for existing user', async ({ page }) => {
    // Mock Telegram Web App
    await page.addInitScript(() => {
      (window as any).Telegram = {
        WebApp: {
          initData: 'query_id=test&user=%7B%22id%22%3A123456%7D&auth_date=1622559000&hash=test',
          initDataUnsafe: { user: { id: 123456, first_name: 'Existing User' } },
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
        },
      }

      // Mock localStorage — пользователь уже прошёл онбординг
      localStorage.setItem('lumen:onboarded', '1')
    })

    // Mock успешную авторизацию
    await page.route('**/api/auth/telegram', (route) => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({ ok: true }),
      })
    })

    await page.goto('/')

    // Ждём редиректа на /day/today (не на /onboarding)
    await page.waitForURL('**/day/today', { timeout: 10000 })

    // Скриншот главной страницы
    await page.screenshot({ path: '/tmp/onboarding-skipped.png', fullPage: true })

    console.log('✅ Onboarding skipped for existing user!')
  })
})
