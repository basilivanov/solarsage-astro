---
id: visual-regression-testing
status: active
wave: W-TEST
last_review: 2026-07-07
---

# Visual Regression Testing

## Назначение

Visual regression tests защищают внешний вид ключевых экранов от случайных изменений. В SolarSage Astro они являются частью frontend migration gate, но не заменяют real e2e.

Главное разделение:

- **Mock visual e2e** проверяет внешний вид и структуру на стабильных fixture payload'ах.
- **Real e2e** проверяет Telegram auth, backend/API, cache, sidecar/read-model integration.

## Текущая архитектура

Используем Playwright screenshots. MSW не используем.

Для mock visual режима API перехватывается в тесте:

```ts
await page.route("**/api/**", async (route) => {
  const url = new URL(route.request().url())
  if (url.pathname === "/api/day/2026-07-05") {
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(dayFixture),
    })
  }
  return route.fallback()
})
```

Route interception должен жить только в `e2e/` test harness. Product code не должен знать о mock mode.

## Что покрываем скриншотами

Минимальный набор для миграции UI:

- `/day/:date`
- `/calendar`
- `/profile`
- `/readings`
- `/readings/horary`
- `/readings/natal`
- locked state
- empty state
- loading/error state
- generating/report processing state

Не покрываем pixel-perfect всем подряд:

- длинные LLM/API-тексты;
- случайные даты без фиксации;
- каждый мелкий компонент;
- состояния, которые лучше проверять DOM/assertions.

## Baseline Policy

Baseline screenshots коммитятся только для стабильных mock fixtures и фиксированных viewport'ов.

Правила:

- Изменение baseline требует review как изменение UI.
- Если текст или данные динамические, область маскируется или проверяется структурно.
- Если изменение намеренное, baseline обновляется вместе с PR.
- Если изменение не намеренное, фиксится UI.

## Селекторы и DOM Contract

Тесты должны опираться на публичный DOM/accessibility contract:

- `data-testid` для крупных экранов и блоков;
- `data-state` для loading/ready/empty/error/locked;
- `data-status` для domain status;
- `aria-current`, `aria-expanded`, `aria-busy`, `aria-invalid`;
- `role="status"`, `role="alert"`, `role="dialog"`;
- `getByRole(...)` и accessible names для кнопок/ссылок.

Не использовать CSS-классы как основной selector.

Пример:

```ts
await expect(page.getByTestId("today-screen")).toBeVisible()
await expect(page.getByTestId("today-summary")).toHaveAttribute("data-status", "calm")
await expect(page.getByRole("button", { name: "Подробнее" })).toHaveAttribute("aria-expanded", "false")
```

## 3001 Mock Preview

`/opt/solarsage-astro-mock-preview` на port `3001` может использоваться временно как visual oracle во время переноса UI.

Это не постоянная архитектура.

После переноса внешний вид должен фиксироваться в:

- contract-valid fixtures;
- Playwright screenshots;
- structural assertions;
- real e2e.

`3001 mock-preview` можно выключить после того, как baseline и real e2e покрывают перенесённые экраны.

## Команды

Текущий Playwright config использует `E2E_BASE_URL` и проекты `chromium` / `mobile`.

Реальный e2e:

```bash
E2E_BASE_URL=http://localhost:3002 pnpm exec playwright test --project=chromium
```

Mock visual/parity e2e должен быть добавлен как отдельный Playwright project/spec. До появления отдельного package script запускать его напрямую:

```bash
E2E_BASE_URL=http://localhost:3002 pnpm exec playwright test e2e/mock-visual.spec.ts --project=chromium
```

Обновление snapshots после намеренного UI-изменения:

```bash
E2E_BASE_URL=http://localhost:3002 pnpm exec playwright test e2e/mock-visual.spec.ts --project=chromium --update-snapshots
```

## Troubleshooting

### Шрифты или ассеты не успели загрузиться

```ts
await page.waitForLoadState("networkidle")
```

### Анимации дают шум

```ts
await page.addStyleTag({
  content: "* { animation: none !important; transition: none !important; }",
})
```

### Динамический контент ломает diff

Использовать mock fixture, mask или structural assertion.

```ts
await expect(page).toHaveScreenshot("today.png", {
  mask: [page.getByTestId("today-reading-text")],
})
```

## Acceptance Rule

Visual regression считается достаточным только вместе с другими gates:

```text
unit/component tests
+ contract tests
+ mock visual/structural e2e
+ real e2e
+ no-runtime-mocks guardrail
```
