# ТЗ: Синастрия / Совместимость — адаптация HTML-прототипа в React

Источник: PR #11 (`public/prototypes/synastry/`), дизайн-контракт — `00_DESIGN_AND_LLM_CONTRACT.md` в этой же папке.
Прототип — только эталон UX и текстов. Код прототипа не переиспользуется.

## 1. Scope

**В scope:**
- раздел «Вместе» (синастрия): список сравнений, добавление партнёра, подробный отчёт пары, drill-down одного аспекта;
- backend: расчёт синастрии через sidecar, LLM-интерпретация по structured outputs (паттерн horary);
- состояние «время рождения партнёра неизвестно» (approximate-режим);
- монетизация MVP: расчёт за кредиты из общего с хораром/элективкой пула (п. 8).

**Не в scope (пока):**
- расшаривание публичного snapshot (точка интеграции закладывается в схему, выключено);
- редактирование/удаление партнёра после сохранения (MVP — только добавление);
- проверка реальностью «Да, очень / Частично / Не похоже» влияет только на сохранённый feedback, без перевзвешивания интерпретации в MVP.

## 2. UX-флоу и экраны

### 2.1. Список сравнений — `data-testid="synastry-screen"`

- Поиск по имени, фильтры `Хорошо подходит / Нормально / Сложно` (`aria-pressed` на активном фильтре).
- CTA «Добавить человека» → sheet `role="dialog" aria-modal`.
- Карточка сравнения: аватар, имя, тип связи, балл `X из 100`, статус-пилюля, 1–2 предложения summary, счётчики `N поддерживают / N неоднозначны / N напрягают`.
- Карточка — `<button>` со стабильным `data-testid="synastry-card"`, `data-status="good|mid|bad"`.
- Состояния: `data-state="loading|ready|empty|error"` на корне списка; empty — «Никого не нашли…».

### 2.2. Добавление партнёра — `data-testid="synastry-add-sheet"`

- Поля: имя, дата рождения, время рождения, место рождения. Реальные `<label>`, не placeholder.
- Переключатель «Точное время неизвестно» — `role="switch"`, `aria-checked`:
  - очищает и блокирует поле времени (`disabled`);
  - показывает предупреждение: планеты и основные аспекты останутся, ASC и дома партнёра не рассчитываются, Луна и балл — менее точные;
  - при выключении восстанавливает ранее введённое время;
  - precision-preview строка меняется на `Примерный расчёт: без ASC и домов партнёра`.
- Submit: loading на кнопке (`aria-busy`), ошибка — `role="alert"` внутри sheet, sheet не закрывается.

### 2.3. Отчёт пары — `data-testid="synastry-detail-screen"`

Секции сверху вниз (все со стабильными testid):

1. **Hero** `synastry-hero`: аватары пары, тип связи, «Ты + Имя», даты рождения, плашка `примерный расчёт` при approximate.
2. **Балл и вердикт** `synastry-score`: большой балл, вердикт, summary, баланс счётчиков. `data-status="good|mid|bad"`.
3. **Карта взаимодействия** `synastry-wheel`: двухкольцевой SVG, цветные линии аспектов (зелёный/янтарный/красный), легенда. Список аспектов ниже: 3 ключевых + «Показать все аспекты» (`aria-expanded`, `aria-controls`). Каждая строка аспекта — кнопка `data-testid="synastry-aspect"`, `data-tone`, кликабельна → drill-down.
4. **Наложение домов** `synastry-overlays`: пары «тех. подпись → человеческий текст». При approximate партнёра — честные строки вида «без времени рождения нельзя определить наложение».
5. **Человеческий перевод** `synastry-translations`: карточки `тон-точка + заголовок + tech-подпись + текст + сцена`. Tech-подпись — кликабельная кнопка «что значит?» → drill-down соответствующего аспекта.
6. **Сферы** `synastry-spheres`: Близость / Общение / Быт / Дела и деньги — accordion `<details>`-подобный, `aria-expanded`, балл сферы.
7. **Проверка реальностью** `synastry-feedback`: Да, очень / Частично / Не похоже (`aria-pressed`), дисклеймер «синастрия описывает паттерны, а не выносит приговор».

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

Новый расчёт в sidecar: две натальные карты → межкарточные аспекты + домовые наложения.

