# E2E Testing Guide

## Overview

Playwright E2E tests для SolarSage Astro, которые ловят 95% ошибок фронтенда ДО продакшена.

## Что тестируем

### 1. API Integration (`api-integration.spec.ts`)
- ✅ Отсутствие бесконечной загрузки
- ✅ Обработка 401 Unauthorized
- ✅ Обработка network errors
- ✅ Обработка 500 Internal Server Error
- ✅ Tracking API response times
- ✅ Capture console errors

### 2. Performance (`performance.spec.ts`)
- ✅ Page load time (< 5 seconds)
- ✅ First Contentful Paint (FCP)
- ✅ Memory leaks detection
- ✅ API response time
- ✅ Long tasks detection

### 3. GRACE Logs (`grace-logs.spec.ts`)
- ✅ Frontend log shipping
- ✅ Navigation events logging
- ✅ Error events capture
- ✅ Log shipping latency

### 4. User Flows (`today.spec.ts`)
- ✅ Today screen loads
- ✅ Calendar navigation
- ✅ Week strip navigation

## Quick Start

### Prerequisites

```bash
# Install dependencies
pnpm install

# Install Playwright browsers
pnpm exec playwright install --with-deps
```

### Running Tests

```bash
# Run all E2E tests
pnpm test:e2e

# Run with UI (interactive mode)
pnpm test:e2e:ui

# Run specific test file
pnpm exec playwright test e2e/api-integration.spec.ts

# Run in headed mode (see browser)
pnpm exec playwright test --headed

# Debug mode
pnpm exec playwright test --debug
```

## Environment Setup

Убедитесь, что в `.env` указаны правильные порты:

```bash
# Next.js frontend
PORT=3002

# FastAPI backend
NEXT_PUBLIC_API_URL=http://localhost:8001
```

### Start Services

```bash
# Terminal 1: Start backend
cd apps/api
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2: Start frontend
npm run dev

# Terminal 3: Run tests
pnpm test:e2e
```

## Test Results

После запуска тестов:

```bash
# View HTML report
pnpm exec playwright show-report

# Check JSON results
cat test-results/results.json

# Check GRACE logs
cat test-results/grace-logs.json

# Check error events
cat test-results/error-events.json
```

## CI/CD Integration

GitHub Actions автоматически запускает E2E тесты при:
- Push в `main` или `develop`
- Pull Request

См. `.github/workflows/e2e.yml`

## Debugging Failed Tests

### 1. Check screenshots
```bash
ls test-results/
# Найдите *-failed.png
```

### 2. Check videos
```bash
ls test-results/
# Найдите *.webm
```

### 3. Check traces
```bash
pnpm exec playwright show-trace test-results/trace.zip
```

### 4. Run in debug mode
```bash
pnpm exec playwright test --debug e2e/api-integration.spec.ts
```

## Common Issues

### Issue: "Timeout waiting for selector"

**Причина:** API не отвечает или фронтенд висит в загрузке.

**Решение:**
1. Проверьте, что backend запущен: `curl http://localhost:8001/api/health`
2. Проверьте логи backend: `tail -f /tmp/solarsage-api.log`
3. Проверьте `NEXT_PUBLIC_API_URL` в `.env`

### Issue: "401 Unauthorized"

**Причина:** Нет сессии для тестов.

**Решение:**
- Тесты должны мокать API или использовать тестовую сессию
- См. `api-integration.spec.ts` для примеров мокирования

### Issue: "Port 3002 already in use"

**Решение:**
```bash
# Найти процесс
lsof -i :3002

# Убить процесс
kill -9 <PID>
```

## Writing New Tests

### Template

```typescript
import { test, expect } from '@playwright/test';

test.describe('Feature Name', () => {
  test('should do something', async ({ page }) => {
    await page.goto('/path');

    // Wait for content
    await page.waitForSelector('[data-testid="element"]', {
      timeout: 10000
    });

    // Assert
    await expect(page.getByTestId('element')).toBeVisible();
  });
});
```

### Best Practices

1. **Always use data-testid** для селекторов
2. **Set timeouts** для всех waitFor операций
3. **Capture errors** через page.on('console') и page.on('pageerror')
4. **Mock API** для тестирования error states
5. **Clean up** после тестов (если создаёте данные)

## Performance Benchmarks

### Target Metrics

- Page load time: < 5 seconds
- First Contentful Paint: < 1.8 seconds
- API response time: < 3 seconds
- No infinite loading (max 15 seconds)

### Monitoring

Тесты автоматически логируют performance metrics:

```bash
# Check console output after tests
pnpm test:e2e | grep "Performance\|ms"
```

## GRACE Logging Integration

Тесты интегрированы с GRACE W-1.7 log shipping:

- Перехватывают `/api/_log` endpoint
- Сохраняют логи в `test-results/grace-logs.json`
- Проверяют отсутствие ERROR level логов

## Mobile Testing

Тесты запускаются на:
- Desktop Chrome (1280x720)
- iPhone 13 (390x844)

```bash
# Run only mobile tests
pnpm exec playwright test --project=mobile
```

## Continuous Improvement

### Adding New Tests

1. Identify a bug that reached production
2. Write E2E test that catches it
3. Verify test fails without fix
4. Apply fix
5. Verify test passes

### Metrics to Track

- Test coverage (% of user flows)
- Test execution time
- Flakiness rate
- Bugs caught before production

## Support

Вопросы? Проблемы?

1. Check logs: `test-results/`
2. Check GitHub Actions: `.github/workflows/e2e.yml`
3. Check Playwright docs: https://playwright.dev
