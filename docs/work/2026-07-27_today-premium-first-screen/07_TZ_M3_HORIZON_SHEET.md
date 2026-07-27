# M3 TZ: «Почему так у меня» — teaser-карточки + модалки горизонтов

Дата: 2026-07-27
Phase / Wave: **W-TODAY-SPHERE-WHY-MODALS**, срез M3 (frontend)
Modules: `M-TODAY-WHY-EXPANDED`, новый `M-TODAY-HORIZON-SHEET`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Goal (один наблюдаемый результат)

Раскрытый блок «Почему так у меня» больше не портянка: intro + три
teaser-карточки горизонтов (01 Долгий цикл / 02 Текущий период / 03 Быстрый
триггер), каждая открывает bottom-sheet модалку с полным контентом
горизонта. Мгновенно, из уже загруженного payload (v2.horizons), без
дозапросов.

## 2. Exact write scope

- `components/today/horizon-sheet.tsx` — **новый**: модалка одного
  горизонта (на `components/ui/sheet.tsx`, side="bottom").
- `components/today/why-expanded.tsx` — backend-horizons ветка: вместо
  развёрнутых карточек — intro (eyebrow/headline/body как сейчас) + три
  teaser-карточки; state открытой модалки; рендер HorizonSheet.
- `components/today/why-time-horizon-card.tsx` — НЕ удалять файл; если он
  перестаёт использоваться — доложить в отчёте (удаление отдельным
  решением ревьюера).
- Тесты: `__tests__/components/TodayScreen.v2-downstream.test.tsx` —
  синхронизация.
- e2e: `e2e/mock-visual/day-v2.spec.ts` — синхронизация селекторов/скриншотов
  (бейзлайны обновит ревьюер при деплое).

## 3. Frozen / out-of-scope

- `today-screen.tsx`, `sphere-details-sheet.tsx` (M2), `day-summary-card.tsx`.
- Backend, lib/contracts, lib/presentation/today-v2.ts (чтение только).
- Legacy-ветки why-expanded (legacy-v2 / human-only / legacy) — не трогать.

## 4. Требования

### Teaser-карточки (внутри раскрытого why-блока)

- Порядок строго backend order: long → medium → fast.
- Каждая: номер 01/02/03, backend eyebrow дословно, backend title дословно,
  tone-badge (текущая mapping-таблица tone сохраняется), одна строка
  summary (обрезка ~2 строки, line-clamp), chevron.
- `data-testid="why-horizon-teaser"`, `data-horizon="long|medium|fast"`,
  `data-status` (tone enum), `aria-haspopup="dialog"`.
- Интерактивность и визуал — в духе строк сфер (S2/S3 система).

### Модалка горизонта

- `role="dialog"`, `aria-modal`; Escape/оверлей закрывают.
- Контент — полный состав текущей horizon card: eyebrow+title+tone,
  summary + plainExplanation, timing (range/peak/state), manifestations,
  strength/risk, actions (do/avoid), ссылки на сферы (ведут в модалку
  сферы M2 через существующий onSphereSelect — модалка горизонта при этом
  закрывается), внизу закрытый disclosure «Как это рассчитано» (техника,
  как сейчас).
- Внутренний скролл, max-height ~85dvh.
- `data-testid="horizon-sheet"`, `data-horizon`.

### Deeplinks и state

- `?why=1` — как сейчас открывает why-блок (теперь с teasers).
- `?why=1&astro=1` — открывает why-блок; технический disclosure внутри
  модалки НЕ автооткрывается (доложить в отчёте, если это ломает e2e).
- Смена даты — модалка закрывается (существующий reset TodayScreen).

## 5. Must-preserve

- Backend intro eyebrow/headline/body дословно; никаких frontend-authored
  нарративов.
- Запрещённые слова в human-части (транзит/натал/профекция/фирдар/аспект/орб)
  — как в текущем коде, vocabulary guard не ослаблять.
- `data-testid="why-expanded"` и его open/onOpenChange контракт.
- Banned-copy e2e проверки остаются зелёными.

## 6. Verification (одна targeted-команда)

```bash
npx vitest run __tests__/components/TodayScreen.v2-downstream.test.tsx __tests__/components/TodayScreen.test.tsx
```

## 7. Expected evidence

- Список файлов, вывод verification, статус why-time-horizon-card.tsx
  (используется / осиротел), обновлённые e2e-ожидания.

## 8. Escalation rule

Sheet-примитив не подходит / нужен файл вне §2 — стоп, доложить. Ничего не
коммить и не пушить.
