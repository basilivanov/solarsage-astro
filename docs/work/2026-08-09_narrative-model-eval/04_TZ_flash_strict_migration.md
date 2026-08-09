# 04 — Миграция Today-нarrative на DeepSeek V4 Flash + strict json_schema

Дата: 2026-08-09. Следствие eval run `20260809T082931Z` (см. `evals/results/20260809T082931Z/`,
`review-revealed.json`). Решения владельца:

1. **Pregen-путь (офлайн, day_pregen 04:07): `deepseek/deepseek-v4-flash`** — победитель
   слепого review (rank #1), json_valid 1.0, auto_score 78.2, $2.37/мес @3000 вызовов.
2. **On-demand путь (холодный день, интерактивный cache-miss): остаётся
   `openai/gpt-4.1-nano`** — p50 3.6с против 27с у flash; просадка качества
   допустима на minority-пути. Вариант 2 из обсуждения, утверждён владельцем.
3. **Оба пути — strict json_schema (array-шаблон) + `provider.require_parameters`**:
   strict-плечо лучше json_object почти по всем метрикам у всех моделей;
   у flash strict подавляет reasoning 2295→264 токена/вызов (цена вдвое ниже).
4. **Fallback-модель: `google/gemma-4-31b-it`** (runner-up eval, не reasoning,
   $1.81/мес) — через OpenRouter `models` fallback array.

## Кодовая фактура (проверена ревьюером)

- Современный клиент: `apps/api/app/services/llm_service.py` — `_openrouter_generate`
  уже умеет `json_schema` + `require_parameters` (line ~327) и `json_object` mode;
  модель всегда `settings.llm_model` (глобальная, default nano, config.py:164).
- Устаревший прямой fallback: `_deepseek_generate` там же (line ~387) — модель
  `deepseek-chat` выведена из эксплуатации 2026-07-24 → fallback сейчас сломан
  по факту. То же в старом `apps/api/app/services/llm/client.py:113`.
- Narrative: `apps/api/app/services/today_narrative_service.py` —
  `build_today_narrative_prompt` (keyed json_object шаблон, prompt_version
  default `today-narrative-v5`), `_call_kwargs` интроспектирует сигнатуру llm.
- Pregen: `app/jobs/day_pregen.py` → `today_pregen_service.py`
  (env DAY_PREGEN_*). On-demand: `today_service.py` → narrative lease.
- Strict array-схема для порта: `strict_response_schema()` в
  `scripts/narrative_model_eval.py` (eval arm B, валидирована на 56 вызовах flash
  с json_valid 1.0 и 28 nano с 0.93).
- Измеренные токены flash strict: mean completion 1059 (reasoning 264 + visible 800).

## Задачи кодера

### T1. Config (`apps/api/app/core/config.py`)

- `today_narrative_model_pregen` = `"deepseek/deepseek-v4-flash"` (env `TODAY_NARRATIVE_MODEL_PREGEN`)
- `today_narrative_model_ondemand` = `"openai/gpt-4.1-nano"` (env `TODAY_NARRATIVE_MODEL_ONDEMAND`)
- `today_narrative_fallback_models` = `["google/gemma-4-31b-it"]` (env `TODAY_NARRATIVE_FALLBACK_MODELS`, comma-separated)
- `today_narrative_pregen_max_output_tokens` = `3000` (env; измеренный mean 1059 → headroom ×3)
- Глобальный `llm_model` НЕ менять (другие фичи untouched).

### T2. Strict array-шаблон для narrative (оба пути)

- Портировать `strict_response_schema()` из eval-runner в прод
  (`today_narrative_service.py` или `app/schemas/`).
- Narrative-вызов: `response_format={"type":"json_schema","json_schema":{...,"strict":True}}`
  + `provider: {"require_parameters": True}`.
- Парсинг: array-ответ → существующая внутренняя keyed-структура **на этапе парсинга**,
  чтобы хранение/рендеринг/фронт-контракт не изменились (старый кэш остаётся валидным).
- Валидация fail-closed как сейчас (существующие валидаторы + sanitizer не трогаем).
- `TODAY_NARRATIVE_PROMPT_VERSION` → `today-narrative-v6` (инструкция шаблона меняется
  на array-формулировку из eval arm B; остальной контент промпта byte-identical).
- Проверить: входит ли prompt_version в ключи narrative-кэша; если нет — обеспечить,
  чтобы старый кэш не подмешивался (обосновать в докладе).

### T3. System/user сплит

- Расширить `_openrouter_generate` опциональным `system: str | None` (или `messages=`),
  дефолт — текущее поведение (другие вызовы byte-identical).
- Narrative: правила/роль/контракт → system; факты дня/payload → user.
  Суммарный текст — тот же, меняются только роли.

### T4. Роутинг моделей по путям

- Pregen-путь: model = pregen (flash), max_tokens = 3000.
- On-demand путь: model = ondemand (nano), max_tokens = текущий `TODAY_NARRATIVE_MAX_OUTPUT_TOKENS`.
- Fallback: OpenRouter `models` array = `[path_model, *fallback_models]` в теле запроса
  (проверить по доке OpenRouter семантику model+models; unit-тест формы тела).
- Direct-DeepSeek fallback для narrative-пути больше не используется.

### T5. Починка legacy fallback-цепочки (deepseek-chat EOL)

- `_deepseek_generate` (llm_service.py и старый client.py, если жив): заменить
  deprecated `deepseek-chat`. Выбор: fallback через OpenRouter на
  `settings.llm_fallback_model` (новый env, default `google/gemma-4-31b-it`),
  прямой api.deepseek.com не использовать. Цепочка обслуживает horary (платная
  фича) — сейчас fallback там гарантированно 4xx; покрыть тестом.

### T6. Тесты (pytest, apps/api/tests/)

- форма тела narrative-запроса: json_schema strict + require_parameters + models array;
- парсинг array→keyed: валидный, невалидный (fail-closed), пустые секции;
- роутинг: pregen → flash/3000, on-demand → nano/текущий cap;
- legacy fallback использует llm_fallback_model;
- существующие today/pregen/llm тесты зелёные (обновить ожидания формы тела).
- `python -m pytest tests/ -q` в apps/api полностью зелёный + grace_lint.

### T7. Доки

- AGENTS.md: новые env (TODAY_NARRATIVE_MODEL_PREGEN/ONDEMAND/FALLBACK_MODELS,
  PREGEN_MAX_OUTPUT_TOKENS), prompt_version v6, факт «flash=pregen, nano=on-demand,
  fallback=gemma», убрать устаревшее про deepseek-chat.
- Dev `.env` — добавить новые переменные (значения как в ТЗ).

## НЕ в скоупе

- Фоновая догенерация холодного дня (вариант 1) — отложено владельцем.
- Horary/election/why-промпты — не трогаем (кроме починки fallback-модели T5).
- Фронт — контракт не меняется.
- Прод-деплой и правка `/etc/solarsage/app.env` — отдельным шагом после приёмки на dev.

## Приёмка (ревьюер + владелец на dev)

1. pytest зелёный, grace_lint чисто, доклад кодера с diff-резюме.
2. Деплой на dev (стандартный путь), `python -m app.jobs.day_pregen` вручную →
   в логах виден flash + reasoning tokens в разумных пределах (~200-500/вызов);
   тексты владельцу на завтра — глазами против текущих.
3. Холодный день через UI: narrative приходит за ~3-5с (nano).
4. Rollback: revert env (TODAY_NARRATIVE_MODEL_PREGEN=nano или prompt_version=v5) + restart.
