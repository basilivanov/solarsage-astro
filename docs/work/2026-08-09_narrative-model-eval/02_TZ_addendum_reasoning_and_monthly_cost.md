# 02 — Addendum: reasoning-модели + месячная проекция стоимости

Дата: 2026-08-09. Дополнение к `01_TZ.md`. Все инварианты 01_TZ в силе
(fail-closed, PII-маскинг, кодер НЕ делает платных вызовов, продовый код не трогаем).

## Контекст и проблема

Базовый платный прогон (run-id `20260809T082931Z`, `.eval-runs/narrative-model-eval-v1/`)
выявил: DeepSeek V4 (flash и pro) и Qwen 3.7 Plus на OpenRouter — reasoning-модели.
Они расходуют ~2000 из 2000 `completion_tokens` на скрытые reasoning-токены,
упираются в `max_tokens=2000` и отдают JSON, обрезанный на первых строках
(cap_hits по завершении прогона: flash 56/56, pro 54/56, qwen 56/56).
Это артефакт конфигурации вызова, не качество модели. nano и gemma — без обрезок.

Решение владельца: **reasoning НЕ отключаем** — замеряем стоимость как есть,
с reasoning-токенами, чтобы честно понимать бюджет prod-эксплуатации.

## Задачи кодера (только код, без платных вызовов)

### R1. Runner `scripts/narrative_model_eval.py`

1. Per-model overrides в `models.toml` (секция модели):
   - `max_tokens` (int, optional; дефолт 2000). Для `deepseek-v4-flash`,
     `deepseek-v4-pro` и `qwen-3.7-plus` выставить `6000` (reasoning ~2-4k + JSON ~1k).
   - `extra_body` (table, optional) — произвольные поля верхнего уровня запроса
     (на будущее, например `reasoning = { effort = "low" }`). Сейчас не заполнять.
2. Сохранять **полный raw `usage`** из ответа OpenRouter в response-файл, включая
   `completion_tokens_details.reasoning_tokens` (сейчас usage урезается до
   prompt/completion). Старые поля `prompt_tokens`/`completion_tokens` верхнего
   уровня сохранить для совместимости со scorer.
3. CLI-фильтр `--models key1,key2` — прогон только перечисленных моделей
   (матрица inputs×arms×repeats внутри фильтра не меняется).
4. `--out-dir <existing-run-dir>` — допрогон в существующий run-dir:
   файлы выбранных моделей перезаписываются, manifest обновляется идемпотентно,
   чужие файлы не трогаются. Это наш merge-механизм вместо второго run-id.
5. Truncation-флаг: если `completion_tokens >= max_tokens` — в response-файл
   писать `truncated: true`; scorer учитывает `truncated_rate` отдельной метрикой
   от `json_valid` (чтобы обрезка по капу не маскировалась под невалидный JSON
   и наоборот). Обрезанные ответы по-прежнему не участвуют в контент-метриках.

### R2. Отчёт `scripts/narrative_eval_report.py`

Новая секция **«Месячная проекция стоимости»**:

- Блок допущений (отображать текстом): 100 DAU, каждый день смотрит день →
  **3000 narrative-генераций/мес** (1 вызов на пользователь-день; day-pregen
  офлайн-батчем в 04:07, кэш-hit для пользователя). Цены из pricing TOML
  as_of 2026-08-09. Токены — измеренные средние по прогону (не оценка).
- Таблица по модель×плечо: mean prompt tokens, mean completion tokens
  (со split reasoning/visible, где доступно), mean $/вызов, **$/мес на 3000 вызовов**,
  p50/p95 latency.
- Примечание в отчёте: day-pregen офлайн → latency до ~60с приемлем;
  интерактивный on-demand путь — только cache-miss ( minority трафика).

### R3. Валидация (бесплатная)

- `--selftest` PASS, `validate` PASS (в т.ч. с `--models` фильтром).
- `python3 -m py_compile` обоих скриптов + grace_lint по канону.
- Никаких сетевых вызовов OpenRouter из кода кодера — платный допрогон
  делает ревьюер.

## После кодера — шаги ревьюера (не кодера)

1. ~~Проверить cap_hits qwen/gemma~~ Проверено по факту: qwen 56/56 truncated
   (reasoning), gemma 0/56 (чисто). В допрогон идут flash + pro + qwen
   (всем max_tokens=6000 в models.toml).
2. Допрогон: `--models deepseek-v4-flash,deepseek-v4-pro,qwen-3.7-plus --out-dir <run-dir>`
   с `--confirm-paid-run`; смета $0.2334, max-cap $0.9954.
   Стоп-гард поднят ревьюером $0.90 → $1.60 (`MAX_BUDGET_USD`,
   scripts/narrative_model_eval.py:81): гард считает кумулятивно с учётом
   уже потраченных $0.506, иначе fail-closed остановил бы допрогон на ~$0.39.
   Худший случай итого: $0.506 + $0.995 ≈ $1.50 < $1.60. Решение владельца:
   «пусть жгут reasoning, будем бюджет понимать». Овершот над первоначальным
   $1 фиксируем в отчёте прозрачно.
3. Compact + report + публикация — по 01_TZ.

## Done-критерии addendum

- [ ] models.toml: max_tokens/extra_body поддержаны; deepseek = 6000
- [ ] raw usage с reasoning_tokens в response-файлах
- [ ] `--models` + `--out-dir` работают (показать на validate/selftest)
- [ ] truncated_rate — отдельная метрика в metrics.json и отчёте
- [ ] отчёт содержит секцию месячной проекции ($/мес на 3000 вызовов)
- [ ] selftest/validate/py_compile/grace_lint зелёные
