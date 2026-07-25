# ТЗ: Синастрия / Совместимость — адаптация HTML-прототипа в React

Источник: PR #11 (`public/prototypes/synastry/`), дизайн-контракт — `00_DESIGN_AND_LLM_CONTRACT.md` в этой же папке.
Прототип — только эталон UX и текстов. Код прототипа не переиспользуется.

## 0. Артефакты и приоритет контрактов

- UX/LLM master: `docs/work/2026-07-25_synastry-prototype/00_DESIGN_AND_LLM_CONTRACT.md`.
- Implementation contract: этот файл.
- Риски и rollback: `02_TECHNICAL_PREMORTEM.md`.
- Нормативная формула: `03_SCORING_AND_TONE_CONTRACT.md`.
- Запускаемый visual reference: `public/prototypes/synastry/index.html`.

При расхождении implementation contract и прототипа действует этот файл;
для scoring/tone действует `03_SCORING_AND_TONE_CONTRACT.md`. Production code,
tests и fixtures не импортируют JS/CSS/HTML из `public/prototypes/synastry/`.

MVP entry point — доступная карточка «Совместимость» в `/readings`, ведущая
на `/synastry`. Нижняя 5-tab навигация в этом релизе не меняется; отдельный
таб «Вместе» — последующее продуктовое решение после MVP.

## 1. Scope

**В scope:**

- раздел «Вместе» (синастрия): список сравнений, добавление партнёра, подробный отчёт пары, drill-down одного аспекта;
- backend: расчёт синастрии через sidecar, LLM-интерпретация по structured outputs (паттерн horary);
- состояние «время рождения партнёра неизвестно» (approximate-режим);
- монетизация MVP: расчёт за кредиты из общего с хораром/элективкой пула (п. 8).
- удаление партнёра и связанных ПДн/отчётов владельцем с сохранением обезличенного credit audit.

**Не в scope (пока):**

- расшаривание публичного snapshot (точка интеграции закладывается в схему, выключено);
- редактирование birth data партнёра после сохранения (изменение делается удалением и новым расчётом);
- проверка реальностью «Да, очень / Частично / Не похоже» влияет только на сохранённый feedback, без перевзвешивания интерпретации в MVP.

## 2. UX-флоу и экраны

### 2.1. Список сравнений — `data-testid="synastry-screen"`

- Поиск по имени, фильтры `Хорошо подходит / Нормально / Сложно` (`aria-pressed` на активном фильтре).
- CTA «Добавить человека» → sheet `role="dialog" aria-modal`.
- Карточка сравнения: аватар, имя, тип связи, балл `X из 100`, статус-пилюля, 1–2 предложения summary, счётчики `N поддерживают / N неоднозначны / N напрягают`.
- Карточка — `<button>` со стабильным `data-testid="synastry-card"`, `data-status="good|mid|bad"`.
- Состояния: `data-state="loading|ready|empty|error"` на корне списка; empty — «Никого не нашли…».
- Карточка дополнительно имеет `data-state="pending|generating|ready|failed"`.
  Для pending/generating показывается progress и переход на status screen; failed
  показывает безопасную ошибку и состояние возвращённого кредита.

### 2.2. Добавление партнёра — `data-testid="synastry-add-sheet"`

- Поля: имя, тип связи (`romantic|friendship|family|work|other`), дата рождения,
  время рождения, место рождения. Реальные `<label>`, не placeholder.
- Место выбирается через существующий `CityPicker`: submit передаёт display city,
  `lat`, `lon`, IANA `timezone`. Свободно введённая, но не выбранная подсказка
  не считается валидным местом; submit disabled до разрешения timezone.
- Переключатель «Точное время неизвестно» — `role="switch"`, `aria-checked`:
  - очищает и блокирует поле времени (`disabled`);
  - показывает предупреждение: планеты и основные аспекты останутся, ASC и дома партнёра не рассчитываются, Луна и балл — менее точные;
  - при выключении восстанавливает ранее введённое время;
  - precision-preview строка меняется на `Примерный расчёт: без ASC и домов партнёра`.
- Submit: loading на кнопке (`aria-busy`), ошибка — `role="alert"` внутри sheet, sheet не закрывается.
- Submit передаёт UUID `idempotency_key`; повтор с тем же key+payload возвращает
  существующий partner/report, а тот же key с другим payload → 409.

### 2.3. Отчёт пары — `data-testid="synastry-detail-screen"`

Секции сверху вниз (все со стабильными testid):