- Вход: birth data обоих (у партнёра `birth_time_precision: exact|unknown`).
- Выход: список аспектов `{owner_planet, partner_planet, aspect, orb_degrees, applying}`, домовые наложения (только если у партнёра exact), флаги precision.
- **Sidecar меняется строго additive**: новый эндпоинт `/v1/synastry`; существующие схемы/эндпоинты natal и transits не трогаем (AGENTS.md bug #2 «нет `planet.house`» в рамках этой фичи **не чиним** — домовые наложения маппим API-side через существующий `find_house`, прецедент `normalization_service.py:217`).
- При `unknown`: дома и ASC партнёра не возвращаются вообще (`houses_available=false, asc_available=false`), Луна партнёра считается для полудня с `moon_precision=approximate`.
- **Правило Луны при unknown (жёстко, engine)**: все аспекты с участием Луны партнёра получают `confidence=low` и **нулевой вес** в общем балле; в UI — пометка меньшей точности. Балл не должен зависеть от того, в какое время суток «родился» партнёр (Луна проходит ~13°/день).
- Тон контакта (`supportive|mixed|tense`) определяет **движок** по типу аспекта и планетам (квадрат/оппозиция Сатурна-Плутона → tense и т.п.), не LLM. **Таблица tone-mapping и формула балла фиксируются в ТЗ до начала реализации (см. п. 3.3.1) — не свобода исполнителя.**
- Общий балл 0–100 и счётчики good/mid/bad — тоже движок (взвешенная свёртка аспектов, орбисы уменьшают вес). LLM балл не генерит и не видит как задание «объясни цифру».

#### 3.3.1. Формула балла и tone-mapping (заполняется до старта кода)

- Tone-mapping: таблица «планеты × тип аспекта → tone» с порогами орбисов (точная таблица — отдельным приложением к ТЗ; ориентиры: соединение/тригон/секстиль гармоничных планет → supportive, квадрат/оппозиция → tense, квиконс и контакты Урана/Нептунa → mixed по умолчанию, исключения фиксируются явно).
- Балл: взвешенная свёртка `Σ(weight(aspect) × orb_decay) / Σ(weight)` → 0–100; веса и кривая орбис-затухания фиксируются численно.
- Калибровка на golden-фикстурах: 4 пары из прототипа (Максим≈89, Ирина≈78, Кирилл≈61, Денис≈24) с допуском ±5; при расхождении правится формула, а не ожидание.
- Пороги статуса: `good ≥ 78`, `mid 45–77`, `bad < 45` (калибруется на тех же фикстурах).

### 3.2. API (FastAPI, паттерн `apps/api/app/api/natal.py`)

| Endpoint | Назначение |
|---|---|
| `GET /api/synastry` | список сравнений пользователя (карточки: балл, статус, summary, счётчики) |
| `POST /api/synastry/partners` | добавить партнёра (name, date, time?, place, precision) |
| `GET /api/synastry/{partner_id}` | полный отчёт пары |
| `GET /api/synastry/{partner_id}/aspect/{aspect_id}` | drill-down контент аспекта |
| `POST /api/synastry/{partner_id}/feedback` | проверка реальностью |

- Кеширование по образцу `NatalContextService`: отчёт считается один раз, хранится в БД, пересчёт только при смене входных данных. Обязательно хранить `calculation_version` — при фиксе формулы/промпта версия бампается, старые отчёты soft-invalidate (`invalidated_at`), иначе пользователи вечно видят текст старой генерации.
- **Владение данными**: все запросы по `partner_id` фильтруются `user_id` из сессии на уровне запроса к БД; чужой `partner_id` → 404 (не 403). Это ПДн третьих лиц, IDOR здесь недопустим.
- **Дедупликация**: повторный `POST /api/synastry/partners` с тем же `(user_id, имя, дата рождения)` → 409 или возврат существующего; частичный unique-индекс по образцу `0016_add_natal_cache_and_reports`.
- Генерация идемпотентна; 409 при неполном профиле пользователя; 502 при недоступном sidecar.
- **Runbook миграции**: миграции на проде не авто. Последовательность: `prod-orchestrator migrate <sha> --manual-confirm` → проверка маркера → deploy → post-deploy smoke на `GET /api/synastry`. Перед продом — прогон upgrade/downgrade на копии прод-дампа.

### 3.3. Схемы данных (public contract)

```jsonc
// SynastryReport
{
  "partner": { "name": "...", "relation": "...", "birth_time_precision": "exact|unknown" },
  "precision": {
    "houses_available": true, "asc_available": true,
    "moon_precision": "exact|approximate",
    "report_precision": "exact|approximate"
  },
  "score": 89,                       // engine
  "status": "good|mid|bad",          // engine
  "counts": { "good": 8, "mid": 2, "bad": 2 },  // engine
  "summary": "...",                  // LLM
  "aspects": [SynastryAspect],       // engine fields + LLM short
  "house_overlays": [{ "tech": "...", "text": "..." }],  // LLM, пусто при unknown
  "translations": [{ "tone": "...", "title": "...", "tech": "...", "text": "...", "scene": "..." }],  // LLM
  "spheres": [{ "name": "...", "score": 74, "tone": "...", "text": "..." }]  // score — engine, text — LLM
}

// SynastryAspect
{
  "id": "mercury-mercury-square",
  "owner_planet": "Mercury", "partner_planet": "Mercury",
  "aspect": "square", "orb_degrees": 1.05,
  "tone": "supportive|mixed|tense",  // engine
  "short": "Смысл теряется в форме", // LLM, ≤ 7 слов
  "confidence": "high|medium|low"    // engine (орбис + precision)
}

// AspectDrilldown (GET .../aspect/{id})
{
  "aspect": SynastryAspect,
  "owner_planet_meaning": "...",     // статический словарь
  "partner_planet_meaning": "...",   // статический словарь
  "aspect_meaning": "...",           // статический словарь
  "intro": "...",                    // LLM
  "scenes": [{ "title": "...", "text": "..." }],  // LLM, 3–4
  "repairs": ["..."],                // LLM, 3–5
  "not_means": ["..."]               // LLM, 3
}
```

При `birth_time_precision=unknown` → обязаны `houses_available=false, asc_available=false, report_precision=approximate`. Это инвариант, проверяемый схемой, а не пожелание к LLM.

## 4. LLM-слой

Паттерн — **только `apps/api/app/services/llm_service.py`** (provider-enforced Structured Outputs: `response_format: json_schema strict` + `provider.require_parameters=true`, `llm_service.py:272-277`). Пакет `apps/api/app/services/llm/` — legacy-стек без `response_format`, его **не расширяем**. DeepSeek-fallback молча роняет json_schema (`llm_service.py:333-335`), поэтому локальная fail-closed валидация обязательна (п. 4.5). **Движок владеет детерминированными полями (баллы, тон, орбисы, флаги precision) — LLM пишет только нарративные строки.** Собранный ответ валидируется по shared contract перед персистом; невалидный — отклоняется, не сохраняется.

**PII в промптах**: имя партнёра и точные данные его рождения в LLM-промпт не передаются — промпт оперирует «партнёр» + астрологические факторы (планеты/аспекты/орбисы/тона). Имя подставляется в текст уже на backend после генерации (шаблонная подстановка) или остаётся на уровне UI.

### 4.1. Что НЕ отдаётся LLM (статические словари)

Из прототипа (`aspect-drilldown.js`) переносятся вербатим в backend-константы:

- `PLANET_MEANINGS` — функции 10 планет + ASC (рус., 1 строка каждая);
- `ASPECT_MEANINGS` — 6 типов аспектов: имя + объяснение.

### 4.2. LLM-генерации

| Генерация | Вход | Выход | Лимиты |
|---|---|---|---|
| `summary` пары | топ-аспекты с тонами, счётчики, статус | 2–3 предложения | ≤ 300 символов |
| `short` на аспект | планеты, тип, тон | заголовок | ≤ 7 слов |
| `translations` (3–5 шт) | ключевые аспекты | title/text/scene на каждый | text ≤ 220 символов |
| `house_overlays` тексты | пары «планета → дом» | человеческий текст | 1 предложение |
| `spheres` тексты | баллы сфер (engine) | текст со встроенными «Слабое место:/Помогает:/Риск:» | ≤ 220 символов |
| drill-down `intro/scenes/repairs/not_means` | аспект + словарные значения | структура п. 2.4 | scenes 3–4, repairs 3–5, not_means ровно 3 |

### 4.3. Правила тона (system prompt, обязательный блок)

- Калиброванный язык: «может», «чаще», «похоже». **Запрещено**: «всегда», «никогда», «обречены», «идеальная пара», «точно изменит».
- Обращение на «ты», партнёр — по имени. Не «пользователь», не «натив».
- Описывать наблюдаемое поведение пары, не личность: «разная эмоциональная логика», а не «он холодный».
- Не приписывать намерения: аспект не доказывает ложь, контроль, измену или манипуляцию.
- Не оценивать интеллект или качество человека (особенно по напряжённому Меркурию).
- Формула карточки: астро-причина → узнаваемое поведение → конкретная сцена. У каждого напряжения — repair; не оставлять пользователя с приговором.
- Одна мысль — одна сфера жизни. Без простыней: headline ≤ 7 слов, объяснение ≤ 220 символов.
- При доминировании tense-контактов **не сглаживать** вывод (эталон — кейс Дениса 24/100 в прототипе).
- При approximate-режиме: не упоминать дома/ASC партнёра, при необходимости явно помечать сниженную точность.

### 4.4. Few-shot gold standard

Эталонный пример в промпт drill-down — `Меркурий □ Меркурий` из прототипа (функция `mercurySquareDetail()` в `aspect-drilldown.js`): сцены «переписка и неверно услышанный тон», «разный порядок обсуждения планов», «я такого не говорил / но так прозвучало», «разная память о разговоре»; repairs «я услышал, что… Верно?», «не решать чувствительные темы короткими сообщениями»; not_means «не значит, что кто-то глупее / не доказывает ложь / не запрещает научиться слышать друг друга». Копируется в `services/llm/prompts.py` как образец структуры и тона.

### 4.5. Валидация LLM-вывода

По образцу `llm_claim_validator` / `validate_horary_llm_blocks`:

- JSON-schema strict на уровне провайдера;
- backend-проверка лимитов длины (short ≤ 7 слов, text ≤ 220 символов);
- блоклист запрещённых формулировок («обречены», «всегда», «никогда», «идеальная пара») → отказ генерации, retry;
- при approximate: reject текста, упоминающего дома/ASC партнёра как рассчитанные.

## 5. Тестирование

- **Unit (pytest)**: tone-mapping движка и формула балла на golden-фикстурах 4 пар прототипа (±5); правило Луны при unknown (параметризованный тест: 00:00 vs 23:59 → одинаковый балл); инвариант precision (`unknown` → no houses/ASC); валидатор LLM-блоков (лимиты, блоклист, approximate-ограничение, DeepSeek без schema); идемпотентность генерации; **IDOR**: чужой `partner_id` → 404 на всех эндпоинтах; дедуп партнёров (повторный POST → 409); **биллинг**: buy-flow POST purchase/start на каждый активный slug → 200; refund при падении генерации (кредит вернулся, повторный refund — no-op); конкурентное создание weekly-free (нет 500); регресс порядка списания из общего пула (п. 8.2).
- **Unit (vitest)**: рендер списка/отчёта по fixture, переключатель «время неизвестно» (блокировка поля, восстановление значения), открытие drill-down из строки аспекта и из tech-подписи, paywall-sheet при 402.
- **Mock e2e (Playwright, route interception)**: структурный контракт экранов на стабильных payload — testid'ы п. 2, `data-state`, `data-status`, `aria-expanded` у «Показать все аспекты», `role="dialog"` у sheet'ов.
- **Real e2e**: Telegram HMAC → реальный API: добавление партнёра (exact и unknown), отчёт, drill-down, покупка кредита в тестовом режиме ЮKassa.
- **Миграция**: upgrade + downgrade `0025_*` на копии прод-дампа до деплоя.
- Visual baseline: список, отчёт (good/mid/bad), drill-down sheet, approximate-состояние. Динамические текстовые зоны — маскировать.

## 6. GRACE-канон, структурные логи и обсервабилити

### 6.1. GRACE-разметка

Все новые файлы (backend и frontend) — по канону AGENTS.md: `AI_HEADER`, `START_MODULE_CONTRACT`, `START_MODULE_MAP` (с обязательным `owned_tests`), для нетривиальных публичных функций — `START_FUNCTION_CONTRACT`, для смысловых блоков — `START_BLOCK`/`END_BLOCK`. Гейт `scripts/grace/check-markers.sh` должен проходить.

Предлагаемые module-ID:

- `M-API-SYNASTRY` — `apps/api/app/api/synastry.py`;
- `M-SYNASTRY-SERVICE` — `apps/api/app/services/synastry_service.py` (оркестрация: sidecar → scoring → LLM → персист);
- `M-SYNASTRY-SCORING` — tone-mapping, балл 0–100, счётчики, precision-инварианты (engine);
- `M-LLM-SYNASTRY` — промпты и валидатор в `apps/api/app/services/llm/` (по образцу horary);
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
| `synastry.calculation_failed` | sidecar недоступен / ошибка расчёта (→ 502) |
| `synastry.llm_phase_completed` | LLM-генерация блока завершена (по образцу `day.llm_phase_completed`) |
| `synastry.llm_validation_failed` | валидатор отклонил LLM-вывод (блоклист/лимиты/approximate) |
| `synastry.report_viewed` | отчёт отдан клиенту |
| `synastry.feedback_submitted` | проверка реальностью сохранена |

Frontend-события (`logEvent` из `lib/log/index.ts`):

| Событие | Когда |
|---|---|
| `synastry.list_viewed` | экран списка открыт |
| `synastry.partner_add_started` | sheet добавления открыт |
| `synastry.unknown_time_toggled` | переключатель «время неизвестно» (payload: `enabled`) |
| `synastry.aspect_drilldown_opened` | drill-down открыт (из строки аспекта или tech-подписи, payload: `source`) |
| `synastry.all_aspects_toggled` | раскрытие полного списка аспектов |

### 6.3. Требования к payload и приватность

- Каждый лог: `slice`, `module`, `block`, `event`, `correlation_id` (frontend-логгер заполняет defaults, но feature-код передаёт точные `slice/module/block` в `meta`).
- **PII третьих лиц**: имя партнёра, его дата/время/место рождения и LLM-тексты про него в логах запрещены — логировать `partner_id` (UUID), precision-флаги, счётчики. Это жёстче обычного правила redaction, т.к. данные принадлежат не пользователю, а третьему лицу.
- Ошибки логирования не ломают пользовательский flow (swallow + handled), бизнес-ошибки логируются и возвращаются по контракту эндпоинта.

### 6.4. Синхронизация GRACE-доков

- `grace/verification-matrix.md`: новый срез синастрии — маппинг модулей (`M-API-SYNASTRY`, `M-SYNASTRY-SERVICE`, `M-SYNASTRY-SCORING`, `M-LLM-SYNASTRY`, `components/synastry/*`) на slice gates и UC-сценарии (happy path: список → добавление exact/unknown → отчёт → drill-down → feedback).
- `emitted_logs` в MODULE_CONTRACT каждого нового модуля — только имена из реестра п. 6.2.
- AGENTS.md: при появлении раздела «Вместе» в нижней навигации — обновить описание навигации/экранов в каноне (root testid `synastry-screen` уже заложен в п. 2.1).

## 7. Замечания к прототипу (не блокеры ТЗ)

При ревью PR #11 обнаружено (чинить в рамках прототипа не требуется, учесть при реализации):

- drill-down в прототипе падает (`planetGlyph` не определён) — в React-версии словари планет/аспектов должны быть типизированным модулем, а не свободными глобалами;
- tech-подписи карточек перевода в прототипе не кликабельны (мёртвый override `renderTranslations`) — в ТЗ это требование п. 2.3.5;
- файлы `app.js/data.js/scenarios.js/logic.js/detail.css` — неподключённая старая версия прототипа, из ТЗ исключена.

## 8. Монетизация (MVP): общий кошелёк кредитов

Решение владельца: на MVP синастрия тратит **те же кредиты, что хорар и элективка** — общий пул `HoraryCredit`. Прецедент уже живой: элективка тратит `HoraryCredit` через `ElectionRequest.spent_credit_id` (`models.py:1059-1063`), отдельной таблицы кредитов у неё нет.

### 8.1. Механика (копируем паттерн election)

- Каталог: новый продукт `synastry_1` в `product_catalog.py` (`one_time`, `horary_quota=1`, цена — отдельным решением; сидится миграцией, т.к. `seed_products` не обновляет существующие строки). Fulfillment ничего менять не надо: `billing_service.py:982-991` уже грантит любой one-time продукт с `horary_quota` в общий пул.
- Списание: через `HoraryCreditService.select_spendable_credit(lock=True)` — тот же путь, что `election_service.py:112-146`.
- Журнал: своя таблица `SynastryCreditSpend` по образцу `ElectionCreditSpend` (`credit_id` FK, `report_id` UNIQUE, `idempotency_key` UNIQUE).
- Нет кредитов → **402** с кодом по образцу `NO_HORARY_CREDITS`; фронт открывает purchase-sheet (паттерн `HoraryPurchaseSheet`). Код ошибки и mapping — feature-нейтральные (`NO_CREDITS`), хорар/элективку не трогаем.
- **Refund при падении генерации**: если LLM/расчёт отчёта упал — кредит возвращается по паттерну `horary_service.py:330-381` (find spend → decrement `used_amount` → delete spend row → `refund_status`). Внимание: существующие реализации уже разошлись в поле expiry (`access_week_end` vs `expires_at`) — не копипастить вслепую, сверить обе и зафиксировать одно правило.
- `GET /api/synastry/quota` — тот же `get_balance`, что у хорара/элективки; **UI-подпись — «кредиты», а не «хорарные вопросы»** (пул общий, профиль уже показывает этот же баланс).

### 8.2. Обязательные правки вне фичи (без них покупка не заведётся)

- `PurchaseStartRequest.product_slug` (`schemas/payment.py:110-114`) — `Literal`, в который **уже сейчас не входит `election_1`** (покупка элективки 422-ит на валидации — живой баг). Добавить `election_1` + `synastry_1`, синхронизировать union в `lib/api/payment.ts`, тест buy-flow на каждый slug.
- Атрибуция: при гранте писать `HoraryCredit.metadata_json = {product_slug, purchase_id}` (поле существует, сейчас не используется) — иначе per-product выручка и «куплено для X, потрачено на Y» не считаются в принципе.
- События: `synastry.credit_spent`, `synastry.credit_refunded` в реестр (п. 6.2); `horary.credit_spent` зарегистрирован, но нигде не эмитится — не использовать как образец.
- **Гонка weekly-free** (существующий латентный баг, принято закрыть в этом релизе): `get_or_create_current_weekly_free` (`horary_credit_service.py:102-145`) вставляет строку без catch IntegrityError — два одновременных первых касания пула → 500. Добавить catch + повторное чтение; тест на конкурентное создание.
- **Stalled purchases**: cron-свип (или алерт) на `payments/purchases` в `pending` старше 24ч — paid-but-unfulfilled сейчас восстанавливается только вручную по логам (`billing_service.py:1397-1403`). Минимум: алерт на `billing.fulfillment_blocked` + метрика stalled; идеал: sweep-джоба по образцу `jobs/billing_rebill.py`.
- **Каталог меняется только миграцией**: `seed_products` insert-only (`product_catalog.py:173-207`) — любое изменение цены/квоты без миграции молча не применится. Правило в runbook; post-deploy сверка таблицы `products` с `product_catalog.py`.
- **Денежный refund — только ручной процесс**: API возврата средств в ЮKassa в коде нет. Зафиксировать операторский runbook: по жалобе → проверка `payments`/`purchases` → ручной refund в кабинете ЮKassa → запись в лог.
- **Регресс порядка списания**: общий для трёх фич тест-набор «weekly-free → bonus по ближайшему expires_at → paid по created_at» (`horary_credit_service.py:273-285`) — пул общий, изменение порядка бьёт по хорару, элективке и синастрии одновременно.

### 8.3. Решение по weekly-free (принято владельцем 2026-07-25)

Синастрия тратит кредиты из общего пула **включая weekly-free** — поведение как у элективки, source/feature-фильтр не вводим. `select_spendable_credit` берёт weekly-free первым (`horary_credit_service.py:273-285`) — это осознанное поведение для всех трёх фич. UX-последствие (расчёт синастрии может израсходовать «бесплатный вопрос недели») принимается; подписи в UI не должны обещать, что weekly-free — «именно хорарный вопрос».

## 9. Merge-blocking гейты из pre-mortem

До мёржа реализации обязательны (подробности — в премортеме от 2026-07-25):

1. Формула балла + tone-mapping + golden-фикстуры (п. 3.3.1) — закрыто в ТЗ, реализовать и покрыть тестами.
2. Правило Луны при unknown time (п. 3.1) + тест стабильности балла внутри суток.
3. LLM только через `llm_service.py`; fail-closed валидатор с trap-тестами (п. 4).
4. Sidecar additive-only; оверлеи домов через `find_house` API-side (п. 3.1).
5. IDOR-фильтр владельца + тесты 404 на чужой `partner_id` (п. 3.2).
6. Дедуп партнёров: unique-индекс / 409 (п. 3.2).
7. Runbook миграции `migrate → deploy → smoke` + прогон на копии прод-дампа (п. 3.2).
8. `PurchaseStartRequest` Literal + `metadata_json`-атрибуция + refund-тест (п. 8.2).
9. ~~Решение по weekly-free~~ — принято: тратит, как элективка (п. 8.3). Позиция по ПДн третьих лиц зафиксирована в п. 4 (промпт без имени партнёра) и п. 6.3 (логи только по `partner_id`).
10. Гонка weekly-free, stalled-purchases алерт/свип, каталог-только-миграцией, ручной refund-runbook, регресс порядка списания (п. 8.2) — приняты в релиз.
