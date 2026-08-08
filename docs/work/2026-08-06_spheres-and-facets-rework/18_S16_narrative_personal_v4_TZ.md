# S16 TZ — narrative v4: персональные конкретные тексты вместо общих фраз

## packet title
S16-narrative-personal-concrete-v4

## Phase / Wave
W-SPHERES-FACETS-REWORK (docs/work/2026-08-06_spheres-and-facets-rework/)

## Modules
- M-TODAY-NARRATIVE (`apps/api/app/services/today_narrative_service.py`)
- M-API-DAY (`apps/api/app/api/day.py`)
- M-TODAY-PREGEN-SERVICE (`apps/api/app/services/today_pregen_service.py`)

## Контекст

v3 пишет канцелярской водой («В сфере отношений может усилиться напряжение»),
а строгий grounding-санитайзер такие тексты справедливо зануляет → карточки
без текстов. Причины на стороне промпта:
1. Промпт прямо требует «общими словами» и не даёт ни персоны, ни фона периода.
2. meaning/action в шаблоне ответа принудительно null — модель пишет только summary.
3. Анти-штампов нет; модель по умолчанию производит «в сфере X наблюдается Y».

Решение владельца (2026-08-08): персонализировать — имя, возраст, периодный фон
(фирдары/профекции уже есть в canonical units), конкретика вместо общих фраз.

## goal

1. Вход промпта получает блок `person` (firstName, age — оба опциональны) и
   `periodBackground` (большой/малый фирдар, годовая/месячная профекция —
   лорд + окно), извлечённый из canonical factor units.
2. Prompt version `today-narrative-v4`: анти-штампы, требование конкретики
   в рамках facet, few-shot примеры плохо→хорошо, обращение на «ты»,
   имя не чаще одного раза.
3. meaning и action становятся заполняемыми claim'ами (шаблон ответа —
   все три поля); drilldown уже умеет их рендерить.
4. Жёсткие инварианты сохраняются: без дат/часов в тексте, facet-дисциплина,
   capability-гейты, запрет машинных имён, grounding-валидация без изменений.

## exact write scope

- `apps/api/app/services/today_narrative_service.py`
- `apps/api/app/api/day.py` (только проброс person в background narrative)
- `apps/api/app/services/today_pregen_service.py` (только проброс person)
- `apps/api/app/core/config.py` (default prompt version → v4)
- `apps/api/tests/test_today_narrative_service.py`
- `.env` (dev): `TODAY_NARRATIVE_PROMPT_VERSION=today-narrative-v4`

## frozen / out-of-scope

- grounding-санитайзер (`narrative_sanitizer.py`), lease-механика, projection,
  selection, frontend — без изменений;
- PII-политика логов: person в промпте — да (решение владельца), в логах
  prompt/person не печатается (проверить emitted события — только счётчики).

## Требования к реализации

1. `TodayNarrativePerson(first_name: str | None, age: int | None)`;
   `generate_today_narrative(..., person: TodayNarrativePerson | None = None)`.
   day.py: first_name из user.profile, age = от profile.birthday на target_date.
   pregen: то же из cohort member profile. Оба None → блок person опускается.
2. `_period_anchors(units)`: firdar_major/firdar_minor/annual_profection/
   monthly_profection из background units (technique из semantic_key JSON),
   с русским лордом (существующие PLANET/LOT маппинги) и окном active_from/
   active_until. В промпт — как фон («не факт дня»).
3. v4 prompt (русский): персона, фон, анти-штампы (явный список), требование
   конкретного бытового наблюдения/действия в рамках facet, 2 few-shot пары
   плохо→хорошо, summary ≤220 (validator), meaning ≤260 и action ≤180
   (инструкция). Имя ≤1 раза в каждом claim, естественно.
4. Шаблон ответа: summary/meaning/action все `{text, sourceEventIds}`.
   Инструкция: все три обязательны в каждом присутствующем блоке.
5. GRACE-разметка обновлённых блоков сохранить.

## must-preserve invariants

- `_validate_response`/`_claim`/`_block_grounding` семантика без изменений;
  grounding-null деградация остаётся.
- Существующие тесты narrative/pregen/day зелёные (шаблон ответа меняется —
  фикстуры ответов провайдера в тестах обновить под 3-claim блоки).
- Логи: никаких текстов промпта/ответов/имён в событиях.

## verification commands

```bash
cd apps/api && .venv/bin/python -m pytest tests/test_today_narrative_service.py tests/test_today_pregen_service.py tests/test_day_convergence_api.py -q
```

Плюс живой прогон на аккаунте владельца: удалить narrative-строки 08–18.08,
открыть день, проверить: тексты конкретные, без штампов, выровнены по событиям,
grounding-нулей меньше чем до пакета.

## expected evidence

- diff'ы scope-файлов; pytest вывод; 2–3 примера сгенерированных текстов
  до/после по одному дню владельца.

## escalation rule

Потребовалось менять санитайзер, lease, projection или wire-контракт — СТОП,
доложить ревьюеру.

## no-commit rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
