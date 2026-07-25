# Named Promo Campaign Context Handover

## Цель

Реализовать named promo campaigns для SolarSage Astro маленькими независимо проверяемыми slices через skill coder-loop. После завершения всех slices, полного release-gate и PostgreSQL acceptance — push main, штатный production deploy и smoke-check.

Важно: промокампания не называется «тестерской». PromoCampaign.display_name — произвольное название, заданное владельцем. Confirmation sheet показывает это название и конкретные доступные преимущества.

## Состояние Git

- branch: main
- HEAD: 30d083e
- main ahead origin/main на 10 коммитов
- product-коммиты НЕ отправлены в origin
- production НЕ обновлялся этой реализацией
- tracked working tree чистый

Не трогать чужие untracked-файлы:
- docs/work/2026-07-24_ci-pipeline-optimization/
- docs/work/2026-07-24_election-personal/
- docs/work/2026-07-24_prod-error-loop/
- public/election-proto.html

Origin/main:
20f7d08 docs(promo): define named campaign implementation slices

Локальные коммиты после origin/main:
952a7bb feat(promo): route telegram start parameters safely
1461c15 feat(promo): add campaign redemption schema
95aa7f1 refactor(access): expose additive grant primitive
d741848 docs(promo): serialize cross-campaign user grants
b253447 refactor(profile): expose birth readiness contracts
24bdc87 chore(observability): register promo campaign events
3222753 feat(promo): add safe campaign preview domain
af06a45 feat(promo): issue campaign grants atomically
7305cec feat(promo): harden redemption failure handling
30d083e fix(promo): recover natal entitlement races

## Документация

Master и Slice 01–20:
docs/work/2026-07-24_named-promo-campaign/

## Следующая задача

Начать строго со Slice 07:
docs/work/2026-07-24_named-promo-campaign/07_PROMO_WIRE_CONTRACTS_TZ.md

Не переходить сразу к HTTP/UI. Сначала закончить и принять Slice 07, затем Slice 08 и далее.

## Workflow coder-loop

- Обязательно прочитать:
  /opt/solarsage-astro/.agents/skills/coder-loop/SKILL.md
- Код пишет Gemini/opencode в tmux astro2.
- Одна итерация = одна локальная цель, обычно 1–3 файла и targeted test.
- Кодеру всегда говорить: ничего не коммить и не пушить.
- Ревьюер читает полный diff и коммитит только после приёмки.
- Модель несколько раз удаляла или ослабляла уже принятые assertions и откатывала GRACE header. При каждом продолжении сравнивать тесты с HEAD: нельзя удалять старые проверки ради зелёного результата.
- Не push до полного release-gate: push main запускает production workflow.

## Завершённый backend domain

Основные файлы:
- apps/api/app/services/promo_campaign_service.py
- apps/api/tests/test_promo_campaign_service.py

Последние проверки:
- promo service: 35 passed
- access/profile/natal соседний контур: 43 passed
- scripts/check_logging_guardrails.py: passed
- compileall: passed
- git diff --check: passed

Полный test suite и release-gate ещё НЕ запускались.

## Ключевые продуктовые инварианты

### 1. Start parameter
- numeric /^\d+$/ — только существующая referral-механика;
- promo token:
  ^(?=.{12,16}$)(?=.*[a-hj-km-np-z])[a-hj-km-np-z2-9]+$
- исключены 0/o и 1/l/i;
- остальные значения игнорируются;
- invalid/promo никогда не должны попасть в referral fallback;
- promo token сохраняется только в sessionStorage:
  __astro_pending_promo_token
- после чтения tgWebAppStartParam удаляется из URL;
- raw token/start_param/initData не логируются.

### 2. PromoCampaign
Поля:
- display_name — произвольное публичное название;
- code_hash — SHA-256 lowercase hex, UNIQUE;
- active;
- activation_starts_at inclusive;
- activation_ends_at exclusive;
- max_redemptions;
- redemptions_used;
- access_days;
- bonus_credits;
- unlock_natal.

В БД хранится только hash. Raw token существует только на границе запроса/CLI.

### 3. PromoRedemption
- UNIQUE(campaign_id, user_id);
- ссылки на access_ledger_id, credit_id, natal_purchase_id;
- grant FK используют SET NULL;
- redemption/counter/grants создаются одной outer-транзакцией.

### 4. Preview
- ordinary SELECT, без FOR UPDATE;
- не мутирует БД и ничего не резервирует;
- не логирует offer_viewed;
- existing redemption имеет приоритет ALREADY_REDEEMED даже после disable/expiry/full;
- incomplete profile возвращает profile_complete=false, не ошибку.

