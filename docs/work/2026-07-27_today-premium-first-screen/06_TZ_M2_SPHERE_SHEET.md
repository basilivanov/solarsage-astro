# M2 TZ: модалка детали сферы (BottomSheet, мгновенно из payload)

Дата: 2026-07-27
Phase / Wave: **W-TODAY-SPHERE-WHY-MODALS**, срез M2 (frontend)
Зависимость: M1 (поле `concreteAdvice.rows[].details`) — если M1 ещё не в main,
модалка обязана корректно работать и без details (fallback-режим).
Modules: `M-TODAY-CONCRETE-DAY-ADVICE`, новый `M-TODAY-SPHERE-DETAILS-SHEET`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Goal (один наблюдаемый результат)

Тап по строке сферы открывает **премиальную bottom-sheet модалку** с
персональным разбором сферы, мгновенно (данные уже в payload, ноль
дозапросов). Инлайн-раскрытие деталей в потоке удаляется. Никакого бейджа
«Объяснение основано на вашей личной карте».

## 2. Exact write scope

- `components/today/sphere-details-sheet.tsx` — **новый** компонент модалки.
- `components/today/concrete-day-advice.tsx` — строки открывают модалку
  (вызывают onSelectedKeyChange как сейчас), инлайн SphereDetails удаляется.
- `components/today/today-screen.tsx` — рендер SphereDetailsSheet по
  selectedKey; `scrollAndFocusSphere` и его effect удалить (модалка сама
  фокусируется); deeplink-поведение `?why=1` не трогать.
- `components/today/activation-evidence-card.tsx` — ranked-ссылки сфер
  ведут в ту же модалку (поведение onSphereSelect сохраняется).
- Тесты: `__tests__/components/ConcreteDayAdvice.keyboard.test.tsx`,
  `__tests__/components/TodayScreen.test.tsx`,
  `__tests__/components/TodayScreen.v2-downstream.test.tsx` — синхронизация.
- e2e: `e2e/mock-visual/day.spec.ts`, `e2e/mock-visual/day-v2.spec.ts`,
  `e2e/dev-visible-sphere-status.spec.ts` — синхронизация селекторов.

## 3. Frozen / out-of-scope

- Backend, lib/contracts (поле details читать опционально `row.details ?? null`;
  контракт TS-типа обновить в `lib/contracts/today.ts` ТОЛЬКО аддитивно:
  `details?: { story: string; why: string[]; advice: string } | null`).
- `why-expanded.tsx`, `why-time-horizon-card.tsx` (это M3).
- Визуальная система строк (уже принята) — не трогать.

## 4. Модалка — требования

Использовать существующий примитив `components/ui/sheet.tsx` (Radix Dialog,
side="bottom"). Если его API не покрывает — escalation, не писать свой
диалог с нуля.

- `role="dialog"`, `aria-modal`, `aria-labelledby` на заголовок сферы;
  Escape и свайп-оверлей закрывают; фокус внутри при открытии.
- Скругление верха 24px, grabber-полоска, max-height ~85dvh, внутренний
  скролл контента (`overflow-y-auto`), премиальная анимация появления
  (из sheet.tsx) + backdrop.
- `data-testid="sphere-details-sheet"`, `data-sphere-key`.
- Мгновенность: контент рендерится из props, без fetch/loading-состояний.

### Контент модалки (порядок строгий)

1. Иконка сферы в squircle + заголовок сферы (serif 24px).
2. **story** (details.story, 2–3 предложения) — основной текст 15px relaxed.
3. Секция **«Что за этим стоит»** — строки details.why (каждая с мягким
   маркером). НИГДЕ не использовать фразу «Почему именно у тебя».
4. Секция **«Что поможет»** — details.advice (или row.text, см. fallback).
5. Кнопка «Почему так у меня» (существующий onWhyOpen) + «Закрыть».

### Fallback (старые кеши без details / details === null)

- Пункты 2–3 скрываются; вместо story показывается row.text в секции
  «Что поможет». Никаких пустых заголовков секций.

## 5. Must-preserve

- `data-testid="concrete-day-advice-row"`, `data-sphere-key`, aria-expanded
  НЕ требуется на строках (модаль, не аккордеон) — заменить на
  `aria-haspopup="dialog"`; обновить связанные тесты.
- Одна модалка; повторный тап по той же строке открывает её же (не toggle-close).
- Поведение «Почему так у меня» CTA (openWhy) сохраняется.
- Все остальные testid экрана нетронуты.

## 6. Verification (одна targeted-команда)

```bash
npx vitest run __tests__/components/ConcreteDayAdvice.keyboard.test.tsx __tests__/components/TodayScreen.test.tsx __tests__/components/TodayScreen.v2-downstream.test.tsx
```

## 7. Expected evidence

- Список файлов, вывод verification, список обновлённых e2e-ожиданий.

## 8. Escalation rule

Sheet-примитив не подходит / нужен файл вне §2 — стоп, доложить. Ничего не
коммить и не пушить.
