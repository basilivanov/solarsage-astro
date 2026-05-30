// AI_HEADER
// module: M-TEST-SESSION-PERSISTENCE
// wave: W-2.7
// purpose: Test session persistence across page reloads

import { test, expect } from '@playwright/test'

test.describe('Session Persistence', () => {
  test.use({ baseURL: 'https://dev.astro.vasiliy-ivanov.ru' })

  test('should persist session across page reloads', async ({ page }) => {
    // Mock Telegram + Auth
    await page.addInitScript(() => {
      (window as any).Telegram = {
        WebApp: {
          initData: 'query_id=test&user=%7B%22id%22%3A123456%7D&auth_date=1622559000&hash=test',
          initDataUnsafe: { user: { id: 123456, first_name: 'Test' } },
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
      localStorage.setItem('lumen:onboarded', '1') // Use "1" instead of "true"
    })

    await page.route('**/api/auth/telegram', route => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({ ok: true }),
        headers: { 'Set-Cookie': 'session_id=test-session; Path=/; HttpOnly' }
      })
    })

    // Mock API responses
    await page.route('**/api/**', route => {
      const url = route.request().url()
      if (url.includes('/api/auth/telegram')) {
        route.fulfill({
          status: 200,
          body: JSON.stringify({ ok: true }),
        })
      } else {
        route.fulfill({
          status: 200,
          body: JSON.stringify({ ok: true, data: [] }),
        })
      }
    })

    console.log('=== Initial load ===')
    await page.goto('/')
    await page.waitForURL('**/day/**', { timeout: 10000 })
    await page.screenshot({ path: '/tmp/session-initial.png', fullPage: true })

    // Verify we're on /day/today or /day/YYYY-MM-DD
    expect(page.url()).toMatch(/\/day\/(today|\d{4}-\d{2}-\d{2})/)

    console.log('=== Reload page ===')
    await page.reload()
    await page.waitForTimeout(2000)

    // Should still be on /day/today (not redirected to /onboarding or auth)
    expect(page.url()).toMatch(/\/day\/(today|\d{4}-\d{2}-\d{2})/)

    await page.screenshot({ path: '/tmp/session-persistence.png', fullPage: true })

    console.log('=== Navigate away and back ===')
    await page.goto('/chat')
    await page.waitForTimeout(1000)
    await page.goto('/day/today')
    await page.waitForTimeout(1000)

    // Should still be on /day/today
    expect(page.url()).toMatch(/\/day\/(today|\d{4}-\d{2}-\d{2})/)

    await page.screenshot({ path: '/tmp/session-navigate-back.png', fullPage: true })

    console.log('✅ Session persistence test passed')
  })

  test('should redirect to onboarding when not onboarded', async ({ page }) => {
    // Mock Telegram + Auth but NO onboarded flag
    await page.addInitScript(() => {
      (window as any).Telegram = {
        WebApp: {
          initData: 'query_id=test&user=%7B%22id%22%3A123457%7D&auth_date=1622559000&hash=test',
          initDataUnsafe: { user: { id: 123457, first_name: 'Test' } },
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
      localStorage.clear() // No onboarded flag
    })

    await page.route('**/api/auth/telegram', route => {
      route.fulfill({ status: 200, body: JSON.stringify({ ok: true }) })
    })

    console.log('=== Load without onboarded flag ===')
    await page.goto('/')
    await page.waitForURL('**/onboarding', { timeout: 10000 })

    // Should be redirected to /onboarding
    expect(page.url()).toContain('/onboarding')

    await page.screenshot({ path: '/tmp/session-not-onboarded.png', fullPage: true })

    console.log('✅ Redirect to onboarding test passed')
  })
})