1. **Hero** `synastry-hero`: аватары пары, тип связи, «Ты + Имя», даты рождения, плашка `примерный расчёт` при approximate.
2. **Балл и вердикт** `synastry-score`: большой балл, вердикт, summary, баланс счётчиков. `data-status="good|mid|bad"`.
3. **Карта взаимодействия** `synastry-wheel`: двухкольцевой SVG, цветные линии аспектов (зелёный/янтарный/красный), легенда. Список аспектов ниже: 3 ключевых + «Показать все аспекты» (`aria-expanded`, `aria-controls`). Каждая строка аспекта — кнопка `data-testid="synastry-aspect"`, `data-tone`, кликабельна → drill-down.
4. **Наложение домов** `synastry-overlays`: пары «тех. подпись → человеческий текст». При approximate партнёра — честные строки вида «без времени рождения нельзя определить наложение».
5. **Человеческий перевод** `synastry-translations`: карточки `тон-точка + заголовок + tech-подпись + текст + сцена`. Tech-подпись — кликабельная кнопка «что значит?» → drill-down соответствующего аспекта.
6. **Сферы** `synastry-spheres`: Близость / Общение / Быт / Дела и деньги — accordion `<details>`-подобный, `aria-expanded`, балл сферы.
7. **Проверка реальностью** `synastry-feedback`: Да, очень / Частично / Не похоже (`aria-pressed`), дисклеймер «синастрия описывает паттерны, а не выносит приговор».
8. **Удаление** — overflow action «Удалить сравнение» → confirmation dialog.
   Успех возвращает на список; удаление готового отчёта не возвращает уже
   потраченный кредит.

В approximate-режиме: плашка на hero, пометка меньшей точности у Луны и общего балла, секция домов партнёра показывает ограничение, а не выдуманные данные.

### 2.4. Drill-down аспекта — `data-testid="aspect-drilldown-sheet"`

Mobile sheet (`role="dialog" aria-modal`, закрытие по Escape, backdrop и кнопке; `aria-labelledby` на заголовок):

1. **Что соединяется** — две карточки: планета пользователя и планета партнёра, функция каждой (статический словарь, не LLM).
2. **Как работает аспект** — соединение/тригон/секстиль/квадрат/оппозиция/квиконс (статический словарь).
3. **Как проявляется в жизни** — 3–4 короткие сцены (LLM).
4. **Что помогает** — 3–5 конкретных действий, нумерованные (LLM).
5. **Это не означает** — 3 пункта защиты от фатализма (LLM с жёсткими запретами).

Тон sheet'а отражает тон контакта: `data-tone="supportive|mixed|tense"`.

## 3. Backend

### 3.1. Расчётный слой (sidecar)

Новый additive endpoint `/v1/synastry` рассчитывает партнёрскую карту и
межкарточные аспекты. Он не дублирует owner natal calculation.

- Вход: уже рассчитанный owner chart из `NatalContextService` + partner birth
  data (`birth_time_precision: exact|unknown`). Это сохраняет owner natal cache
  единственным production source of truth.
- Выход: partner planets, доступные partner houses/ASC, cross aspects
  `{owner_planet, partner_planet, aspect, orb_degrees}`, precision flags.
- Sidecar не вычисляет tone, score, narrative и house overlays.
- House overlays строит API через существующий `find_house`:
  `partner planet → owner house` доступен всегда (Moon может быть approximate),
  `owner planet → partner house` — только при exact partner time.
- `applying` удалён из cross-natal contract как семантически неоднозначный для
  двух карт, построенных в разные моменты.
- **Sidecar меняется строго additive**: natal/transits schemas и endpoints не
  трогаются; AGENTS.md bug #2 про `planet.house` в этой фиче не исправляется.
- При `unknown` sidecar игнорирует любое присланное время и использует local
  `12:00`; partner houses/ASC отсутствуют, partner Moon получает approximate.
- Все Moon-partner аспекты получают `confidence=low`, `excluded_from_score=true`
  и нулевой вес, но остаются видимыми.
- Tone, общий score, counts и sphere scores вычисляет чистый API engine
  `M-SYNASTRY-SCORING` строго по нормативному приложению п. 3.2.

### 3.2. Формула балла и tone-mapping

Нормативный численный контракт полностью вынесен в
`03_SCORING_AND_TONE_CONTRACT.md`: орбисы, tone overrides, веса тел/аспектов,
orb decay, confidence, rounding, sphere mapping, versioning и trap fixtures.

Четыре числа из HTML-прототипа — visual copy targets, а не engine goldens:
прототип содержит только часть аспектов и не содержит полный owner birth input.
Подгонять формулу под 89/78/61/24 запрещено. Engine goldens строятся из полных
детерминированных входов, указанных в приложении.

### 3.3. API (FastAPI, паттерн `apps/api/app/api/natal.py`)

| Endpoint | Назначение |
|---|---|
| `GET /api/synastry/capabilities` | feature availability и public limits |
| `GET /api/synastry` | список сравнений пользователя (карточки: балл, статус, summary, счётчики) |
| `GET /api/synastry/quota` | общий credit balance |
| `POST /api/synastry/partners` | атомарно создать партнёра/report/spend, ответ 202 |
| `GET /api/synastry/{partner_id}/status` | polling generation state |
| `GET /api/synastry/{partner_id}` | полный отчёт пары |
| `GET /api/synastry/{partner_id}/aspect/{aspect_id}` | drill-down контент аспекта |
| `POST /api/synastry/{partner_id}/feedback` | проверка реальностью |
| `DELETE /api/synastry/partners/{partner_id}` | удалить partner PII и generated content |

- Статические `/capabilities` и `/quota` регистрируются до dynamic
  `/{partner_id}`; route trap-test обязан доказать отсутствие 422 collision.
- `PartnerCreate` содержит `name`, `relation`, `birth_date`, `birth_time?`,
  `birth_city`, `birth_lat`, `birth_lon`, `birth_tz`, `birth_time_precision`,
  `idempotency_key`.
