# S19 TZ — narrative prompt: грамматика и согласование (v5)

## packet title
S19-narrative-grammar-v5

## Phase / Wave
W-SPHERES-FACETS-REWORK (docs/work/2026-08-06_spheres-and-facets-rework/)

## Modules
- M-TODAY-NARRATIVE (`apps/api/app/services/today_narrative_service.py`)

## Контекст

v4 тексты местами содержат грамматические ошибки согласования: «Солнце
сошлась» (средний род — «сошлось»), «сосредоточиться на рутины» (падеж —
«на рутине»). Модель не знает род русских названий планет и спотыкается
о редкие конструкции. Контракты/API не меняются — правка только в тексте
промпта.

## goal

1. В v5-промпте — явный блок про согласование: роды планет
   (Солнце — средний; Луна, Венера — женский; Меркурий, Марс, Юпитер,
   Сатурн, Уран, Нептун, Плутон — мужской), требование перечитать каждое
   предложение и исправить согласование рода/падежа перед ответом.
2. Prompt version bump: `today-narrative-v4` → `today-narrative-v5`
   (lease-инвалидация старых текстов, честное измерение эффекта).
3. Никаких других изменений промпта — одна точечная вставка.

## exact write scope

- `apps/api/app/services/today_narrative_service.py` (только текст промпта)
- `apps/api/app/core/config.py` (default `today_narrative_prompt_version`)
- `.env` (dev): `TODAY_NARRATIVE_PROMPT_VERSION=today-narrative-v5`
  (ревьюер применит сам, кодеру .env не трогать — только сообщить в отчёте)

## frozen / out-of-scope

- sanitizer, selection, lease, projection, frontend — без изменений;
- структура входа/шаблона ответа промпта — без изменений (только новый
  инструкционный абзац);
- лимиты длины claim'ов (220/260/180) — без изменений.

## Требования к реализации

1. Вставить в системную часть промпта короткий блок (русский):

   ```
   Грамматика обязательна:
   - Род планет: Солнце — средний («сошлось», «помогло»); Луна и Венера —
     женский; Меркурий, Марс, Юпитер, Сатурн, Уран, Нептун, Плутон — мужской.
   - Следи за падежами после предлогов («сосредоточиться на рутине»,
     не «на рутины»).
   - Перед ответом перечитай каждое предложение и исправь согласование.
   ```

   Место вставки — сразу после блока про запрещённые штампы, до примеров.
2. Никаких изменений Python-логики, только f-string текст. Проверить, что
   существующие prompt-assertions в тестах не привязаны к соседним строкам
   места вставки (test_today_narrative_service.py проверяет конкретные
   фрагменты — если упали на сдвиге, обновить фрагмент, не удаляя проверку).
3. `config.py`: default → `today-narrative-v5`.
4. Новый regression-тест: промпт содержит строку «сошлось» (защита от
   случайного удаления блока).

## must-preserve invariants

- Все существующие тесты narrative/content_cap/pregen зелёные;
- bounded-prompt инварианты (count evt_ bound, no factor_units) не меняются;
- логи: только счётчики, без текстов.

## verification commands

```bash
cd apps/api && .venv/bin/python -m pytest tests/test_today_narrative_service.py tests/test_today_narrative_content_cap.py tests/test_today_pregen_service.py tests/test_day_convergence_api.py -q
python3 scripts/grace_lint.py apps/api/app
```

## expected evidence

- diff scope-файлов; вывод pytest; цитата вставленного блока из промпта.

## escalation rule

Потребовалось менять что-либо кроме текста промпта и config default — СТОП,
доложить ревьюеру.

## no-commit rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
