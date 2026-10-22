# TZ 06: mock-visual harness — synastry спеки должны явно мокать auth

1. **Packet title**: SLICE-06 mock-visual auth harness fix (test-only)
2. **Phase / Wave**: W-AUTH-TIMEOUT-RACE-FIX (2026-10-22), срез 06 (harness)
3. **Modules**: e2e mock-visual specs
4. **Goal**: synastry mock-visual спеки больше не зависят от «тихого» падения
   dev-auth: они явно мокают `/api/auth/dev` → 200, как все остальные спеки сьюты.

## Контекст (доказано A/B на базе 9b65e65e)

- До фикса auth-гонки layout подавлял auth-error при `inTelegram=false`; synastry-спеки
  проходили с ФАКТИЧЕСКИ упавшим dev auth (Next route `app/api/auth/dev` проксирует на
  реальный бэкенд :8000, где dev auth выключен; ошибка была скрыта, контент рендерился).
- Теперь auth-error честно показывается → `synastry-screen` не появляется. Это
  intended-поведение продукта; чинится harness, не продукт.
- `promo-campaign.spec.ts:182` (retains token) падает и на базе — pre-existing локально
  на этом хосте, в этом срезе НЕ трогаем (на GH-раннере было зелёным на последнем деплое).

## 5. Exact write scope

- `e2e/mock-visual/synastry.spec.ts`
- `e2e/mock-visual/synastry-detail.spec.ts`

## 6. Frozen / out-of-scope

- Любой product/runtime код — запрещён. Только test-only harness.
- `e2e/mock-visual/route-interception.ts` — НЕ менять (использовать как есть).
- `promo-campaign.spec.ts` — не трогать.
- Бейзлайны PNG — не обновлять (визуальных диффов нет, причина — auth-precondition).

## 7. Must-preserve invariants

- Существующие assertions обоих спеков (testid/data-state/скриншоты) — без изменений.
- Mock остаётся test-only слоем (page.route), никаких изменений runtime.
- GRACE-маркеры файлов обновить под новые dependencies.

## Техническое задание

1. В обоих synastry-спеках добавить явный mock `POST /api/auth/dev` → 200
   (`{status:"ok", userId:"mock-preview-user"}`), ДО `page.goto`. Предпочтительно через
   общий strict-слой `installMockApiRoutes` из `./route-interception` (как
   promo-campaign/calendar/today-convergence), чтобы `/api/_log` и прочие побочные
   запросы тоже были покрыты; если переход на strict-слой раздувает diff — допустимо
   локальный `page.route("/api/auth/dev", ...)` рядом с существующим
   `page.route("/api/synastry", ...)`. Не ломать существующие route-настройки спеков.
2. Прогнать P5-подмножество: оба synastry-спека на chromium и mobile — все зелёные.
3. Затем полный P5 по инструкции из prod-deploy скилла (preview :3003,
   `E2E_BASE_URL=http://127.0.0.1:3003 CI=true pnpm exec playwright test e2e/mock-visual/
   --project=chromium --project=mobile`). Ожидание: зелёно всё, КРОМЕ известного
   pre-existing `promo-campaign.spec.ts:182` (его падение = не блокер, зафиксировать
   в отчёте). Preview после прогона остановить, порты 3003/18092 освободить.

## 8. Verification (одна команда)

```bash
E2E_BASE_URL=http://127.0.0.1:3003 CI=true pnpm exec playwright test e2e/mock-visual/synastry.spec.ts e2e/mock-visual/synastry-detail.spec.ts --project=chromium --project=mobile
```

## 9. Expected evidence

diff по двум спекам; вывод verification (все passed); итог полного P5 (N passed,
допустимый единственный failure — promo:182 pre-existing).

## 10. Escalation rule

Если зелень требует правки runtime или route-interception.ts — стоп, доложить, новый packet.

## 11. No-commit rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