- Validation: name trim 1–80 Unicode chars; birth date `1900-01-01..today`;
  city ≤200; lat/lon в географических диапазонах; `birth_tz` проходит
  `ZoneInfo`; exact требует time, unknown требует `time=null`; максимум 50
  active partners per user (`PARTNER_LIMIT_REACHED`, 409).
- Production availability = `SYNASTRY_ENABLED && products.synastry.is_active`.
  При false только `/capabilities` отвечает 200 с `enabled=false`; остальные
  routes возвращают 404 `FEATURE_DISABLED`, payment catalog скрывает продукт.
  Frontend build flag — coarse gate, runtime card/state сверяется с capabilities.
- Кеш-ключ отчёта:
  `(user_id, partner_id, owner_profile_hash, partner_input_hash,
  calculation_version, prompt_version, report_schema_version)`.
  Изменение owner birth profile или версии создаёт новый отчёт, старый получает
  `invalidated_at` и не возвращается как current.
- **Владение данными**: все запросы по `partner_id` фильтруются `user_id` из сессии на уровне запроса к БД; чужой `partner_id` → 404 (не 403). Это ПДн третьих лиц, IDOR здесь недопустим.
- Natural unique по `(name, birth_date)` запрещён: это не идентификатор человека
  и ломает одноимённых людей/близнецов. Дедупликация транспорта — только
  `(user_id, idempotency_key)` + request hash; одинаковый key с другим payload → 409.
- Создание partner row, report row и credit spend — одна DB transaction.
  External sidecar/LLM calls выполняются после commit и без удержания row lock.
- 409 при неполном owner profile; 402 при отсутствии кредита; sidecar failure
  сохраняет failed state и после исчерпания retry возвращает кредит.
- **Runbook миграции**: staged rollout из п. 11. Перед production обязательны
  upgrade и пустой downgrade на копии prod dump, old-app compatibility и
  app rollback без schema downgrade.

### 3.4. Схемы данных (public contract)

```jsonc
// SynastryCapabilitiesRead
{
  "enabled": true,
  "maxPartners": 50,
  "relations": ["romantic", "friendship", "family", "work", "other"],
  "productSlug": "synastry"
}

// PartnerCreate
{
  "name": "Максим",
  "relation": "romantic|friendship|family|work|other",
  "birthDate": "1987-09-09",
  "birthTime": "08:15",             // null only when precision=unknown
  "birthCity": "Москва",
  "birthLat": 55.7558,
  "birthLon": 37.6173,
  "birthTz": "Europe/Moscow",
  "birthTimePrecision": "exact|unknown",
  "idempotencyKey": "uuid"
}

// SynastryListRead
{
  "items": [{
    "partnerId": "uuid",
    "name": "Максим",
    "relation": "romantic",
    "reportState": "pending|generating|ready|failed",
    "score": 89,                       // null until ready
    "status": "good|mid|bad",         // null until ready
    "summary": "...",                 // null until ready
    "counts": { "good": 8, "mid": 2, "bad": 2 }, // null until ready
    "reportPrecision": "exact|approximate"
  }]
}

// SynastryGenerationRead — POST 202 / status polling
{
  "partnerId": "uuid",
  "reportId": "uuid",
  "status": "pending|calculating|narrating|ready|failed_retryable|failed_refunded",
  "stage": "queued|sidecar|scoring|narrative|persist|refund",
  "attemptCount": 0,
  "llmAttemptCount": 0,
  "creditState": "spent|refunded|not_spent",
  "error": null
}

// SynastryReport
{
  "reportId": "uuid",
  "schemaVersion": "synastry-report/v1",
  "calculationVersion": "synastry-calc/v1",
  "promptVersion": "synastry-prompt/v1",
  "partner": { "name": "...", "relation": "romantic", "birthTimePrecision": "exact|unknown" },
  "precision": {
    "ownerHousesAvailable": true, "partnerHousesAvailable": true,
    "ownerAscAvailable": true, "partnerAscAvailable": true,
    "partnerMoonPrecision": "exact|approximate",
    "reportPrecision": "exact|approximate"
  },
  "score": 89,                       // engine
  "status": "good|mid|bad",          // engine
  "counts": { "good": 8, "mid": 2, "bad": 2 },  // scored aspects only
  "visibleAspectCount": 14,
  "excludedAspectCount": 2,
  "summary": "...",                  // LLM
  "aspects": [SynastryAspect],       // engine fields + LLM short
  "houseOverlays": [{
    "id": "partner-mars__owner-house-5",
    "direction": "partner_to_owner|owner_to_partner",
    "planet": "Mars", "house": 5,
    "available": true,
    "unavailableReason": null,
    "tech": "Его Марс → твой 5 дом", "text": "..."
  }],
  "translations": [{ "aspectId": "owner-mercury__partner-mercury__square", "tone": "...", "title": "...", "tech": "...", "text": "...", "scene": "..." }],
  "spheres": [{ "key": "communication", "name": "Общение", "score": 74, "tone": "...", "text": "..." }]  // score/tone nullable if insufficient data
}

// SynastryAspect
{
  "id": "owner-mercury__partner-mercury__square",
  "ownerPlanet": "Mercury", "partnerPlanet": "Mercury",
  "aspect": "square", "orbDegrees": 1.05,
  "tone": "supportive|mixed|tense",  // engine
  "short": "Смысл теряется в форме", // LLM, ≤ 7 слов
  "confidence": "high|medium|low",   // engine (орбис + precision)
  "excludedFromScore": false
}

// AspectDrilldown (GET .../aspect/{id})
{
  "aspect": SynastryAspect,
  "ownerPlanetMeaning": "...",     // статический словарь
  "partnerPlanetMeaning": "...",   // статический словарь
  "aspectMeaning": "...",          // статический словарь
  "intro": "...",                    // LLM
  "scenes": [{ "title": "...", "text": "..." }],  // LLM, 3–4
  "repairs": ["..."],                // LLM, 3–5
  "notMeans": ["..."]                 // LLM, 3
}

// SynastryFeedbackWrite / Read
{
  "value": "yes|partly|no"
}
// response: { "value": "partly", "updatedAt": "2026-07-25T10:00:00Z" }
```

