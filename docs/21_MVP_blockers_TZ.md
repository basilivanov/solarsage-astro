# 21. MVP-блокеры: аудит перед запуском

**Дата:** 2026-06-08  
**Статус:** Аудит  
**Цель:** Перечислить всё, что мешает запустить MVP в прод, с приоритетом и оценкой.

---

## Сводка блокеров

| # | Блокер | Серьёзность | Фронт | Бэк | Оценка |
|---|--------|-------------|-------|-----|--------|
| B1 | Пайволл/оплата — нет реального потока подписки | 🔴 Критический | ✗ | ✗ | 3 дня |
| B2 | Профиль: current_location + birthday_location не сохраняются | 🔴 Критический | — | ✗ | 0.5 дня |
| B3 | today_service использует birth_tz как current_tz | 🟡 Средний | — | ✗ | 0.5 дня |
| B4 | Horary — нет ни бэкенда, ни фронтенда | 🟠 Высокий | ✗ | ✗ | 5+ дней |
| B5 | HoraryCard берёт данные из chat/quota (мок) | 🟡 Средний | ✗ | — | 1 день |
| B6 | Нет маршрута /paywall — LockedDay ведёт в никуда | 🟡 Средний | ✗ | — | 0.5 дня |
| B7 | 1 тест падает: test_day_endpoint_returns_placeholder_when_llm_fails | 🟢 Низкий | — | ✗ | 0.5 дня |
| B8 | 64 теста ERROR: нет подключения к SolarSage sidecar (18091) | 🟢 Низкий | — | — | 0 (env) |
| B9 | Миграция dab4641 — от detached head | 🟡 Средний | — | ✗ | 0.5 дня |
| B10 | Нет products/subscription таблиц — YooKassa некуда писать | 🔴 Критический | — | ✗ | 2 дня |
| B11 | Payment router — заглушка без YooKassa | 🔴 Критический | — | ✗ | 1 день |
| B12 | PaymentService — Telegram-заглушка, нет реального провайдера | 🔴 Критический | — | ✗ | 1 день |

---

## B1. Пайволл/оплата — нет реального потока подписки 🔴

**Проблема:** В проде доступны экраны `AccessCard` (4 состояния: trial/subscription/expired/none) и `Paywall`, но кнопки «Оформить подписку» не ведут ни в какой реальный платёжный поток. Нет экрана выбора тарифа, нет интеграции с ЮKassa, нет подтверждения оплаты. Пользователь нажимает — и ничего не происходит.

**Фронтенд:**  
- `components/monetization/access-card.tsx` — кнопки `onSubscribe` передаются как props, но **нигде не вызываются** с реальным обработчиком.  
- `components/monetization/paywall.tsx` — кнопки `<button>` без `onClick`.  
- `components/grace/LockedDay.tsx` — `router.push('/paywall')`, но маршрута `/paywall` нет.  

**Бэкенд:**  
- `apps/api/app/api/payment.py` — только `POST /api/payment/create-intent` и `POST /api/payment/webhook` (заглушки).  
- Нет эндпоинта для инициации оплаты через ЮKassa, нет redirect/confirmation.  

**Что нужно для MVP:**  
1. Маршрут `/paywall` (или `/subscribe`) на фронтенде — выбор тарифа.  
2. Бэкенд: `POST /api/payment/create` → создание payment в БД → редирект на ЮKassa.  
3. Бэкенд: `POST /api/payment/yookassa-webhook` → приём уведомления → `AccessService.grant_subscription()`.  
4. Фронтенд: afterPayment callback → refresh access state.  

**Зависимость:** B10 (нужна таблица products) + B11 + B12.

---

## B2. Профиль: current_location + birthday_location не сохраняются 🔴

**Проблема:** Онбординг (фронтенд) уже собирает 3 локации: birthPlace, currentCity, birthdayCity. Но бэкенд `ProfileWrite` (`apps/api/app/schemas/profile.py`) содержит только `BirthData` — нет полей `current_city/lat/lon/tz`, нет `birthday_city/lat/lon/tz`. Модель `UserProfile` в БД тоже не имеет этих колонок.

**Фронтенд:** `onboarding-flow.tsx:86-95` — отправляет только `birth` данные:  
```ts
await updateProfile({
  birth: {
    birthday, birthTime, birthCity: birthPlaceStr,
    birthLat, birthLon, birthTz,
  },
})
```
`currentCity` и `birthdayCity` **теряются** — не отправляются.

