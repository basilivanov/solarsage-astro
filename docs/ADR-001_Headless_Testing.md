---
id: adr-001
title: Headless Testing Strategy
status: accepted
date: 2026-05-30
---

# ADR-001: Headless Testing Strategy

## Status
Accepted

## Context

### Problem
Нужна стратегия тестирования для MVP, которая:
- Покрывает критичные user flows (UC из verification-matrix.md)
- Работает в CI без GUI
- Позволяет Sonnet видеть результаты (screenshots)
- Интегрируется с GRACE verification gates
- Поддерживает auth-first подход (все через Telegram WebApp)

### Current State
- ✅ Backend: pytest с fixtures для Telegram auth
- ✅ Verification matrix: детальные UC с scenarios
- ❌ Frontend: нет unit тестов (vitest)
- ❌ E2E: нет Playwright тестов
- ❌ Visual regression: нет baseline screenshots

### Requirements
1. **Auth-first**: все endpoint тесты через Telegram auth
2. **3 уровня**: unit (изолированные) / integration (с auth) / e2e (full flow)
3. **Visual regression**: baseline screenshots в git, diff в CI
4. **Verification matrix mapping**: каждый UC → минимум 1 executable test
5. **CI gates**: блокируют merge при падении тестов

## Decision

### 1. Three-Level Testing Pyramid

#### Level 1: Unit Tests (быстрые, много)
**Backend (pytest):**
- Изолированные функции/сервисы БЕЗ auth
- Примеры: scoring canon validation, normalization logic, HMAC validation
- Расположение: `apps/api/tests/test_*.py`
- Coverage target: 80%+ для критичных модулей

**Frontend (vitest):**
- Hooks, reducers, utils БЕЗ UI
- Примеры: useAccess, chatReducer, date formatters
- Расположение: `apps/web/__tests__/**/*.test.ts`
- Coverage target: 60%+ для логики

#### Level 2: Integration Tests (средние, меньше)
**Backend (pytest):**
- Все endpoint тесты С auth через `authenticated_client` fixture
- Примеры: GET /api/day/:date, POST /api/profile, cache invalidation
- Расположение: `apps/api/tests/test_*_endpoints.py`
- Каждый endpoint: happy path + error cases

**Fixture pattern:**
```python
@pytest.fixture
async def authenticated_client(async_client, make_initdata, db_session):
    # 1. Login через fake Telegram initData
    raw = make_initdata(user_id=7777, username="testuser")
    await async_client.post("/api/auth/telegram", json={"initData": raw})
    
    # 2. Onboarding (создание профиля)
    await async_client.post("/api/profile", json={...})
    
    # 3. Возвращаем клиент с session cookie
    return async_client
```

#### Level 3: E2E Tests (медленные, критичные)
**Playwright:**
- Full user flows через Telegram WebApp auth
- Примеры: auth → onboarding → day view → navigation
- Расположение: `apps/web/e2e/**/*.spec.ts`
- Каждый UC из verification-matrix → минимум 1 e2e тест

**Auth helper pattern:**
```typescript
// apps/web/e2e/helpers/auth.ts
async function authenticateAndOnboard(page, context, userData) {
  // 1. Inject Telegram WebApp API
  await page.addInitScript((data) => {
    window.Telegram = { WebApp: { initData: data, ... } };
  }, generateFakeInitData(userData));
  
  // 2. Open app → auto auth
  await page.goto('/');
  
  // 3. Complete onboarding
  await fillOnboardingForm(page, userData);
  
  // 4. Wait for redirect to /day/today
  await page.waitForURL('/day/today');
}
```

### 2. Visual Regression Strategy

**Tool:** Playwright built-in screenshots (не percy.io, не chromatic)

**Baseline storage:** Git repository в `apps/web/e2e/visual/__screenshots__/`

**Workflow:**
1. Первый запуск → генерирует baseline
2. Последующие запуски → сравнивает с baseline
3. Diff > 0.1% → тест падает, артефакты в CI
4. Обновление baseline → коммит новых screenshots

**Example:**
```typescript
// apps/web/e2e/visual/today-screen.spec.ts
test('Today screen - supportive day', async ({ page }) => {
  await authenticateAndOnboard(page, context, testUser);
  await page.goto('/day/2026-05-30');
  await page.waitForSelector('[data-testid="today-headline"]');
  
  // Full screen screenshot
  await expect(page).toHaveScreenshot('today-supportive.png');
  
  // Component screenshot
  const weekStrip = page.locator('[data-testid="week-strip"]');
  await expect(weekStrip).toHaveScreenshot('week-strip.png');
});
```

**Coverage:**
- Today screen: supportive / steady / tense days
- Calendar: 3-month grid
- Locked day: preview + soft lock
- Onboarding: all 5 steps
- Profile: edit form

### 3. Verification Matrix Integration

**Mapping rule:** Каждый UC → минимум 1 executable test

**Example mapping:**

| UC | Test File | Test Name |
|---|---|---|
| UC-TG-AUTH | `e2e/auth.spec.ts` | `test('valid initData → session set')` |
| UC-DAY-VIEW | `test_day_endpoints.py` | `test_get_day_today()` |
| UC-DAY-VIEW | `e2e/day-view.spec.ts` | `test('renders headline, flags, reading')` |
| UC-DAY-NAV | `e2e/day-view.spec.ts` | `test('tap arrow → URL updates')` |
| UC-CAL-NAV | `e2e/calendar.spec.ts` | `test('tap day → navigates to /day/:date')` |
| UC-ACCESS-CHECK | `test_access_service.py` | `test_referral_bonus_14_days()` |
| UC-LOCKED-DAY | `e2e/locked-day.spec.ts` | `test('no access → preview + soft lock')` |