JSON выше показывает wire camelCase. В Pydantic/SQLAlchemy implementation
используется snake_case через общий `CamelModel`; отдельные ручные wire-типы
на frontend запрещены.

При `birth_time_precision=unknown` обязаны
`partner_houses_available=false`, `partner_asc_available=false`,
`report_precision=approximate`. Owner flags остаются true при полном профиле.
Unavailable owner→partner overlay создаётся backend как deterministic row с
`unavailable_reason=partner_birth_time_unknown`; LLM его не придумывает.

## 4. LLM-слой

Единственный сетевой client/entrypoint —
`apps/api/app/services/llm_service.py` (provider-enforced Structured Outputs:
`response_format: json_schema strict` + `provider.require_parameters=true`).
Новый pure-модуль `apps/api/app/services/synastry_llm.py` владеет schema,
prompt builders, статическими словарями и локальным валидатором, но не вызывает
provider напрямую. Пакет `apps/api/app/services/llm/` — legacy и не меняется.

`LLMService` получает ровно два новых entrypoint:

- `generate_synastry_report_narrative()` — один batched response для summary,
  shorts, translations, available overlays и spheres;
- `generate_synastry_aspect_detail()` — одна lazy generation на aspect с
  persist/cache по `(report_id, aspect_id, prompt_version)`.

DeepSeek fallback не получает provider schema, поэтому одинаковая локальная
fail-closed Pydantic + semantic validation обязательна после любого provider.
Движок владеет баллами, tone, орбисами и precision; LLM пишет только narrative.

**PII в промптах**: имя партнёра и точные данные его рождения не передаются.
Prompt оперирует «партнёр» + астрологические факторы. Имя используется только
структурными UI-заголовками; шаблонная подстановка в свободный LLM-текст не нужна.

### 4.1. Что НЕ отдаётся LLM (статические словари)

Из прототипа (`aspect-drilldown.js`) переносятся вербатим в backend-константы:

- `PLANET_MEANINGS` — функции 10 планет + ASC (рус., 1 строка каждая);
- `ASPECT_MEANINGS` — 6 типов аспектов: имя + объяснение.

### 4.2. LLM-генерации

| Генерация | Вход | Выход | Лимиты |
|---|---|---|---|
| base report batch | score/counts + все deterministic aspects/overlays/spheres | summary + shorts + translations + overlay/sphere texts | один provider response, ≤ 2 attempts total |
| aspect drill-down | один aspect + словарные значения | intro/scenes/repairs/not_means | lazy, persist once, ≤ 2 attempts total |

Один provider call имеет timeout 60 секунд. OpenRouter transport/validation
failure и DeepSeek fallback вместе входят в persisted лимит двух provider calls
на base report либо detail через все process/job retries. Никаких N-вызовов
«по одному short на аспект» нет.

Batch narrative связывается с engine facts только стабильными ID:

- `shorts[{aspectId, short}]` — ровно по одному на каждый visible aspect;
- `translations[{aspectId, ...}]` — 3–5 разных ключевых аспектов, одна карточка
  относится ровно к одному aspect; combined tech captions в MVP запрещены;
- `overlayTexts[{overlayId, text}]` — только для `available=true`;
- `sphereTexts[{sphereKey, text}]` — только для sphere с numeric score.

### 4.3. Правила тона (system prompt, обязательный блок)

- Калиброванный язык: «может», «чаще», «похоже». **Запрещено**: «всегда», «никогда», «обречены», «идеальная пара», «точно изменит».
- Обращение на «ты»; в narrative использовать «партнёр»/«вы», не имя,
  не «пользователь» и не «натив».
- Описывать наблюдаемое поведение пары, не личность: «разная эмоциональная логика», а не «он холодный».
- Не приписывать намерения: аспект не доказывает ложь, контроль, измену или манипуляцию.
- Не оценивать интеллект или качество человека (особенно по напряжённому Меркурию).
- Формула карточки: астро-причина → узнаваемое поведение → конкретная сцена. У каждого напряжения — repair; не оставлять пользователя с приговором.
- Одна мысль — одна сфера жизни. Без простыней: headline ≤ 7 слов, объяснение ≤ 220 символов.
- При доминировании tense-контактов **не сглаживать** вывод (эталон — кейс Дениса 24/100 в прототипе).
- При approximate-режиме: не упоминать дома/ASC партнёра, при необходимости явно помечать сниженную точность.

