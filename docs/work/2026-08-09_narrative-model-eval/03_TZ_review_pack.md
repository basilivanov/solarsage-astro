# 03 — Blind review pack: тексты для слепой оценки владельца

Дата: 2026-08-09. Продолжение `01_TZ.md` (раздел «Human blind review») и `02_TZ_addendum`.
Инварианты в силе: stdlib-only, GRACE-маркеры, fail-closed, платных вызовов нет,
продовый код не трогаем. Run: `evals/results/20260809T082931Z/`,
raw: `.eval-runs/narrative-model-eval-v1/20260809T082931Z/` (gitignored).

## Зачем

report.html по контракту не содержит сырых текстов — владельцу нечего оценивать.
Нужен отдельный review-пак: ~30 анонимизированных блоков текстов от топ-2 и baseline,
scorecard для оценок, раскрытие идентичностей после заполнения.

## Кандидаты (фиксированы ревьюером)

| label | model_key | arm | роль |
|---|---|---|---|
| candidate-a | baseline-nano | json_object | текущий продовый конфиг |
| candidate-b | gemma-4-31b | strict_json_schema | топ-1 по автометрикам |
| candidate-c | deepseek-v4-flash | strict_json_schema | топ-2, самый дешёвый из reasoning |

Маппинг candidate→model+arm — ТОЛЬКО в `evals/results/20260809T082931Z/review-key.json`.
В review.html и scorecard маппинг НЕ встраивать (ни в markup, ни в комментарии,
ни в data-атрибуты, ни в порядок следования candidate-меток — см. shuffle).

## Задачи кодера

### P1. `scripts/narrative_eval_review_pack.py`

1. Читает raw responses из `--run-dir .eval-runs/narrative-model-eval-v1/20260809T082931Z`
   и `inputs.json` задачи. Никаких сетевых вызовов.
2. Выборка дней: все 3 `convergence_today` + 7 `quiet_day` с максимальным покрытием
   facets/polarities (детерминированное правило от `inputs.json`, repeat r0).
   Итого 10 input_id × 3 кандидата = 30 блоков.
   Пропускать response-файлы с `truncated: true` или невалидным JSON — fail-closed
   с явным списком пропусков в stdout (для наших кандидатов trunc=0, но правило нужно).
3. Блок = один день одного кандидата:
   - факт-шапка из inputs.json: `target_date`, `state`, `day_tone`, `facets`,
     `polarities` + список expected events (facet + polarity + eventId) — это опора
     для оценки accuracy («текст соответствует фактам дня?»);
   - тексты модели как в продукте: по каждому событию summary / meaning / action
     (поле `.text`), в порядке следования в payload; разделы `impulses`/`convergences`
     подписаны по-русски;
   - заголовок блока: `blk-NN · candidate-x` (никаких имён моделей).
4. Группировка по дню (3 кандидата одного дня рядом — так accuracy сравнивается
   на одних фактах), порядок кандидатов внутри дня — перемешан детерминированным
   seed от run_id. Порядок дней — тоже перемешан (тот же seed).
5. Маскинг: тексты не должны содержать имя владельца. Входы уже замаскированы
   («ИМЯ»), но добавить fail-closed проверку: если в тексте блока встречается
   что-то кроме токена «ИМЯ» похожее на firstName из person-поля промпта — падать.
   (Сейчас firstName отсутствует — проверка на будущее, пометить в коде.)
6. Выходы в `evals/results/20260809T082931Z/`:
   - `review.html` — self-contained, лёгкие стили, без внешних ресурсов;
   - `scorecard.md` — шаблон таблицы: blk-NN | candidate | beauty 1–5 | accuracy 1–5 | заметка;
   - `review-key.json` — маппинг candidate→{model_key, arm, label} (НЕ публиковать);
   - `review.json` — пустой шаблон по схеме ниже.
7. `--reveal <filled-review.json>`: джойнит с review-key.json, печатает и пишет
   `review-revealed.json`: mean beauty/accuracy по моделям, per-block детали,
   итоговая таблица. Запускает ревьюер после заполнения владельцем.

### P2. Схема review.json

```json
{
  "schema_version": 1,
  "run_id": "20260809T082931Z",
  "blocks": [
    {"block_id": "blk-01", "candidate": "candidate-a", "beauty": null, "accuracy": null, "note": ""}
  ]
}
```

### P3. Проверки

- `python3 -m py_compile` + `scripts/grace_lint.py` чисто.
- Прогон генератора: 30 блоков, 0 пропусков, review.html без строк
  "gemma", "deepseek", "nano", "openai", "qwen" (grep-проверка в selftest-стиле
  прямо в stdout генератора).
- Отчитаться: пути артефактов + вывод grep-проверки анонимности.

## После кодера — ревьюер

1. Публикую review.html через CF-туннель (рядом с report.html), scorecard.md
   прикладываю в чат.
2. Владелец заполняет оценки → ревьюер запускает `--reveal` → финальный отчёт
   и рекомендация по модели.
