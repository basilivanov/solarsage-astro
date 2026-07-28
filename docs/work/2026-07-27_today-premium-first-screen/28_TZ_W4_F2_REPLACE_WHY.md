# W4-F2 TZ: замена «Почему так у меня» на TodayFocus + счётчик-ссылка на факторы

Дата: 2026-07-28
Phase / Wave: **W4-TODAY-CONVERGENCE**, срез F2 (frontend)
Решение владельца (2026-07-28): блок «Почему так у меня» (teasers + horizon
modals) заменяется TodayFocus; долгий фон — в свёрнутый disclosure
«Контекст периода»; счётчик «0N ▸» — кнопка в disclosure со всеми факторами.
Modules: `M-TODAY-TODAY-SCREEN`, `M-TODAY-FOCUS-CARD`, `M-ACTIVATION-EVIDENCE-CARD`, `M-TODAY-SPHERE-DETAILS-SHEET`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Goal

- why-блок (`why-expanded.tsx` + тизеры + `horizon-sheet.tsx`) УДАЛЯЕТСЯ с
  экрана Дня (компоненты не удалять из репо — убрать из композиции).
- CTA «Почему так у меня» убирается из сторис-карты и модалки сферы.
- Новый disclosure «Контекст периода» с долгим горизонтом (из
  `payload.v2.horizons` items[long]).
- Счётчик факторов «0N ▸» в eyebrow фокус-блока — кнопка с aria-expanded,
  открывающая technical disclosure фокуса, где перечислены ВСЕ факторы
  схождения с ролями (якорь сегодня / фон).

## 2. Exact write scope

- `components/today/today-screen.tsx` — убрать WhyExpanded из композиции и
  связанный state/handlers (whyOpen/openWhy/deeplink ?why=1 теперь ведёт на
  фокус-блок scroll+expand его disclosure); добавить «Контекст периода»
  disclosure (DayCollapsible) с рендером long-горизонта (те же части, что в
  horizon-sheet: eyebrow+title+tone, summary+plainExplanation, timing,
  manifestations, actions) — переиспользовать существующие подкомпоненты
  horizon-sheet БЕЗ модалки.
- `components/today/activation-evidence-card.tsx` — удалить
  `personal-story-why-cta` и prop onWhyOpen.
- `components/today/sphere-details-sheet.tsx` — удалить `sphere-why-cta` и
  prop onWhyOpen.
- `components/today/today-focus.tsx` — счётчик «0N ▸» как button:
  `data-testid="today-focus-factor-toggle"`, aria-expanded/aria-controls,
  открывает `today-focus-technical-content`; в content — список ВСЕХ
  факторов схождения: для каждого — technical title + роль
  («сегодня» якорь с временем / «фон»), данные из
  `convergence.sourceActivationIds` + lookup в `payload.v2.activationEvidence`
  (там есть titles; если id не найден — безопасно скрыть строку).
- Тесты: `__tests__/components/TodayFocus.test.tsx` (счётчик-кнопка,
  disclosure факторов), `__tests__/components/TodayScreen.test.tsx`,
  `__tests__/components/TodayScreen.v2-downstream.test.tsx`,
  `__tests__/components/ActivationEvidenceCard.personal.test.tsx` — убрать
  ожидания why-блока/CTA, добавить «Контекст периода» и фокус.
- e2e: `e2e/mock-visual/day.spec.ts`, `e2e/mock-visual/day-v2.spec.ts` —
  синхронизация (why-expanded/тизеры/CTA удалены из ожиданий; фокус-блок
  добавлен в порядок секций).

## 3. Frozen / out-of-scope

- Backend, payload, today-focus.tsx остальная логика.
- Удаление файлов why-expanded.tsx/horizon-sheet.tsx/why-time-horizon-card.tsx
  (решение ревьюера позже).
- «Все сферы дня», disclosures «Полный разбор»/«Как это рассчитано».

## 4. Must-preserve

- Порядок экрана: статус → TodayFocus → сторис → Все сферы → «Контекст
  периода» → disclosures → footer.
- Все существующие testid сохраняющихся блоков; новые:
  `today-focus-factor-toggle`, `day-context-disclosure` (+`-toggle/-region`
  по DayCollapsible контракту).
- Deeplink ?why=1 не 404 и не ломает экран (scroll к фокусу).
- Banned-жаргон в human-частях не появляется.

## 5. Verification

```bash
npx vitest run __tests__/components/TodayFocus.test.tsx __tests__/components/TodayScreen.test.tsx __tests__/components/TodayScreen.v2-downstream.test.tsx __tests__/components/ActivationEvidenceCard.personal.test.tsx
```

## 6. Expected evidence

- Файлы, вывод verification, список удалённых из композиции элементов и
  обновлённых e2e-ожиданий.

## 7. Escalation rule

Нужен файл вне §2 — стоп, доложить. Ничего не коммить и не пушить.
