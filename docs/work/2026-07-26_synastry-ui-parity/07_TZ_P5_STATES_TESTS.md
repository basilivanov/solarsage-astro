# 07_TZ (P5): Синастрия — states, форма добавления, финальные тесты (Этап 5)

## 1. Packet title
Synastry UI parity, срез P5: generation/processing/error/empty states, add-sheet визуальная доводка, финальный visual/e2e прогон. Зависит от P1-P4.

## 2. Phase / Wave
W-SYNASTRY-MVP, parity wave. Master TZ §13, §14, §20, §21 (критерии приёмки — финальный чек-лист), §15.

## 3. Modules
- Frontend: `components/synastry/synastry-add-sheet.tsx`, `components/synastry/synastry-detail-screen.tsx` (processing state), `components/synastry/synastry-screen.tsx` (empty states)
- Tests: `__tests__/synastry/*`, `e2e/mock-visual/synastry*.spec.ts`

## 4. Goal

1. **Processing state §14.1-14.2**: вместо голого spinner на detail — staged loader «Строим карту взаимодействия» со стадиями из status (`✓ Сопоставили планеты / • Рассчитываем аспекты / • Готовим человеческий перевод`, маппинг state/stage); после создания партнёра — переход в processing screen, poll `/{partner_id}/status` до ready/failed, остановка polling при unmount; failed → retry/error state.
2. **Error copy §14.3**: все пользовательские fallback-сообщения на русском (убрать английские `Failed to ...` из видимых состояний synastry-компонентов).
3. **Empty states §14.4**: различать пустой аккаунт (copy «Добавь первого человека…») и пустой поиск/фильтр («По этому имени никого нет» + сброс).
4. **Add sheet §13**: header без Sparkles («НОВОЕ СРАВНЕНИЕ» / «Добавить человека»); порядок полей §13.2; max-height 92dvh + внутренний scroll + safe-area; CTA «Построить синастрию» / loading «Сохраняем данные…»; unknown-time notice copy §13.4; после success → processing state (не пустой detail).
5. **Финальный visual прогон §21**: обновить/добавить snapshots (list, detail, drilldown, processing, empty, approximate); сверить с proto-*.png из этой папки; прогнать полный чек-лист §21 (Список/Detail/Drill-down/Approximate/Quality).

## 5. Exact write scope
- `components/synastry/synastry-add-sheet.tsx`
- `components/synastry/synastry-detail-screen.tsx` (только processing/error states)
- `components/synastry/synastry-screen.tsx` (только empty states)
- `__tests__/synastry/*` (новые кейсы states)
- `e2e/mock-visual/synastry.spec.ts`, `e2e/mock-visual/synastry-detail.spec.ts` + snapshots

## 6. Frozen / Out of scope
- Backend — не трогать (status endpoint уже есть).
- Wheel/drilldown/list/detail композиция (приняты в P1-P4) — только states, без редизайна.
- `app/(grace)/synastry/page.tsx` — только если нужен переход в processing (минимально).

## 7. Must-preserve invariants
- Все принятые ранее экраны визуально не регрессируют (snapshots P1-P3 обновлять только при states-изменениях).
- Polling останавливается при unmount (no state update after unmount).
- a11y staged loader: role=status, aria-live polite.
- GRACE-разметка; все тесты зелёные.

## 8. Verification commands
```bash
npx vitest run __tests__/synastry
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/
```

## 9. Expected evidence
- `git diff --name-only` — только файлы из scope.
- Вывод проверок; список snapshots; явное прохождение чек-листа §21 по пунктам.

## 10. Escalation rule
Нужен backend/редизайн принятых экранов → стоп, доложить.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