### 4.4. Few-shot gold standard

Эталонный пример в prompt builder — `Меркурий □ Меркурий` из прототипа
(`mercurySquareDetail()`): сцены про переписку/тон, порядок обсуждения,
«я такого не говорил», разную память; repairs и три `not_means`.
Он переносится в `services/synastry_llm.py`, не в legacy `services/llm/`.

### 4.5. Валидация LLM-вывода

По образцу `llm_claim_validator` / `validate_horary_llm_blocks`:

- JSON-schema strict на уровне провайдера;
- backend-проверка лимитов длины (short ≤ 7 слов, text ≤ 220 символов);
- блоклист запрещённых формулировок («обречены», «всегда», «никогда», «идеальная пара») → отказ генерации, retry;
- при approximate: reject текста, упоминающего дома/ASC партнёра как рассчитанные.
- ID-set validation: missing, duplicate или unknown aspect/overlay/sphere ID
  отклоняет весь batch; LLM не может добавлять deterministic factor.

## 5. Тестирование

- **Unit (pytest)**: все pure fixtures/boundaries из
  `03_SCORING_AND_TONE_CONTRACT.md`; tone fixtures из видимых prototype aspects;
  unknown `null|00:00|12:00|23:59` → одинаковые scored facts/score; directional
  overlays; fail-closed LLM validator; report/aspect generation idempotency.
- **API security**: чужой `partner_id`, `report_id`, `aspect_id` → 404 на
  list/detail/status/aspect/feedback/delete; PII не попадает в prompt/log capture.
- **PostgreSQL integration**: конкурентный PartnerCreate с одним idempotency key;
  два spend/refund; process death после spend; stale lease recovery; weekly-free
  creation; общий ordering weekly→bonus→paid для horary/election/synastry.
- **Billing**: purchase/start на каждый active slug; attribution metadata;
  refund до и после expiry; повторный/concurrent refund no-op.
- **Unit (vitest)**: список/отчёт/status states; CityPicker без timezone блокирует
  submit; unknown-time restore; drill-down из двух источников; paywall 402;
  delete confirmation; route `/quota` не воспринимается как partner ID.
- **Mock e2e (Playwright, route interception)**: структурный контракт экранов на стабильных payload — testid'ы п. 2, `data-state`, `data-status`, `aria-expanded` у «Показать все аспекты», `role="dialog"` у sheet'ов.
- **Real e2e**: Telegram HMAC → API: exact/unknown partner, polling до ready,
  report, lazy drill-down, feedback, delete; отдельный YooKassa sandbox buy-flow.
- **Миграция**: upgrade + downgrade `0025_*` на копии prod dump до появления
  данных; после production activation проверяется только forward/app rollback,
  data-bearing downgrade запрещён.
- Visual baseline: список, отчёт (good/mid/bad), drill-down sheet, approximate-состояние. Динамические текстовые зоны — маскировать.

## 6. GRACE-канон, структурные логи и обсервабилити

### 6.1. GRACE-разметка

Все новые файлы (backend и frontend) — по канону AGENTS.md: `AI_HEADER`, `START_MODULE_CONTRACT`, `START_MODULE_MAP` (с обязательным `owned_tests`), для нетривиальных публичных функций — `START_FUNCTION_CONTRACT`, для смысловых блоков — `START_BLOCK`/`END_BLOCK`. Гейт `scripts/grace/check-markers.sh` должен проходить.

Предлагаемые module-ID:

- `M-API-SYNASTRY` — `apps/api/app/api/synastry.py`;
- `M-SYNASTRY-SERVICE` — `apps/api/app/services/synastry_service.py` (оркестрация: sidecar → scoring → LLM → персист);
- `M-SYNASTRY-SCORING` — tone-mapping, балл 0–100, счётчики, precision-инварианты (engine);
- `M-LLM-SYNASTRY` — pure prompts/schema/validator в
  `apps/api/app/services/synastry_llm.py`; network entrypoints остаются в
  каноническом `apps/api/app/services/llm_service.py`;
- frontend: `components/synastry/*` — по одному контракту на файл, как в соседних фичах.

Sidecar-расчёт размечается по правилам sidecar-репозитория; со стороны API он остаётся за фасадом сервиса (как `NatalContextService` — прямых вызовов sidecar из роутов нет).

### 6.2. Реестр событий (canon-first)

Имена событий — `domain.verb` в стиле существующего реестра (`day.viewed`, `election.search_created`). **Сначала** добавить в `grace/canon/observability.xml` §8.5, затем перегенерировать `apps/api/app/core/logging_events.py` и `lib/log/events.gen.ts` (файлы сгенерированы — руками не править, см. WARNING в шапке `logging_events.py`).

Backend-события (`log_event` + `bind_log_context` из `apps/api/app/core/logging.py`):

