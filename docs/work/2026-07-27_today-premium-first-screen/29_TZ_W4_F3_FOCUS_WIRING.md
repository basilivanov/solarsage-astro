# W4-F3 TZ: «Что сошлось» вниз экрана + связка featured-сфер через модалку

Дата: 2026-07-28
Phase / Wave: **W4-TODAY-CONVERGENCE**, срез F3 (frontend)
Решение владельца (2026-07-28, финальная модель):
```text
1. Статус + зона
2. ИМЕННО ДЛЯ ТЕБЯ
3. Все сферы дня
4. «Что сошлось именно сегодня»  ← блок ПЕРЕМЕЩАЕТСЯ СЮДА (в конец, как «Почему»)
5. «Контекст периода» (disclosure)
6. «Полный разбор дня» / «Как это рассчитано» (disclosures)
```
Featured-сфера в модалке получает «Почему сегодня» + ссылку-скролл к блоку;
не-featured — ничего нового. Disclosure фокуса — все факторы с ролями.
Modules: `M-TODAY-TODAY-SCREEN`, `M-TODAY-FOCUS-CARD`, `M-TODAY-SPHERE-DETAILS-SHEET`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Goal

- TodayFocus перемещается из позиции после статуса в позицию после
  «Все сферы дня» (перед «Контекст периода»).
- Модалка featured-сферы: секция «Почему сегодня» (summary + action из
  `focus.featuredSpheres[key]`) + ссылка «Всё схождение дня ↓» —
  закрыть модалку и smooth-scroll к `today-focus` с временной подсветкой.
- Модалка не-featured сферы: без изменений (пустых ссылок нет).
- Technical disclosure фокуса: ВСЕ факторы схождения с ролями
  (якорь сегодня со временем / фон), не только 3 события.

## 2. Exact write scope

- `components/today/today-screen.tsx` — перестановка TodayFocus после
  ConcreteDayAdvice; в SphereDetailsSheet прокинуть
  `featured={payload.focus?.featuredSpheres?.find(s => s.key === selectedRowKey) ?? null}`
  и `onFocusOpen` (закрыть sheet + scrollTo `[data-testid="today-focus"]`
  + временная ring-подсветка ~1.2s).
- `components/today/sphere-details-sheet.tsx` — новая секция
  «Почему сегодня» (`data-testid="sphere-focus-section"`): заголовок,
  summary (muted), action (императивная строка), ссылка
  «Всё схождение дня ↓» (`data-testid="sphere-focus-link"`, вызывает
  onFocusOpen). Рендерится ТОЛЬКО при featured != null; при
  contentState != ready — секция скрыта (не показывать пустые поля).
- `components/today/today-focus.tsx` — `today-focus-technical-content`:
  список факторов схождения: события (уже есть, с временем) + остальные
  `convergence.sourceActivationIds` без события — каждая строка:
  technical title (lookup в `payload.v2.activationEvidence` по id через
  prop `activationEvidence`) + бейдж «фон»; недостающие id скрывать.
- Тесты: `__tests__/components/TodayFocus.test.tsx` (полный disclosure),
  `__tests__/components/TodayScreen.test.tsx` (новый порядок секций,
  featured-прокидывание, onFocusOpen scroll), sheet-тесты в
  `__tests__/components/TodayScreen.v2-downstream.test.tsx`.
- e2e: `e2e/mock-visual/day.spec.ts`, `e2e/mock-visual/day-v2.spec.ts` —
  новый порядок секций (focus после concrete-day-advice, перед
  day-context-disclosure), секция «Почему сегодня» в sheet у featured,
  её отсутствие у не-featured.

## 3. Frozen / out-of-scope

- Backend, payload (всё уже есть).
- Визуальная система остального экрана; why-возвраты (мёртво).
- Модалка сферы в остальном (story/why/advice не трогать).

## 4. Must-preserve

- Порядок секций из §«Решение владельца» выше; e2e sectionOrder совпадает.
- `data-testid`: новые `sphere-focus-section`, `sphere-focus-link`,
  `today-focus-factor-item`; существующие не меняются.
- Ссылка-скролл доступна клавиатурой (button, focus-visible ring).
- featured-рендеринг строго из payload (нет клиентского ranking).

## 5. Verification

```bash
npx vitest run __tests__/components/TodayFocus.test.tsx __tests__/components/TodayScreen.test.tsx __tests__/components/TodayScreen.v2-downstream.test.tsx
```

## 6. Expected evidence

- Файлы, вывод verification, обновлённый e2e sectionOrder.

## 7. Escalation rule

Нужен файл вне §2 — стоп, доложить. Ничего не коммить и не пушить.
