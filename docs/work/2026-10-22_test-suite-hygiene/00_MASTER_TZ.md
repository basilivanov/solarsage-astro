# MASTER TZ: Test-suite hygiene — retire stale gates, promo:182 root cause

Дата: 2026-10-22. Исполнитель: кодер (tmux astro1) по срезам 01→02.
Ревьюер/коммит: архитектор. Принцип владельца: красный тест в наборе держать
неправильно — либо чинить, либо осознанно удалять.

## Факты (проверено архитектором 2026-10-22)

- **acceptance-day.spec.ts** — retired V2-gate: доказывает рендер committed
  today.v2.2 audit-payload; падает детерминированно везде; исключён из ОБОИХ GH
  workflow (visual-regression.yml:86, deploy-production.yml:139). Контракт V2
  superseded convergence Today, покрытым `e2e/mock-visual/today-convergence.spec.ts`
  (16 фикстур) + real-API release spec. `e2e/mock-visual/v2-wire-gate.ts`
  используется ТОЛЬКО им. Артефакт `artifacts/audit/2026-07-08/11_final_today_payload.json`
  остаётся (его читает `scripts/audit_today.py`).
- **promo-campaign.spec.ts:182** («incomplete profile redirects to promoNatal
  onboarding and retains token») — НЕ входит в GH gate-scope (visual-regression.yml
  гоняет только 7 спеков: calendar, profile, readings, horary, natal,
  today-convergence, synastry; deploy real-e2e suite его тоже не включает). Падает
  локально на этом хосте и на текущем, и на базовом дереве (A/B доказано) —
  возможно, не был зелёным никогда: pending promo token в sessionStorage === null
  после редиректа на /onboarding. ВАЖНО: если это не харнесс, а продукт — это
  реальный пользовательский баг (промо-токен теряется на ветке неполного профиля).
- GH gate-scope (visual-regression.yml) ЗЕЛЁНЫЙ на последних двух деплоях — это
  подтверждённая рамка «какие mock-visual спеки блокируют релиз».

## Карта срезов

| Срез | Содержание | Проверка |
|------|-----------|----------|
| 01 retire stale | удалить acceptance-day.spec.ts + v2-wire-gate.ts | grep-чистота + vitest/playwright smoke |
| 02 promo root cause | инструментировать, найти и устранить причину null-токена (test-only, если харнесс; эскалация, если продукт) | promo-campaign spec зелёный локально на chromium+mobile |

Кодер НЕ коммитит и НЕ пушит — коммит делает ревьюер.

## Критерии приёмки (глобальные)

- [ ] Полный локальный прогон `e2e/mock-visual/` (chromium+mobile) — 0 failed.
- [ ] Нет висячих ссылок на удалённые файлы.
- [ ] Корневая причина promo:182 задокументирована; если она продуктовая — отдельным
  packet с моего approve (scope-расширение).