| Событие | Когда |
|---|---|
| `synastry.partner_created` | партнёр сохранён (exact или unknown) |
| `synastry.calculation_started` | старт расчёта sidecar |
| `synastry.calculation_succeeded` | расчёт завершён, payload: число аспектов, precision |
| `synastry.calculation_failed` | sidecar недоступен / ошибка расчёта; report переходит в retry/refund state |
| `synastry.llm_phase_completed` | LLM-генерация блока завершена (по образцу `day.llm_phase_completed`) |
| `synastry.llm_validation_failed` | валидатор отклонил LLM-вывод (блоклист/лимиты/approximate) |
| `synastry.generation_recovered` | stale lease безопасно подхвачен повторно |
| `synastry.report_stuck` | reconciliation обнаружил report старше порога |
| `synastry.report_viewed` | отчёт отдан клиенту |
| `synastry.feedback_submitted` | проверка реальностью сохранена |
| `synastry.partner_deleted` | partner PII и generated content удалены владельцем |
| `synastry.credit_spent` | report transaction списала единицу общего пула |
| `synastry.credit_refunded` | credit или replacement adjustment восстановлен |
| `synastry.credit_refund_failed` | reconciliation не смог доказать refund invariant |

Frontend-события (`logEvent` из `lib/log/index.ts`):

| Событие | Когда |
|---|---|
| `synastry.list_viewed` | экран списка открыт |
| `synastry.partner_add_started` | sheet добавления открыт |
| `synastry.unknown_time_toggled` | переключатель «время неизвестно» (payload: `enabled`) |
| `synastry.aspect_drilldown_opened` | drill-down открыт (из строки аспекта или tech-подписи, payload: `source`) |
| `synastry.all_aspects_toggled` | раскрытие полного списка аспектов |

Metrics/alerts:

- `synastry_generation_duration_seconds{stage,result}` histogram;
- `synastry_reports_stuck` gauge, alert при `>0` два reconciliation run подряд;
- `synastry_credit_refund_failures_total`, alert на любое увеличение;
- `synastry_llm_validation_failures_total{provider,reason}` без prompt/output.

### 6.3. Требования к payload и приватность

- Каждый лог: `slice`, `module`, `block`, `event`, `correlation_id` (frontend-логгер заполняет defaults, но feature-код передаёт точные `slice/module/block` в `meta`).
- **PII третьих лиц**: имя партнёра, его дата/время/место рождения и LLM-тексты про него в логах запрещены — логировать `partner_id` (UUID), precision-флаги, счётчики. Это жёстче обычного правила redaction, т.к. данные принадлежат не пользователю, а третьему лицу.
- Ошибки логирования не ломают пользовательский flow (swallow + handled), бизнес-ошибки логируются и возвращаются по контракту эндпоинта.

### 6.4. Синхронизация GRACE-доков

- `grace/verification-matrix.md`: новый срез синастрии — маппинг модулей (`M-API-SYNASTRY`, `M-SYNASTRY-SERVICE`, `M-SYNASTRY-SCORING`, `M-LLM-SYNASTRY`, `components/synastry/*`) на slice gates и UC-сценарии (happy path: список → добавление exact/unknown → отчёт → drill-down → feedback).
- `emitted_logs` в MODULE_CONTRACT каждого нового модуля — только имена из реестра п. 6.2.
- `lib/readings.ts`: перенести `synastry` из coming в available и вести на
  `/synastry`. Нижний TabBar в MVP не меняется; при последующем выделении
  отдельного таба сначала обновляются AGENTS.md и navigation tests.

## 7. Замечания к прототипу (не блокеры ТЗ)

При ревью PR #11 обнаружено и исправлено в reference artifact:

- drill-down больше не зависит от неопределённого `planetGlyph`;
  React-версия объявляет типизированный UI glyph map, а semantic-словари
  получает из backend contract;
- tech-подписи карточек перевода вызывают drill-down после основного render;
- форма партнёра содержит обязательный выбор `relation`, чтобы visual reference
  не расходился с `PartnerCreate`;
- файлы `app.js/data.js/scenarios.js/logic.js/detail.css` — неподключённая старая версия прототипа, из ТЗ исключена.

## 8. Монетизация (MVP): общий кошелёк кредитов

Решение владельца: на MVP синастрия тратит **те же кредиты, что хорар и элективка** — общий пул `HoraryCredit`. Прецедент уже живой: элективка тратит `HoraryCredit` через `ElectionRequest.spent_credit_id` (`models.py:1059-1063`), отдельной таблицы кредитов у неё нет.

### 8.1. Механика (копируем паттерн election)

- Каталог: используется уже существующий canonical slug `synastry`, новый
  `synastry_1` не создаётся. V1 contract: `one_time`, `price_kopecks=39900`,
  `horary_quota=1`. Migration обновляет существующую строку, но оставляет
  `is_active=false` до staged activation; `seed_products` insert-only.
- Цена 399 ₽ наследует уже закоммиченный inactive catalog contract. Изменение
  до activation допустимо только отдельным owner decision + migration, не
  правкой константы без DB update.
- Списание: через `HoraryCreditService.select_spendable_credit(lock=True)` — тот же путь, что `election_service.py:112-146`.
- Журнал: `SynastryCreditSpend` (`credit_id` FK, nullable `report_id` UNIQUE
  с `ON DELETE SET NULL`, `idempotency_key` UNIQUE, `refunded_at`, amount=1).
  Nullable report сохраняет обезличенный audit после удаления partner data.
