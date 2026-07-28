# 33 TZ W6-S3 — TodayFocus Frontend Migration (F1) — frontend slice

1. **Packet title**: W6-S3-FOCUS-FRONTEND-MIGRATION
2. **Phase / Wave**: W6-FOCUS-HARDENING, срез S3 (frontend). Normative source:
   `28_TZ_W4_F1_TODAY_FOCUS_FRONTEND_MIGRATION.md` (далее «doc 28») — обязателен.
   Зависит от W6-S1 (canonical selected events с provenance уже в main).
3. **Modules**: M-TODAY-FOCUS, M-TODAY-SCREEN, M-ADAPTERS-TODAY-PAYLOAD.
4. **Goal**: фронтенд полностью соответствует doc 28: один story-slot для
   focus-сюжета, стабильные machine-attributes для тестов (`data-event-id`,
   `data-event-kind`, `data-event-relation`), корректный null-time рендер,
   adapter parity без fallback, controlled legacy branch.

## Текущее состояние (зафиксировано ревьюером, не переделывать)

- `TodayFocusCard` уже рендерится из `payload.focus` и стоит после списка сфер;
  «Почему так у меня» удалён; `today-focus-event` строки — кнопки с
  drilldown-модалкой (W5). ЭТО БАЗА, не parallel implementation.
- `data-testid="today-focus"`, `data-state`, `data-content-state` уже есть.
- `lib/adapters/today-payload.ts` уже прокидывает `focus` (проверить parity
  тестом, не переписывать).

## 5. Exact write scope

- `components/today/today-focus.tsx` — добавить `data-event-id`,
  `data-event-relation` на event rows (kind уже есть); null `occursAt` — строка
  без часов (никакого `00:00`), всегда после timed rows ТОЛЬКО если backend так
  отдал (клиент НЕ пересортировывает — doc 28 §6).
- `lib/presentation/today-focus-relation.ts` (НОВЫЙ, маленький pure helper) —
  relation из provenance partition (doc 28 §5.1): intersection
  `event.sourceActivationIds` ∩ `focus.convergence.sourceActivationIds` →
  `convergence_event`, иначе `independent_event`; для `single_impulses` всегда
  `independent_event`.
- `components/today/today-screen.tsx` — story-slot routing по таблице doc 28
  §3.2: `focus != null` → TodayFocusCard единственный focus-story;
  `focus == null` → controlled legacy `ActivationEvidenceCard`.
  ВАЖНО: сейчас `ActivationEvidenceCard` (v2 story) рендерится ВСЕГДА под
  summary. Провести audit: если он показывает конкурирующий сюжет/headline —
  перевести в legacy branch (рендерить только при `focus == null`). Если его
  содержимое НЕ конкурирует (детальный v2-разбор, не «сюжет дня») — оставить,
  но зафиксировать решение в отчёте с обоснованием по doc 28 §3.2.
- `__tests__/components/TodayFocus.test.tsx` — атрибуты id/relation/kind,
  null-time без fake time, relation partition для single_impulses.
- `__tests__/lib/adapt-payload.test.ts` и/или
  `__tests__/contracts/today-fixture-roundtrip.test.ts` — adapter parity:
  focus passthrough без пересчёта/сортировки/fallback; невалидный focus →
  contract error, НЕ activationSummary substitution (doc 28 §3.1).
- `__tests__/components/TodayScreen.test.tsx` — branch matrix: focus!=null /
  focus==null / contentState=unavailable (doc 28 §8 п.2-3).

## 6. Frozen / Out of scope

- Backend, wire schema, generated contracts — не трогать.
- `focus-event-sheet.tsx` (W5 drilldown) — не менять; relation атрибуты на
  event rows не ломают его (он открывается по onEventSelect).
- Удаление legacy `ActivationEvidenceCard` и его API-полей — НЕ этот срез
  (doc 28 §3.2: только routing, удаление после consumer audit).
- Никакого client ranking/sort events, никакого fallback-copy, второго
  headline (doc 28 §10).
- Visual baselines: обновление только если реально изменился рендер и после
  глазной проверки ревьюера.

## 7. Must-preserve invariants

- `npx vitest run` зелёный; `npx tsc --noEmit` 0 ошибок.
- e2e day suite зелёный после ребилда (гейт делает ревьюер).
- Существующие data-testid (`today-focus-event`, `today-featured-sphere`,
  `today-focus-technical-*`, `focus-event-sheet`) не ломаются.
- relation — presentation-only helper, НЕ client ranking (doc 28 §5.1).

## 8. Verification

```bash
npx vitest run __tests__/components/TodayFocus.test.tsx __tests__/components/TodayScreen.test.tsx __tests__/lib/adapt-payload.test.ts __tests__/contracts/today-fixture-roundtrip.test.ts && npx tsc --noEmit -p tsconfig.json
```

## 9. Expected evidence

Diff, вывод verification, таблица payload→render branch (4 строки doc 28 §3.2),
решение по ActivationEvidenceCard с обоснованием, accessibility-примечание
(icon-only controls aria-label), git diff --stat.

## 10. Escalation

Нужен wire relation field, client sort, удаление legacy API, изменение
wire schema — стоп, доклад (doc 28 §10).

## 11. No-commit

Ничего не коммитить и не пушить — коммит делает ревьюер.
