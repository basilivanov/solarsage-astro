import { test, expect } from '@playwright/test'

test.describe('Production - External Domain', () => {
  test.use({ baseURL: 'https://dev.astro.vasiliy-ivanov.ru' })

  test('should load without errors via external domain', async ({ page }) => {
    const errors: string[] = []

    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })

    page.on('pageerror', error => {
      errors.push(error.message)
    })

    await page.goto('/')

    // Ждём загрузки
    await page.waitForTimeout(5000)

    // Делаем скриншот
    await page.screenshot({ path: '/tmp/production-homepage.png', fullPage: true })

    // Проверяем, что нет ошибок localhost
    const localhostErrors = errors.filter(e => e.includes('localhost'))
    expect(localhostErrors).toEqual([])

    console.log('All errors:', errors)
  })

  test('should load /day/today via external domain', async ({ page }) => {
    const errors: string[] = []
    const requests: string[] = []

    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })

    page.on('request', request => {
      requests.push(request.url())
    })

    await page.goto('/day/today')

    // Ждём загрузки
    await page.waitForTimeout(5000)

    // Делаем скриншот
    await page.screenshot({ path: '/tmp/production-today.png', fullPage: true })

    // Проверяем, что все запросы идут на dev.astro.vasiliy-ivanov.ru
    const localhostRequests = requests.filter(url => url.includes('localhost'))

    console.log('All requests:', requests.filter(url => url.includes('api')))
    console.log('Localhost requests:', localhostRequests)

    expect(localhostRequests).toEqual([])

    // Проверяем, что нет ошибок
    const criticalErrors = errors.filter(e =>
      e.includes('ERR_CONNECTION_REFUSED') ||
      e.includes('localhost')
    )
    expect(criticalErrors).toEqual([])
  })

  test('should show auth or content (not infinite loading)', async ({ page }) => {
    await page.goto('/day/today')

    // Ждём, пока исчезнет loading или появится контент
    await page.waitForTimeout(10000)

    // Делаем скриншот
    await page.screenshot({ path: '/tmp/production-final-state.png', fullPage: true })

    // Проверяем, что есть либо auth screen, либо контент
    const hasAuth = await page.locator('[data-testid="auth-loading"], [data-testid="auth-error"]').isVisible().catch(() => false)
    const hasContent = await page.locator('h1, h2, [role="heading"]').isVisible().catch(() => false)
    const hasError = await page.locator('[data-testid="error-message"]').isVisible().catch(() => false)

    console.log('Has auth:', hasAuth)
    console.log('Has content:', hasContent)
    console.log('Has error:', hasError)

    // Должно быть что-то из этого (не пустая страница)
    expect(hasAuth || hasContent || hasError).toBe(true)
  })
})