**Бэкенд:** `UserProfile` имеет только `birth_city`, `birth_lat`, `birth_lon`, `birth_tz`. Нет `current_*` и `birthday_*`.

**Что нужно для MVP:**  
1. Миграция 0010: добавить 8 колонок в `user_profiles` (как описано в `docs/19_Profile_three_locations_TZ.md`).  
2. Обновить `BirthData` → `LocationData`, добавить `current_*` и `birthday_*` в `ProfileWrite`/`ProfileRead`.  
3. Обновить `profile_service.py` — сохранять новые поля.  
4. Обновить фронтенд `onboarding-flow.tsx` — отправлять все 3 локации.

---

## B3. today_service: birth_tz вместо current_tz 🟡

**Проблема:** `today_service.py:133` — комментарий `# W-3.4: use birth_tz as current_tz (proper current_tz tracking deferred)`. Транзиты считаются на `profile.birth_tz`, а не на `current_tz` пользователя. Для пользователей, живущих в другом часовом поясе, дневной прогноз будет сдвинут.

**Что нужно:** После B2 — подставить `current_tz` вместо `birth_tz` в `today_service.py:137`.

---

## B4. Horary — нет ни бэкенда, ни фронтенда 🟠

**Проблема:** Хорарные вопросы полностью отсутствуют в реализации.  
- Бэкенд: нет `HoraryQuota` таблицы, нет `horary_service.py`, нет `horary` роутера.  
- Фронтенд: нет `/horary` маршрута, нет формы вопроса, нет экрана результата.  
- `HoraryCard` на /profile берёт данные из `/api/chat/quota` — это чужая квота.  

**Для MVP:** Необязательно для_soft_launch_, но `HoraryCard` показывает мёртвые данные. Нужно либо убрать карту до реализации хорара, либо добавить минимальный эндпоинт `/api/horary/quota`.

---

## B5. HoraryCard: данные из chat/quota 🟡

**Проблема:** `lib/api/profile-meta.ts:getProfileMeta()` читает хорарную квоту из `/api/chat/quota`:
```ts
const quota = await quotaRes.json()
quotaRemaining = quota.remaining || 0
```
Это чатовая квота, не хорарная. Баланс хорарных вопросов **не существует**.

**Для MVP:** Либо скрыть `HoraryCard` до реализации хорара, либо добавить `/api/horary/quota` с заглушкой.

---

## B6. Нет маршрута /paywall 🟡

**Проблема:** `LockedDay.tsx` делает `router.push('/paywall')`, но `app/(grace)/paywall/` не существует. Пользователь видит 404.

**Что нужно:** Минимальная страница `/paywall` с выбором тарифа (или редирект на /profile с открытым AccessCard).

---

## B7. Падающий тест: test_day_endpoint_returns_placeholder_when_llm_fails 🟢

**Проблема:** Тест пытается подключиться к LLM/внешнему сервису и получает `httpx.ConnectError`. Нужен мок или маркер `--skip-external`.

**Что нужно:** Добавить `@pytest.mark.skipif` для тестов, зависящих от внешних сервисов, либо замокать LLM вызов.

---

## B8. 64 теста ERROR: SolarSage sidecar недоступен 🟢

**Проблема:** Тесты `test_pipeline_invariants.py` и `test_pipeline_golden.py` делают реальные запросы к SolarSage на `127.0.0.1:18091`. В тестовом окружении Docker-sidecar не поднят.

**Что нужно:** Не блокирует MVP. В CI нужно поднимать sidecar или мокать `SolarSageClient`.

---

## B9. Миграция dab464195b91 — detached head 🟡

**Проблема:** `dab464195b91_add_is_onboarded_to_user_profiles.py` имеет `down_revision = '0001_users'`, но миграция `0002_add_access_ledger.py` уже ответвляется от `dab4641`. Это создаёт ветвление в alembic history. Миграция 0002 стоит **после** dab4641, а 0001 — до. Это работает, но при добавлении новых миграций (0010, 0011, 0012) нужно быть аккуратным с `down_revision`.

**Что нужно:** Убедиться, что новые миграции 0010/0011/0012 ссылаются на `0009_add_chat_quotas` как `down_revision`, а не на `dab4641`.

---

## B10. Нет products/subscription таблиц 🔴

**Проблема:** Текущая `Payment` модель — плоская (id, user_id, amount, currency, status, provider, provider_payment_id). Нет таблиц `products`, `subscriptions`, `purchases`. ЮKassa-вебхук некуда записывать результат оплаты подписки.

