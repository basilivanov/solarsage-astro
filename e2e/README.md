# E2E Testing Guide

## Real Today V2 preview (3003)

Real preview on port 3003 expects an already-running API (8000) and sidecar
(18091) on the host (Compose app stack on this machine); the launcher does not
start backend or sidecar. In the `e2e.yml` workflow the stack is ephemeral:
Postgres/Redis service containers plus `uvicorn` sidecar/API and a production
Next build — no host services and no production systemd units are touched.

> The real E2E is intentionally strict and fails closed until Stage 1 canonical
> API convergence. Before S1.W3, a `today.v1` identity failure is expected and
> must not be treated as a green real-preview result.

```bash
# Verify the local stack first (Compose app project on this host)
docker compose -p solarsage-app ps

# Start real preview
pnpm preview:v2:real
```

URL: `http://127.0.0.1:3003/day/2026-07-08?why=1`

Run E2E from a second terminal while the launcher is running:

```bash
E2E_BASE_URL=http://127.0.0.1:3003 \
  pnpm exec playwright test e2e/real-v2-preview.spec.ts \
    --project=chromium --project=mobile
```

The real spec uses no route interception, no cookie seeding, no Telegram injection,
and accepts only `today.v2.1 / frontend 3 / content 10` with all three backend
horizons. Mock `pnpm preview:v2` remains a separate test-only reference.
Stop the real launcher with Ctrl+C. It restores only the exact Next-generated
`next-env.d.ts` declaration; `tsconfig.json` is verified during startup and is
never rewritten during normal shutdown.

## Overview

Playwright E2E tests для SolarSage Astro, которые ловят 95% ошибок фронтенда ДО продакшена.

## Что тестируем

Real E2E suites (real Telegram HMAC, no route interception except where noted):

- `today.spec.ts` — Today screen after real auth/onboarding, calendar navigation,
  week strip navigation.
- `onboarding-real.spec.ts` — full real onboarding flow.
- `calendar.spec.ts` — calendar grid and day navigation.
- `cross-feature-navigation.spec.ts` — Day → Calendar → Chat → Profile → Day
  with required link and destination assertions (no conditional passes).
- `profile-city-checkin.spec.ts` — profile "Где живу сейчас" edit through the
  public CityPicker contract (`city-picker-input/-suggestions/-suggestion`)
  with real GET /api/profile proof, then check-in mood → energy → accuracy
  with fresh-load read-back (no interception).
- `readings-horary.spec.ts` — readings screen contract + real horary
  lifecycle: submit (weekly free credit) → auto-navigated answer view → API
  read-back (`status=answered`) → history card (no interception; the product
  has no delete/archive operation and none is invented).
- `natal-report.spec.ts` — natal preview ready contract + the product's own
  `/readings/natal/generating` route (starts generation, polls, redirects) →
  ready report view on the unified `natal-report-screen` root (requires
  `NATAL_REPORT_ENABLED=true` in the ephemeral E2E stack; production flag
  stays off).
- `chat.spec.ts` — real chat send → user bubble → structural assistant reply
  (roles + non-empty content, never LLM-text-dependent).
- `locked-features.spec.ts` — locked/paywalled states.
- `edge-cases.spec.ts` — edge cases (contains one page.route interception).
- `hydration-guard.spec.ts` — hydration stability.
- `real-v2-preview.spec.ts` — V2 preview, strictly no interception (uses
  `/api/auth/dev` instead of Telegram HMAC).
- `dev-timing-fixture.spec.ts`, `dev-visible-sphere-status.spec.ts` — dev
  fixtures for timing/sphere states.

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
pnpm exec playwright test e2e/today.spec.ts

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
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Start Services

The E2E workflow stack is ephemeral and self-contained: GitHub Actions
Postgres/Redis service containers plus `uvicorn` sidecar (18091) and API
(8000) and a production Next build (3002), all started inside the workflow
run and cleaned up afterwards. Production systemd units are never touched.
For local runs, use the already-running host stack (Compose app project):

```bash
docker compose -p solarsage-app ps
```

Start the real preview on 3003:

```bash
pnpm preview:v2:real
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

E2E tests are **manual-only** for ad-hoc runs and **reusable** for the release
gate: `.github/workflows/e2e.yml` supports `workflow_dispatch` with a `suite`
input (`smoke` = today/calendar/cross-feature-navigation on Chromium,
`release` = the blocking gate subset, `full` = all specs) and `workflow_call`
(required string `suite` + required secrets `E2E_TELEGRAM_BOT_TOKEN` /
`E2E_OPENROUTER_API_KEY`; missing secrets fail closed before the stack
starts).

The `release` suite runs only the existing real-HMAC specs without route
interception: `onboarding-real.spec.ts`, `today.spec.ts`, `calendar.spec.ts`,
`cross-feature-navigation.spec.ts`, `profile-city-checkin.spec.ts`,
`readings-horary.spec.ts`, `natal-report.spec.ts`, `chat.spec.ts` (dev-v2 and
edge-cases stay out of the gate). The production deploy workflow reuses it as
the `real-e2e` job (`needs: [source-quality, visual-baselines]`), and the
`deploy` job requires it (`needs: [build, artifact-acceptance, real-e2e]`), so
a failing real flow blocks migrate/deploy/tag.

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
pnpm exec playwright test --debug e2e/today.spec.ts
```

## Common Issues

### Issue: "Timeout waiting for selector"

**Причина:** API не отвечает или фронтенд висит в загрузке.

**Решение:**
1. Проверьте, что backend запущен: `curl http://localhost:8000/api/health`
2. Проверьте логи backend: `tail -f /tmp/solarsage-api.log`
3. Проверьте `NEXT_PUBLIC_API_URL` в `.env`

### Issue: "401 Unauthorized"

**Причина:** Нет сессии для тестов.

**Решение:**
- Тесты должны мокать API или использовать тестовую сессию
- Mock/fixture layer lives only in `e2e/mock-visual/` (test-only route interception)

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