- Нет кредитов → **402** с кодом по образцу `NO_HORARY_CREDITS`; фронт открывает purchase-sheet (паттерн `HoraryPurchaseSheet`). Код ошибки и mapping — feature-нейтральные (`NO_CREDITS`), хорар/элективку не трогаем.
- **Refund при падении base-report generation**:
  - активный original credit: locked decrement `used_amount`, spend помечается refunded;
  - original credit уже истёк: он остаётся immutable для audit, создаётся
    `source=adjustment`, amount=1, expires_at=`now+7d`, metadata содержит только
    refund spend id/reason;
  - unique refund transition делает повторный/concurrent refund no-op;
  - failure lazy aspect drill-down после READY не возвращает цену всего отчёта,
    а остаётся retryable без нового списания.
- `GET /api/synastry/quota` — тот же `get_balance`, что у хорара/элективки; **UI-подпись — «кредиты», а не «хорарные вопросы»** (пул общий, профиль уже показывает этот же баланс).

### 8.2. Обязательные правки вне фичи (без них покупка не заведётся)

- `PurchaseStartRequest.product_slug` (`schemas/payment.py`) — добавить уже
  существующий `election_1` и canonical `synastry`; frontend union уже содержит
  election и получает synastry. Удалить `as any` из election purchase sheet.
- Атрибуция: при гранте писать `HoraryCredit.metadata_json = {product_slug, purchase_id}` (поле существует, сейчас не используется) — иначе per-product выручка и «куплено для X, потрачено на Y» не считаются в принципе.
- События: `synastry.credit_spent`, `synastry.credit_refunded` в реестр (п. 6.2); `horary.credit_spent` зарегистрирован, но нигде не эмитится — не использовать как образец.
- **Гонка weekly-free** (существующий латентный баг, принято закрыть в этом релизе): `get_or_create_current_weekly_free` (`horary_credit_service.py:102-145`) вставляет строку без catch IntegrityError — два одновременных первых касания пула → 500. Добавить catch + повторное чтение; тест на конкурентное создание.
- **Stalled purchases**: cron-свип (или алерт) на `payments/purchases` в `pending` старше 24ч — paid-but-unfulfilled сейчас восстанавливается только вручную по логам (`billing_service.py:1397-1403`). Минимум: алерт на `billing.fulfillment_blocked` + метрика stalled; идеал: sweep-джоба по образцу `jobs/billing_rebill.py`.
- **Каталог меняется только миграцией**: `seed_products` insert-only (`product_catalog.py:173-207`) — любое изменение цены/квоты без миграции молча не применится. Правило в runbook; post-deploy сверка таблицы `products` с `product_catalog.py`.
- **Денежный refund — только ручной процесс**: credit refund не равен возврату
  денег. По жалобе: проверка payments/purchases → ручной refund в ЮKassa →
  безопасная audit-запись без ПДн.
- **Регресс порядка списания**: общий для трёх фич тест-набор «weekly-free → bonus по ближайшему expires_at → paid по created_at» (`horary_credit_service.py:273-285`) — пул общий, изменение порядка бьёт по хорару, элективке и синастрии одновременно.

### 8.3. Решение по weekly-free (принято владельцем 2026-07-25)

Синастрия тратит кредиты из общего пула **включая weekly-free** — поведение как у элективки, source/feature-фильтр не вводим. `select_spendable_credit` берёт weekly-free первым (`horary_credit_service.py:273-285`) — это осознанное поведение для всех трёх фич. UX-последствие (расчёт синастрии может израсходовать «бесплатный вопрос недели») принимается; подписи в UI не должны обещать, что weekly-free — «именно хорарный вопрос».

## 9. Merge-blocking гейты из pre-mortem

`02_TECHNICAL_PREMORTEM.md` остаётся risk source. ТЗ закрывает design ambiguity,
но merge разрешён только при наличии указанного evidence:

| Gate | Spec resolution | Merge evidence |
|---|---|---|
| Scoring/tone | нормативный `03_SCORING_AND_TONE_CONTRACT.md` | pure/property/integration fixtures |
| Unknown time | directional precision + fixed local noon + Moon weight=0 | null/00/12/23 invariant tests |
| Calculation owner | owner cache → sidecar facts → API overlays/scoring | client contract + additive sidecar regression |
| Generation durability | DB state/lease + reconciliation, п. 10 | process-death/stale-lease PostgreSQL test |
| Public wire contract | Pydantic CamelModel only | generated artifacts + `pnpm contracts:check` |
| IDOR | every lookup owner-scoped | two-user 404 matrix |
| Transport idempotency | UUID key + request hash, no natural unique | concurrent same/different payload tests |
| LLM | canonical client + pure synastry module + batch/lazy calls | provider-body, PII and validator traps |
| Billing | canonical `synastry`, locked spend/refund, expiry adjustment | cross-feature PostgreSQL acceptance |
| PII lifecycle | owner delete + hard content purge + anonymized spend audit | delete/CASCADE/404 tests |
| Release/rollback | two-stage inactive→active rollout, п. 11 | prod-dump rehearsal + previous-SHA rollback |
| Observability | canon-first events + stuck/refund metrics | registry generation + alert smoke |

## 10. Durable generation и DB ownership

### 10.1. Таблицы