### 5. Redeem validation/locking
Порядок:
- exact token validation до БД;
- campaign SELECT FOR UPDATE;
- existing redemption check;
- active/start/end validation;
- User SELECT FOR UPDATE;
- profile readiness;
- capacity;
- grants/redemption/counter;
- один final commit.

Campaign lock всегда раньше User lock. User lock обязателен для сериализации двух разных кампаний одного пользователя и предотвращения пересекающихся additive access windows.

### 6. Error codes
Domain:
- INVALID_CODE
- CAMPAIGN_EXPIRED
- CAMPAIGN_FULL
- ALREADY_REDEEMED
- PROFILE_INCOMPLETE

RATE_LIMITED добавится на HTTP/rate-limit слое.

### 7. Profile readiness
- unlock_natal=false: base onboarding readiness;
- unlock_natal=true: strict natal readiness:
  birthday, birth_time, birth_lat, birth_lon, birth_tz, gender;
- координата 0 валидна;
- PROFILE_INCOMPLETE не расходует кампанию.

### 8. Grants
Access:
- AccessLedger entry_type=subscription;
- additive start = max existing end_date + 1 day либо today;
- days inclusive;
- никакой настоящей Subscription/YooKassa enrollment.

Credits:
- HoraryCredit source=gift;
- amount exact, used_amount=0;
- week fields null;
- expiry = UTC 00:00 дня после access_until;
- metadata_json только:
  {"campaign_id":"<uuid>","grant_type":"promo"}
- credits требуют access_days > 0.

Natal:
- Purchase product_slug=natal_full_report;
- status=delivered;
- payment_id=null;
- horary_quota_added=null;
- context_hash текущего strict-профиля;
- существующие succeeded/delivered entitlement переиспользуются;
- insert защищён SAVEPOINT;
- UNIQUE-конфликт повторно ищет fulfilled Purchase;
- посторонний IntegrityError не маскируется и откатывает всю outer transaction;
- get_or_build_natal_context не вызывается, sidecar/LLM не запускаются.

### 9. Transaction/failure invariants
- один final commit;
- промежуточные flush допустимы;
- domain и unexpected errors делают rollback;
- failure после access/credit/natal/final flush оставляет ноль grants, redemption и counter;
- commit failure не пишет success;
- duplicate не создаёт повторных grants;
- success event только после commit.

### 10. Logging/privacy
Events уже зарегистрированы:
- promo.offer_viewed
- promo.redemption_succeeded
- promo.redemption_rejected
- promo.redemption_failed
- promo.campaign_created
- promo.campaign_disabled

Backend redeem использует:
- slice=W-PROMO-CAMPAIGN
- module=M-PROMO-CAMPAIGN-SERVICE
- block=REDEEM

Запрещены в логах:
- token/start_param/code_hash;
- display_name;
- initData;
- Telegram ID;
- birth/profile fields;
- request/response bodies;
- exception message.

Допустимы campaign_id, safe config, stable error_code/error_kind.
Logging failure не должен ломать пользовательский flow.

### 11. Frontend flow, ещё не реализован
- после Telegram auth вызвать preview и показать confirmation sheet;
- sheet показывает display_name и только включённые benefits;
- CTA «Активировать»;
- role=dialog, aria-modal, стабильные data-testid/data-state;
- если profile incomplete:
  token остаётся только в sessionStorage;
  переход в onboarding;
  после заполнения sheet показывается снова;
- закрытие sheet не удаляет pending token;
- success/terminal error удаляет token;
- offer_viewed логируется только при фактическом показе sheet;
- никакого ручного поля ввода в MVP.

### 12. Deployment
Не использовать ручной uvicorn/systemd app units.
Канонический production:
- immutable images;
- infra/production/docker-compose.app.yml;
- /usr/local/libexec/solarsage/prod-orchestrator;
- production host root@2.26.20.80;
- API 8000, frontend 3002, sidecar 18091, DB 5433.

До deploy обязательно:
- закончить Slices 07–20;
- full Vitest/Pytest/contract/typecheck/build/Playwright gates;
- PostgreSQL migration/concurrency acceptance из Slice 19;
- privacy/Nginx checks;
- проверить прод-egress;
- только затем push main, дождаться workflow/tag и сделать smoke.

### Известная отдельная проблема release-gate
bash scripts/grace/check-markers.sh сейчас показывает 4 нарушения в двух election-страницах без module contract/map:
- app/(grace)/readings/election/page.tsx
- app/(grace)/readings/election/[id]/page.tsx

Это не относится к promo diff. Не чинить молча без проверки происхождения, но перед общим release-gate проблему потребуется разрешить.

Точка продолжения: docs/work/2026-07-24_named-promo-campaign/07_PROMO_WIRE_CONTRACTS_TZ.md.