**Scenario coverage:**
- Каждый Scenario (S1, S2, S3) → отдельный test case
- Каждый Gate → минимум 1 assertion

### 4. CI Pipeline

**GitHub Actions workflow:**
```yaml
name: Test

on: [push, pull_request]

jobs:
  backend-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: cd apps/api && pytest tests/ -v
  
  frontend-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pnpm test:unit
  
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: pnpm install
      - run: pnpm playwright install --with-deps
      - run: pnpm test:e2e
      - uses: actions/upload-artifact@v3
        if: failure()
        with:
          name: playwright-report
          path: apps/web/playwright-report/
      - uses: actions/upload-artifact@v3
        if: failure()
        with:
          name: visual-diffs
          path: apps/web/e2e/visual/__screenshots__/__diff_output__/
  
  contracts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pnpm contracts:check
```

**Gates:**
- ✅ All pytest tests pass
- ✅ All vitest tests pass
- ✅ All Playwright tests pass
- ✅ Visual regression diffs < 0.1%
- ✅ Contracts drift check passes

### 5. Test Data Strategy

**Backend:**
- Fixtures: `apps/api/tests/fixtures/*.json`
- Golden JSON: SolarSage parity fixtures (Vasiliy chart)
- In-memory DB: SQLite for fast tests

**Frontend:**
- MSW mocks: `apps/web/__mocks__/handlers.ts`
- Fixture mode: `NEXT_PUBLIC_USE_FIXTURES=true`

**E2E:**
- Real backend in test mode (fixture-backed services)
- Fake Telegram initData через helper
- Test users: user_id 7777, 8888, 9999

### 6. Auth-First Approach

**Principle:** Все тесты идут через Telegram auth, как реальный пользователь.

**Backend:**
- Unit tests: БЕЗ auth (изолированные функции)
- Integration tests: С auth через `authenticated_client` fixture
- Каждый endpoint test: login → onboarding → request

**Frontend:**
- Unit tests: БЕЗ auth (hooks/reducers)
- E2E tests: С auth через `authenticateAndOnboard` helper
- Каждый e2e test: inject Telegram WebApp API → auto auth

**No backdoors:** Нет "test mode" без auth, нет admin endpoints для тестов.

## Consequences

### Positive
- ✅ Executable verification matrix (UC → tests)
- ✅ Visual regression ловит UI поломки
- ✅ Sonnet видит screenshots → понимает правильность UI
- ✅ Auth-first → тесты близки к production
- ✅ CI gates блокируют поломки до merge

### Negative
- ❌ Baseline screenshots занимают ~5-10MB в git
- ❌ E2E тесты медленные (~2-5 мин в CI)
- ❌ Visual regression требует обновления baseline при UI changes
- ❌ Auth setup в каждом тесте добавляет overhead

### Mitigations
- Baseline screenshots: git LFS (опционально)
- E2E скорость: параллельный запуск (Playwright workers)
- Baseline updates: автоматический PR при UI changes
- Auth overhead: shared fixture, переиспользование session

## Implementation Plan

### Wave W-TEST-1: Backend integration tests
**Scope:**
- `test_day_endpoints.py` (UC-DAY-VIEW)
- `test_calendar_endpoints.py` (UC-CAL-NAV)
- `test_access_service.py` (UC-ACCESS-CHECK)
- `authenticated_client` fixture

**Exit criteria:**
- Все UC-DAY-VIEW scenarios (S1-S5) покрыты
- Cache hit/miss assertions
- Performance: p95 < 500ms (cached)

### Wave W-TEST-2: Frontend unit tests
**Scope:**
- `vitest.config.ts`
- `useAccess.test.ts`
- `chatReducer.test.ts`
- `onboardingReducer.test.ts`

**Exit criteria:**
- Coverage 60%+ для lib/grace/**
- CI gate: vitest в GitHub Actions

### Wave W-TEST-3: E2E + Visual regression
**Scope:**
- `playwright.config.ts`
- `e2e/helpers/auth.ts` (authenticateAndOnboard)
- `e2e/auth.spec.ts` (UC-TG-AUTH)
- `e2e/day-view.spec.ts` (UC-DAY-VIEW, UC-DAY-NAV)
- `e2e/calendar.spec.ts` (UC-CAL-NAV)
- `e2e/visual/today-screen.spec.ts` (baseline screenshots)

**Exit criteria:**
- Все критичные UC покрыты e2e
- Baseline screenshots committed
- CI gate: Playwright в GitHub Actions

### Wave W-TEST-4: CI integration
**Scope:**
- `.github/workflows/test.yml`
- Visual diff artifacts upload
- contracts:check gate
- Performance monitoring

**Exit criteria:**
- All gates в CI
- PR блокируется при падении тестов
- Visual diffs доступны в artifacts

## References
- `grace/verification-matrix.md` — UC definitions
- `grace/development-plan.xml` — wave dependencies
- `apps/api/tests/conftest.py` — auth fixtures
- Playwright docs: https://playwright.dev/
