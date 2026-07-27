# S2 TZ: навигатор сфер — премиальные строки, топ-3 + «все сферы», без чипов

Дата: 2026-07-27
Phase / Wave: **W-TODAY-PREMIUM-FIRST-SCREEN**, волна W1, срез S2
Master: `docs/work/2026-07-27_today-premium-first-screen/00_MASTER_TZ.md` (решения D1–D8, особенно D2)
Modules: `M-TODAY-CONCRETE-DAY-ADVICE`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Goal (один наблюдаемый результат)

Блок «Конкретно сегодня» становится премиальным списком «Где проявится
сегодня»: одноколоночные строки (иконка + название сферы + шеврон), по
умолчанию видны первые 3 строки, остальные — за кнопкой «Все N сфер».
Вердикт-чипы («Поддержка»/«Требует внимания»/«Лучше отложить»/«Ровный фон»)
и цветные точки **убраны полностью** (решение D2 — возвращутся в W3 на
честной valence). Раскрытие строки показывает детали сферы без вердикт-бейджа.

Визуальный ориентир строк: макет
`docs/work/2026-07-11_solarsage-v2-three-horizon-why-preview/assets/03-full-day-three-horizons-mobile.png`
(зона «Где проявится сегодня», ~y 1450–1900 оригинала).

## 2. Exact write scope

- `components/today/concrete-day-advice.tsx` — новая композиция блока.
- `__tests__/components/TodayScreen.v2-downstream.test.tsx` — синхронизация.
- `__tests__/components/TodayScreen.test.tsx` — синхронизация, если ломается.
- `e2e/mock-visual/day.spec.ts`, `e2e/mock-visual/day-v2.spec.ts` — только
  если ломаются существующие селекторы/ожидания.

## 3. Frozen / out-of-scope

- `today-screen.tsx`, `day-summary-card.tsx`, `day-collapsible.tsx`,
  `why-expanded.tsx`, `activation-evidence-card.tsx` и всё остальное.
- Backend, `lib/contracts`, `lib/adapters`.
- `lib/presentation/today-v2.ts` — кроме НИЧЕГО; если очень нужно —
  escalation.
- Новые цвета/тени/шрифты сверх описанного в §4 (полная визуальная система —
  S3).

## 4. Требования

### Композиция блока

- Eyebrow: «Конкретно сегодня» (как сейчас).
- Заголовок: **«Где проявится сегодня»** (заменяет «Быстрый навигатор по
  12 сферам»), serif, как сейчас.
- Одна колонка строк. Каждая строка — нативный `<button type="button">`
  на всю ширину: иконка в tinted squircle (нейтральный violet-shell для всех,
  без verdict-цветов) → название сферы (semibold) → chevron вправо
  (`ChevronRight`) когда закрыто / `ChevronDown` когда открыто.
  min-h 64px, radius 16–20px, hairline border, hover — мягкий violet tint.
- По умолчанию рендерятся первые 3 строки в canonical adapter order
  (порядок НЕ менять, не пересортировывать).
- Если строк > 3 — под списком кнопка «Все N сфер» (N = общее число строк),
  `data-testid="concrete-day-advice-show-all"`, `aria-expanded`, по клику
  показывает все строки и превращается в «Свернуть».
- Раскрытая детальная панель (как сейчас, одна на экран): заголовок сферы,
  «Что может проявиться», «Что поможет», плашка «основано на личной карте»,
  CTA «Почему это про меня», «Свернуть». **Убрать**: вердикт-бейдж
  (`concrete-day-advice-details-status`) и блок «Что может проявиться» оставить
  с текстом `getVerdictManifestationCopy`? — НЕТ: см. следующий пункт.

### Удаление вердиктов (D2)

- Удалить `CONCRETE_ADVICE_VERDICT_PRESENTATION`, `normalizeConcreteAdviceVerdict`,
  compact status строку в кнопках (`concrete-day-advice-row-status`), цветные
  точки, вердикт-бейдж в деталях.
- Текст «Что может проявиться» из `getVerdictManifestationCopy(row.verdict)`
  построен на вердикте — этот подблок тоже удалить; в деталях остаются:
  заголовок, «Что поможет» (row.text), плашка про личную карту, CTA.
- `data-status` на строках/деталях больше НЕ ставить (вернётся в W3).
- Экспорт `normalizeConcreteAdviceVerdict` удаляется — проверить импорты
  (grep по репо) и удалить связанные тесты.

### Сохранить (must-preserve)

- `data-testid="concrete-day-advice"` на секции, `concrete-day-advice-row`
  на каждой строке, `data-sphere-key`, `concrete-day-advice-details`,
  `sphere-why-cta`.
- Controlled selection: `selectedKey`/`onSelectedKeyChange` контракт не меняется;
  одна открытая деталь; повторный клик по строке закрывает её.
- `aria-expanded`/`aria-controls` на строках; деталь — `role="region"`.
- Каждая полученная строка рендерится (после «Все N сфер») — ничего не
  скрывается окончательно, порядок backend сохраняется.
- GRACE-разметка файла обновлена под новую семантику блока.

## 5. Must-preserve извне

- TodayScreen scroll/focus навигация (`concrete-day-advice-row[data-sphere-key]`)
  и поведение «Почему это про меня».
- e2e-контракт: строки видимы, детали по клику; существующие e2e, использующие
  `concrete-day-advice-row`, должны продолжать проходить (кроме ожиданий
  вердикт-статусов — их синхронизировать).

## 6. Verification (одна targeted-команда)

```bash
npx vitest run __tests__/components/TodayScreen.v2-downstream.test.tsx __tests__/components/TodayScreen.test.tsx
```

## 7. Expected evidence

- Список файлов, краткий diff-вывод, полный вывод verification.
- Список удалённых вердикт-сущностей и затронутых тестов.

## 8. Escalation rule

Нужен файл вне §2 (например, правка today-v2.ts или других компонентов) —
стоп, доложить, ждать новый packet. Ничего не коммить и не пушить.