- `synastry_partners`: owner-scoped birth PII, relation, precision,
  `partner_input_hash`, timestamps. Hard delete разрешён только владельцу.
- `synastry_reports`: owner/partner FK, owner profile hash, all three versions,
  state/stage/attempt/lease, deterministic JSON, narrative JSON, errors,
  `invalidated_at`. Partial unique — один active report на полный cache key.
- `synastry_aspect_details`: `(report_id, aspect_id, prompt_version)` unique,
  state/attempt/lease/payload/error для lazy generation.
- `synastry_feedback`: `(user_id, report_id)` unique, выбранное значение и time;
  повторный POST — upsert.
- `synastry_credit_spends`: обезличенный ledger из п. 8.1; удаление report не
  удаляет факт расхода/возврата.

JSON хранится только после Pydantic/shared-contract validation. Partner name,
birth data и LLM narrative не дублируются в spend/payment metadata.

### 10.2. State machine

```text
PENDING → CALCULATING → NARRATING → READY
    └──────────────→ FAILED_RETRYABLE → (claim again)
    └──────────────→ FAILED_REFUNDED
READY ──version/profile change──→ INVALIDATED
```

- POST создаёт partner/report/spend и commit, возвращает 202, затем запускает
  best-effort task. Успех task не считается durable enqueue.
- Worker claim — conditional DB update с lease 5 минут. Одновременно report
  исполняет только один owner; внешние вызовы идут без открытой transaction.
- Deterministic sidecar/scoring payload сохраняется перед narrative phase,
  поэтому LLM retry не пересчитывает ephemeris.
- Job claim limit — 3 для sidecar/DB transient failures. Отдельный persisted
  `llm_attempt_count` никогда не превышает 2 через все claims. После исчерпания
  соответствующего лимита base report получает `FAILED_REFUNDED`; refund
  является частью reconciliation transaction.
- `GET /status` может безопасно инициировать claim, но correctness не зависит
  от того, открыл ли пользователь экран.
- One-shot `apps/api/app/jobs/synastry_reconcile.py` запускается каждые 5 минут
  через новый fixed orchestrator subcommand/Compose profile по образцу
  `billing-rebill`. Profile подключён к `app` и `db` networks, поскольку retry
  вызывает sidecar/LLM. Он claims stale leases, продолжает retry либо refund.
- Aspect detail имеет отдельную state machine. Его failure не меняет READY
  base report и не списывает/возвращает credit.

## 11. Production rollout и rollback

### 11.1. Release A — dark launch

1. `0025_synastry_schema` создаёт additive tables/indexes и обновляет строку
   `synastry` до quota=1, сохраняя `is_active=false`.
2. API/sidecar/frontend содержат feature code, но
   `SYNASTRY_ENABLED=false`, `NEXT_PUBLIC_SYNASTRY_ENABLED=false`.
3. Payment product listing и start_purchase обязаны дополнительно скрывать/
   отклонять synastry при server flag=false независимо от DB row.
4. Выполняются migration marker, deploy и regression smoke всех старых фич.

### 11.2. Release B — activation

1. Предыдущий active SHA уже обязан быть Release A.
2. Activation migration переводит `products.synastry.is_active=true`; Release A
   всё ещё скрывает его server flag, поэтому окно migrate→deploy безопасно.
3. Release B включает оба feature flags и карточку в Readings.
4. С prod host выполняется smoke test account с operator-granted adjustment
   credit: exact → ready → drill-down, unknown → ready, delete. Это проверяет
   sidecar и LLM egress; один пустой GET списка недостаточен.
5. Проверяются product row, shared balance/order и отсутствие stuck reports.

### 11.3. Rollback

1. Fixed command `prod-orchestrator synastry-disable --manual-confirm`
   атомарно ставит `products.synastry.is_active=false`; capabilities немедленно
   выключает writes/purchase даже до смены контейнеров.
2. `synastry-reconcile` завершает/возвращает все non-READY spends.
3. `prod-orchestrator rollback <release-a-sha> --manual-confirm`; Release A
   дополнительно имеет env flags=false.
4. Schema остаётся на head: app rollback не запускает Alembic downgrade.
5. Готовые reports/PII остаются читаемыми только после повторной активации;
   owner/operator delete продолжает работать в Release A.
6. Проверить product hidden, старые экраны, credit invariants и zero stale jobs.

Целевой rehearsed RTO: disable writes ≤2 минуты, app rollback ≤15 минут,
credit reconciliation ≤30 минут. Downgrade после появления production data
запрещён; аварийное восстановление данных — только из pre-migration backup.

## 12. Зафиксированные MVP-решения

- Entry point: Readings card → `/synastry`; TabBar не меняется.
- Product slug/price: существующий `synastry`, 399 ₽, общий credit pool.
- Weekly-free: расходуется первым.
- Partner editing: нет; owner delete: есть.
- Base report LLM: один batch; detail: один lazy cached call.
- Public wire: camelCase generated from Pydantic; ручные TS/Zod wire-типы запрещены.
- Share snapshot: schema extension point only, endpoint/кнопка выключены.

Если владелец меняет цену или хочет отдельный tab «Вместе», это отдельное
product decision до Release B; оно не должно молча попадать в implementer diff.
