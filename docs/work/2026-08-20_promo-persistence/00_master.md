# Master: персистентность промокода между сессиями (promo persistence)

Проблема: промокод из Telegram `start_param` живёт только в sessionStorage
вебвью и теряется при перезапуске Telegram / закрытии webview; активация
требует явного нажатия «Активировать» до очистки сессии.

Каноническое решение:
1. Backend сохраняет promo `start_param` (он входит в подписанный initData)
   в `users.pending_promo_token` при `/api/auth/telegram`.
2. Backend автоматически применяет сохранённый токен через
   `PromoCampaignService.redeem()` при завершении онбординга (PUT /api/profile).
3. Frontend fallback: pending token из sessionStorage → localStorage.

Срезы:
- `01_backend_pending_token_TZ.md` — модель + миграция + сохранение в auth.
- `02_backend_auto_apply_TZ.md` — auto-apply при PUT /api/profile.
- `03_frontend_localstorage_TZ.md` — sessionStorage → localStorage.

Ключевые инварианты:
- raw token никогда не попадает в логи/ответы (как и в M-PROMO-CAMPAIGN-SERVICE).
- Логин без start_param НЕ затирает сохранённый pending token.
- Auto-apply никогда не ломает PUT /api/profile: redeem выполняется ПОСЛЕ
  commit профиля, доменные ошибки промокода swallow + лог, HTTP 200 сохраняется.