**Что нужно (из TZ-20):**
1. Миграция 0011: таблицы `products`, `subscriptions`, `purchases`.  
2. `Payment` расширить: `confirmation_token`, `payment_method_id`, `refundable`, `receipt_url`.  
3. `SubscriptionService` — создание/проверка/отмена подписки.

---

## B11. Payment router — заглушка без YooKassa 🔴

**Проблема:** `apps/api/app/api/payment.py` — 2 эндпоинта: `create-intent` (stub) и `webhook` (stub). Нет ЮKassa SDK, нет редиректа, нет подтверждения.

**Что нужно:** Полная замена на реальный YooKassa flow (из TZ-20).

---

## B12. PaymentService — Telegram-заглушка 🔴

**Проблема:** `apps/api/app/services/payment_service.py` — создавал платежи с `provider="telegram"`, 30-дневная подписка хардкод, без реальной оплаты.

**Что нужно:** Заменить на `SubscriptionService` + `yookassa` SDK (из TZ-20).

---

## Минимальный путь к MVP

Для запуска MVP нужно **последовательно** закрыть блокеры:

### Фаза 1: Критический минимум (3 дня)

| Шаг | Что | Блокер | Оценка |
|------|-----|--------|--------|
| 1.1 | Миграция 0010: 8 колонок в user_profiles (current_*, birthday_*) | B2 | 0.5д |
| 1.2 | Обновить ProfileWrite/ProfileRead + profile_service | B2 | 0.5д |
| 1.3 | Обновить onboarding-flow.tsx — отправлять 3 локации | B2 | 0.5д |
| 1.4 | today_service: current_tz вместо birth_tz | B3 | 0.5д |
| 1.5 | Страница /paywall (минимальная) | B6 | 0.5д |

### Фаза 2: Оплата (3 дня)

| Шаг | Что | Блокер | Оценка |
|------|-----|--------|--------|
| 2.1 | Миграция 0011: products + subscriptions + purchases таблицы | B10 | 1д |
| 2.2 | YooKassa client + SubscriptionService | B11+B12 | 1д |
| 2.3 | Фронтенд: экран подписки → редирект ЮKassa → callback | B1 | 1д |

### Фаза 3: Починка тестов + полировка (1 день)

| Шаг | Что | Блокер | Оценка |
|------|-----|--------|--------|
| 3.1 | Замокать LLM в тесте fallback | B7 | 0.5д |
| 3.2 | Проверить цепочку миграций (0010, 0011 → down_revision=0009) | B9 | 0.5д |

### Отложить до после MVP

| Что | Почему |
|-----|--------|
| Horary (B4) | 5+ дней, не критичен для первого запуска |
| HoraryCard (B5) | Скрыть до реализации хорара |
| Pipeline инварианты (B8) | Нужно поднимать Docker sidecar в CI |

---

## Текущее состояние системы

**Работающее:**
- ✅ API Health: `GET /api/health` → 200
- ✅ Frontend: `http://localhost:3002` → рендерится
- ✅ Nginx: проксирует `/api/` → 8000, `/` → 3002
- ✅ 27 из 30 unit-тестов проходят
- ✅ Онбординг: 3 шага (welcome → birth+place → birthday city)
- ✅ Today экран:日报 разбор с LLM
- ✅ Chat: `/api/chat/` — работает
- ✅ Natal: `/readings/natal` — работает
- ✅ Access: `AccessService.grant_subscription()` — логика есть
- ✅ Referral: `POST /api/referral` — работает

**Неработающее/неполное:**
- ❌ Оплата: заглушка, нет ЮKassa  
- ❌ 3 локации профиля: фронтенд собирает, бэкенд не сохраняет  
- ❌ current_tz: используется birth_tz  
- ❌ /paywall: 404  
- ❌ Horary: полностью отсутствует  
- ❌ 1 тест падает, 64 ERROR (sidecar)

---

## Замечание по приоритету

Если нужно **самое быстрое MVP** (без оплаты, только бесплатный доступ по рефералам):
- Закрыть B2 (локации) + B3 (current_tz) ≈ **1.5 дня**  
- Скрыть кнопки «Оформить подписку» или заменить на «Скоро»  
- Оплата → Фаза 2 после первых пользователей

Если нужна **монетизация с первого дня**:
- Фаза 1 + Фаза 2 ≈ **6 дней**  
- ЮKassa sandbox сначала, prod после верификации