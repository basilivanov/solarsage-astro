# TZ 01: Retire acceptance-day + v2-wire-gate (stale V2 gate)

1. **Packet title**: SLICE-01 retire stale acceptance-day gate
2. **Phase / Wave**: W-TEST-SUITE-HYGIENE (2026-10-22), срез 01/02
3. **Modules**: e2e mock-visual
4. **Goal**: удалить детерминированно красный retired V2-gate и его мёртвый helper,
   не оставив висячих ссылок.

## 5. Exact write scope

- DELETE `e2e/mock-visual/acceptance-day.spec.ts`
- DELETE `e2e/mock-visual/v2-wire-gate.ts`

## 6. Frozen / out-of-scope

- `artifacts/audit/**` — НЕ удалять (payload читает `scripts/audit_today.py`).
- `scripts/audit_today.py`, workflows, Makefile — не трогать (ссылок на удаляемые
  файлы там нет — проверено архитектором; перепроверить grep'ом).
- Любые другие спеки.

## 7. Must-preserve invariants

- После удаления: `rg -l "acceptance-day|v2-wire-gate" e2e/ __tests__/ scripts/ Makefile .github/ packages/ app/ components/ lib/` — 0 совпадений.
- Convergence-покрытие Today не тронуто (today-convergence.spec.ts живой).

## Техническое задание

1. Удалить оба файла (git rm не делать — удаление закоммитит ревьюер).
2. Grep-чистота по инвариантам.
3. Прогнать `npx vitest run __tests__/components/telegram-provider.test.tsx` (быстрый
   smoke, что дерево собирается) и gate-scope mock-visual подмножество по списку из
   visual-regression.yml — локально, с preview :3003 (поднять и убить).

## 8. Verification

```bash
rg -l "acceptance-day|v2-wire-gate" e2e/ __tests__/ scripts/ Makefile .github/ packages/ app/ components/ lib/ | wc -l  # ожидается 0
node e2e/mock-visual/start-v2-preview.mjs & sleep 8; E2E_BASE_URL=http://127.0.0.1:3003 CI=true pnpm exec playwright test e2e/mock-visual/calendar.spec.ts e2e/mock-visual/profile.spec.ts e2e/mock-visual/readings.spec.ts e2e/mock-visual/horary.spec.ts e2e/mock-visual/natal.spec.ts e2e/mock-visual/today-convergence.spec.ts e2e/mock-visual/synastry.spec.ts --project=chromium --project=mobile; kill %1
```

## 9. Expected evidence

Вывод grep (0), gate-scope прогон (0 failed), подтверждение остановки preview.

## 10. Escalation rule

Если grep находит живую ссылку за пределами docs/work (история) — стоп, доложить.

## 11. No-commit rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
