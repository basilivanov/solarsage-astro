# TZ 02: promo-campaign:182 — root cause null-токена и зелёный прогон

1. **Packet title**: SLICE-02 promo pending-token null root cause
2. **Phase / Wave**: W-TEST-SUITE-HYGIENE (2026-10-22), срез 02/02
3. **Modules**: e2e promo harness; возможно M-TELEGRAM-START-PARAM / PromoCampaignGate
   (только после approve ревьюера)
4. **Goal**: `e2e/mock-visual/promo-campaign.spec.ts` зелёный локально на chromium и
   mobile; корневая причина null-токена задокументирована.

## Контекст

- Тест 182: `goto /day/2026-07-05?tgWebAppStartParam=m7q4n9x2r5kd` со strict-моками
  (`/api/auth/dev` 200, `/api/promo/preview` profileComplete:false). Редирект на
  `/onboarding?requiredFor=promoNatal` ПРОХОДИТ, но `sessionStorage.getItem(PENDING_KEY)`
  === null вместо токена. Падает и на текущем, и на базовом дереве (9b65e65e) —
  детерминированно, оба проекта. Остальные 3 теста спеки зелёные (токен хранится и
  работает на ветке profileComplete:true).
- В GH gate-scope спека НЕ входит — «зелёный на GH» никогда не проверялся.
- Гипотезы (проверить в этом порядке): a) промо-гейт на ветке incomplete profile
  редиректит ДО записи токена или стирает его; b) запись токена идёт не в то хранилище
  / не под тем ключом именно на этой ветке; c) `isPromoTokenConsumed`/`classifyStartParam`
  на этой ветке; d) тайминг: auth-флоу (dev sleep 500) vs монтирование гейта.

## 5. Exact write scope

- `e2e/mock-visual/promo-campaign.spec.ts` — правки харнесса, если причина тестовая.
- Временная инструментация (логи/дампы) — НЕ коммитить.
- ЕСЛИ причина продуктовая: только чтение product-файлов для доказательства;
  правки — после моего approve отдельным packet.

## 6. Frozen / out-of-scope

- Product-код (`components/promo/`, `hooks/`, `lib/telegram/`, `app/`) — без моего
  approve не править.
- Другие спеки.

## 7. Must-preserve invariants

- Существующие 3 зелёных теста спеки не сломать.
- Mock остаётся test-only слоем.
- Если тест документирует реальный баг — его нельзя «закрасить» ослаблением
  assertion без фикса причины.

## Техническое задание

1. **Воспроизвести** с инструментацией: поднять preview :3003, прогнать только
   `promo-campaign.spec.ts:182` с трассировкой/скриншотами и временным логом:
   момент записи токена (был ли вызов `savePendingPromoToken`), содержимое
   sessionStorage до редиректа и после, кто редиректит (гейт vs day-hook),
   порядок событий относительно `isAuthenticated`.
2. **Классифицировать причину**: харнесс (селекторы/тайминг/хранилище в тесте) vs
   продукт (реальная потеря токена на ветке incomplete profile).
3. **Харнесс** → починить спеку так, чтобы она проверяла настоящий контракт
   (токен сохраняется через неполный профиль), прогнать всю спеку на обоих проектах.
   **Продукт** → стоп, доказательства (логи, trace, минимальный сценарий), мне на
   approve отдельного packet на product-фикс.
4. Финал: полный прогон `e2e/mock-visual/promo-campaign.spec.ts` оба проекта зелёный;
   preview остановлен.

## 8. Verification

```bash
node e2e/mock-visual/start-v2-preview.mjs & sleep 8; E2E_BASE_URL=http://127.0.0.1:3003 CI=true pnpm exec playwright test e2e/mock-visual/promo-campaign.spec.ts --project=chromium --project=mobile; kill %1
```

## 9. Expected evidence

Корневая причина (с логом порядка событий), diff (харнесс) или evidence-пакет
(продукт), финальный прогон (0 failed), порты свободны.

## 10. Escalation rule

Продуктовая причина → стоп, доложить, новый packet. Ослабление assertion без
устранения причины запрещено.

## 11. No-commit rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
