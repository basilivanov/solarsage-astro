# 07_TZ: Синастрия — Frontend screens

## 1. Packet title
Синастрия / Совместимость — Frontend screens (срез 7 из N)

## 2. Phase / Wave
W-SYNASTRY-MVP, slice 7: Frontend screens

## 3. Modules
- components/synastry/* (по одному контракту на файл)

## 4. Goal
Создать frontend screens: synastry list, add sheet, detail, drilldown. Использовать паттерн соседних фич.

## 5. Exact write scope
- `app/(grace)/synastry/page.tsx` — list screen
- `components/synastry/synastry-screen.tsx` — list component
- `components/synastry/synastry-add-sheet.tsx` — add partner sheet
- `components/synastry/synastry-detail-screen.tsx` — detail screen
- `components/synastry/aspect-drilldown-sheet.tsx` — drilldown sheet
- `lib/api/synastry.ts` — API client

## 6. Frozen / Out of scope
- Не трогать existing frontend
- Не трогать backend (уже готов)
- Не трогать tests (следующий срез)

## 7. Must-preserve invariants
- data-testid: synastry-screen, synastry-add-sheet, synastry-detail-screen, aspect-drilldown-sheet
- data-state: loading|ready|empty|error
- data-status: good|mid|bad
- aria-pressed, aria-expanded, role="dialog", aria-modal
- GRACE markers (check-markers.sh must pass)

## 8. Verification commands
```bash
pnpm exec tsc --noEmit
bash scripts/grace/check-markers.sh
```

## 9. Expected evidence
- `git diff --name-only` — frontend files
- `pnpm exec tsc --noEmit` — успешно
- `bash scripts/grace/check-markers.sh` — успешно

## 10. Escalation rule
Нужен соседний scope (tests, backend changes) → стоп, доложить, новый packet.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
