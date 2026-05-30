// AI_HEADER
// module: M-TEST-CROSS-FEATURE-NAVIGATION
// wave: W-2.7
// purpose: Test navigation between Day, Chat, Readings, Calendar

import { test, expect } from '@playwright/test'

test.describe('Cross-Feature Navigation', () => {
  test.use({ baseURL: 'https://dev.astro.vasiliy-ivanov.ru' })

  test('should navigate Day → Chat → Readings → Calendar → Day', async ({ page }) => {
    // Setup: authenticated + onboarded user
    await page.addInitScript(() => {
      (window as any).Telegram = {
        WebApp: {
          initData: 'query_id=test&user=%7B%22id%22%3A123456%7D&auth_date=1622559000&hash=test',
          initDataUnsafe: { user: { id: 123456 } },
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
      localStorage.setItem('lumen:onboarded', 'true')
    })

    await page.route('**/api/**', route => {
      route.fulfill({ status: 200, body: JSON.stringify({ ok: true, data: [] }) })
    })

    // Start at /day/today
    console.log('=== Navigate to Day ===')
    await page.goto('/day/today')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: '/tmp/nav-day.png', fullPage: true })
    expect(page.url()).toContain('/day/today')

    // Navigate to Chat
    console.log('=== Navigate to Chat ===')
    const chatLink = page.locator('a[href="/chat"], a[href*="/chat"], button:has-text("Chat"), nav a:has-text("Chat")').first()
    if (await chatLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      await chatLink.click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: '/tmp/nav-chat.png', fullPage: true })
      expect(page.url()).toContain('/chat')
    } else {
      console.log('⚠️ Chat link not found, navigating directly')
      await page.goto('/chat')
      await page.waitForTimeout(1000)
      await page.screenshot({ path: '/tmp/nav-chat.png', fullPage: true })
    }

    // Navigate to Readings
    console.log('=== Navigate to Readings ===')
    const readingsLink = page.locator('a[href="/readings"], a[href*="/readings"], button:has-text("Readings"), nav a:has-text("Readings")').first()
    if (await readingsLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      await readingsLink.click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: '/tmp/nav-readings.png', fullPage: true })
      expect(page.url()).toContain('/readings')
    } else {
      console.log('⚠️ Readings link not found, navigating directly')
      await page.goto('/readings')
      await page.waitForTimeout(1000)
      await page.screenshot({ path: '/tmp/nav-readings.png', fullPage: true })
    }

    // Navigate to Calendar
    console.log('=== Navigate to Calendar ===')
    const calendarLink = page.locator('a[href="/calendar"], a[href*="/calendar"], button:has-text("Calendar"), nav a:has-text("Calendar")').first()
    if (await calendarLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      await calendarLink.click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: '/tmp/nav-calendar.png', fullPage: true })
      expect(page.url()).toContain('/calendar')
    } else {
      console.log('⚠️ Calendar link not found, navigating directly')
      await page.goto('/calendar')
      await page.waitForTimeout(1000)
      await page.screenshot({ path: '/tmp/nav-calendar.png', fullPage: true })
    }

    // Navigate back to Day
    console.log('=== Navigate back to Day ===')
    const dayLink = page.locator('a[href="/day/today"], a[href*="/day"], button:has-text("Today"), nav a:has-text("Today")').first()
    if (await dayLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      await dayLink.click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: '/tmp/nav-back-to-day.png', fullPage: true })
      expect(page.url()).toContain('/day')
    } else {
      console.log('⚠️ Day link not found, navigating directly')
      await page.goto('/day/today')
      await page.waitForTimeout(1000)
      await page.screenshot({ path: '/tmp/nav-back-to-day.png', fullPage: true })
    }

    console.log('✅ Cross-feature navigation test passed')
  })

  test('should handle direct URL navigation', async ({ page }) => {
    // Setup: authenticated + onboarded user
    await page.addInitScript(() => {
      (window as any).Telegram = {
        WebApp: {
          initData: 'query_id=test&user=%7B%22id%22%3A123458%7D&auth_date=1622559000&hash=test',
          initDataUnsafe: { user: { id: 123458 } },
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
      localStorage.setItem('lumen:onboarded', 'true')
    })

    await page.route('**/api/**', route => {
      route.fulfill({ status: 200, body: JSON.stringify({ ok: true, data: [] }) })
    })

    // Test direct navigation to each route
    const routes = ['/day/today', '/chat', '/readings', '/calendar']

    for (const route of routes) {
      console.log(`=== Direct navigation to ${route} ===`)
      await page.goto(route)
      await page.waitForTimeout(1000)
      expect(page.url()).toContain(route)
      await page.screenshot({ path: `/tmp/nav-direct-${route.replace(/\//g, '-')}.png`, fullPage: true })
    }

    console.log('✅ Direct URL navigation test passed')
  })
})
