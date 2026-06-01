# Visual Regression Testing

## Что это?

Visual Regression Testing автоматически обнаруживает визуальные изменения (CSS, layout, rendering) путём сравнения скриншотов.

## Как работает?

1. **Baseline** — первый запуск создаёт эталонные скриншоты
2. **Comparison** — последующие запуски сравнивают новые скриншоты с baseline
3. **Diff** — если есть разница > threshold, тест падает

## Команды

### Запустить тесты
```bash
npm run test:visual
```

### Обновить baseline (после намеренных изменений)
```bash
npm run test:visual:update
```

### Запустить в UI mode (для отладки)
```bash
npm run test:visual:ui
```

## Когда обновлять baseline?

- После намеренных изменений дизайна
- После обновления UI библиотек
- После изменения layout

## Workflow

1. Делаешь изменения в CSS/компонентах
2. Запускаешь `npm run test:visual`
3. Если тест падает:
   - Проверяешь diff в `e2e/**/*-diff.png`
   - Если изменения намеренные → `npm run test:visual:update`
   - Если изменения НЕ намеренные → исправляешь код

## Примеры

### Тест падает из-за изменения цвета кнопки
```
Expected: button color #3B82F6
Actual: button color #EF4444
Diff: 150 pixels (threshold: 100)
```

→ Проверяешь diff → если намеренно изменил цвет → обновляешь baseline

### Тест падает из-за бага (CSS не загрузился)
```
Expected: styled page
Actual: unstyled page (no CSS)
Diff: 5000 pixels
```

→ Исправляешь баг → тест проходит

## Покрытие тестами

### Homepage
- Loading state (авторизация)

### Onboarding
- Step 1: Welcome screen
- Step 2: Birth date input
- Step 3: Birth place picker

### Day View
- Locked state (paywall)
- Unlocked state (content visible)

### Monetization
- Trial banner

## Конфигурация

### Viewport
- iPhone SE (375x667) — основной мобильный viewport

### Thresholds
- `maxDiffPixels: 100` — максимум 100 пикселей разницы
- `threshold: 0.2` — 20% допустимой разницы

### Screenshot Storage
- Baseline: `e2e/**/*.spec.ts-snapshots/`
- Diffs: `e2e/**/*-diff.png` (только при падении теста)

## CI/CD Integration

Visual regression тесты запускаются автоматически на каждом PR:
- `.github/workflows/visual-regression.yml`
- При падении теста diff-изображения загружаются как artifacts

## Troubleshooting

### Тест падает из-за шрифтов
Убедись, что шрифты загружены перед скриншотом:
```typescript
await page.waitForLoadState('networkidle')
```

### Тест падает из-за анимаций
Отключи анимации в тесте:
```typescript
await page.addStyleTag({
  content: '* { animation: none !important; transition: none !important; }'
})
```

### Тест падает из-за динамического контента
Замокай динамический контент (даты, случайные данные):
```typescript
await page.route('**/api/data', route => {
  route.fulfill({ body: JSON.stringify({ date: '2026-06-01' }) })
})
```

## Best Practices

1. **Стабильные селекторы** — используй `data-testid` вместо текста
2. **Фиксированные данные** — мокай API для предсказуемых результатов
3. **Ожидание загрузки** — всегда жди `networkidle` перед скриншотом
4. **Минимальные thresholds** — держи `maxDiffPixels` как можно ниже
5. **Регулярное обновление** — обновляй baseline после каждого дизайн-изменения

## Расширение покрытия

Чтобы добавить новый visual regression тест:

1. Добавь тест в `e2e/visual-regression.spec.ts`
2. Запусти `npm run test:visual:update` для создания baseline
3. Проверь скриншот в `e2e/**/*.spec.ts-snapshots/`
4. Закоммить baseline в git

Пример:
```typescript
test('new feature - initial state', async ({ page }) => {
  await page.goto('/new-feature')
  await page.waitForLoadState('networkidle')
  
  await expect(page).toHaveScreenshot('new-feature-initial.png', {
    maxDiffPixels: 100,
  })
})
```
