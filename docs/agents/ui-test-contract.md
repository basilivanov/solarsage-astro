# UI Semantic/Test Contract

> Часть operative canon репозитория (вместе с AGENTS.md и `docs/agents/*`).
> Извлечено из AGENTS.md 2026-10-22; AGENTS.md содержит резюме и ссылку на этот файл.
> Обращаться сюда перед: созданием/правкой экранов и интерактивных блоков,
> написанием e2e/unit тестов UI, переименованием любого `data-testid`.

Фронтенд должен быть написан так, чтобы пользователь, accessibility tree и headless-тест видели один и тот же публичный UI-контракт. Тесты не должны зависеть от CSS-классов, React internals или случайного текста LLM.

## Обязательные правила для экранов и интерактивных блоков

- Каждый крупный экран имеет стабильный root selector: `data-testid="today-screen"`, `calendar-screen`, `profile-screen`, `readings-screen`, `horary-screen`, `natal-screen`.
- Крупные повторяемые блоки имеют стабильные `data-testid`: карточки, строки календаря, CTA, paywall, loading/error/empty states.
- Состояния, важные для UI и тестов, отражаются в DOM:
  - для экранов и блоков вне нового Today:
    `data-state="loading|ready|empty|error|locked|disabled"`
  - для нового Today: `data-state="convergence_today|quiet_day|unavailable"`,
    `data-screen-state="loading|ready|error"`,
    `data-day-tone="steady|supportive|mixed|tense"`,
    `data-content-state="ready|pending|unavailable|not_needed"`,
    `data-access-state="full|preview|locked"` и
    `data-birth-time-mode="exact|bucket|unknown"`
  - старый Today `data-status="calm|tense|favorable|neutral"` superseded и не
    используется новым экраном; для остальных экранов действует их собственный
    контрактный enum
  - `disabled`, `aria-disabled`, `aria-busy`, `aria-pressed`, `aria-expanded`, `aria-current`, `aria-selected`
- Icon-only buttons обязательно имеют `aria-label`.
- Табы и основная навигация используют `nav`, `aria-label`, `aria-current="page"` или `aria-selected`.
- Формы используют реальные `label`, `aria-invalid`, `aria-describedby`; placeholder не считается label.
- Loading state использует `role="status"` и/или `aria-busy`; error state использует `role="alert"`; modal/sheet использует `role="dialog"` и `aria-modal`.
- Для accordion/disclosure обязательно отражать состояние через `aria-expanded` и связанный `aria-controls`, если есть раскрываемая область.
- Динамические тексты от API/LLM не должны быть единственной опорой теста; рядом нужен стабильный structural selector или state attribute.
- `data-testid` — это публичный test contract. Не переименовывать без обновления e2e/unit тестов и миграционной причины.

## Тестовая стратегия для UI

- Mock/fixture e2e через Playwright `page.route('/api/**', ...)` допустим только как test-only слой. Он проверяет visual/structural contract фронта на стабильных payload'ах.
- Real e2e всегда идёт без route interception: Telegram HMAC → реальный API → реальные данные.
- Visual regression baseline использовать дозировано: ключевые экраны и состояния (`day`, `calendar`, `profile`, `readings`, `horary`, `natal`, `locked`, `empty`, `error`, `generating`). Динамические текстовые зоны маскировать или проверять структурно.
- Production runtime не должен импортировать `lib/mocks/*`, `lib/demo-data.ts` или demo/mock API. Моки живут в test harness, fixtures и старом visual reference, но не в product path.

Пример контракта:

```tsx
<section
  data-testid="today-screen"
  data-screen-state={screenState}
  data-state={state}
  data-day-tone={dayTone ?? undefined}
  data-content-state={contentState}
  data-access-state={access.state}
  data-birth-time-mode={birthTime.mode}
>
  <button
    type="button"
    aria-expanded={open}
    aria-controls="today-calculation-details"
  >
    Как это рассчитано
  </button>
</section>
```

Тест должен обращаться к публичному DOM-контракту:

```ts
await expect(page.getByTestId("today-screen")).toHaveAttribute("data-state", "quiet_day")
await expect(page.getByTestId("today-screen")).toHaveAttribute("data-screen-state", "ready")
await expect(page.getByTestId("today-screen")).toHaveAttribute("data-day-tone", "steady")
await expect(page.getByRole("button", { name: "Как это рассчитано" })).toHaveAttribute("aria-expanded", "false")
```
