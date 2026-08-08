# S17 TZ — sanitizer: устранение ложных срабатываний (жребий Брака, отрицания)

## packet title
S17-sanitizer-false-positives

## Phase / Wave
W-SPHERES-FACETS-REWORK (docs/work/2026-08-06_spheres-and-facets-rework/)

## Modules
- M-NARRATIVE-SANITIZER (`apps/api/app/services/narrative_sanitizer.py`)

## Контекст

После S16 (v4) ~40% claim'ов зануляются grounding-санитайзером. Живой разбор
(08-08, аккаунт владельца, v4) показал два класса ложных срабатываний:

1. **Имя собственное жребия.** Claim romance/supportive
   «Меркурий в гармонии с твоим жребием Брака: сегодня ощущается поддержка
   и легкость в симпатии и свиданиях.» занулён, потому что `брак\w*` —
   паттерн чужого facet `partnership`. Но «жребий Брака» — собственное имя
   расчётной точки из title события (focus_title_builder.LOT_LABELS_RU:
   Фортуны, Духа, Эроса, Знания, Брака, Необходимости, Победы, Немезиды),
   а не facet-лексика.
2. **Полярность-антоним под отрицанием.** `_POLARITY_CONFLICT_PATTERNS`
   режет любое вхождение `напряж\w*` в supportive-блоке, включая
   семантически корректные «снизить напряжение», «без напряжения»,
   «не будет напряжения». Симметрично для tense: «не легко», «без гармонии».

Кейс, который остаётся ВАЛИДНЫМ null'ом (не трогаем): romance/tense summary
«…напряжением в романтических разговорах…» — «разговорах» это чужой facet
`everyday_contacts`, prompt v4 прямо запрещает эту тему в romance;
санитайзер отработал правильно.

## goal

1. Claim с именем собственным жребия («жребий/жребия/жребием Брака» и т.п.)
   не зануляется из-за слова «брак» — при этом голое «брак» вне имени жребия
   в romance/partnership-чужих блоках по-прежнему зануляется.
2. Полярность-антоним под явным отрицанием/митигацией в том же предложении
   («не», «нет», «без», «снизить», «снять», «избежать», «ослабить»,
   «уменьшить», «отпустить», «минимизировать») не зануляется; голый антоним
   («сегодня напряжение») по-прежнему зануляется.
3. Все прочие правила санитайзера бит-в-бит без изменений.

## exact write scope

- `apps/api/app/services/narrative_sanitizer.py`
- `apps/api/tests/test_narrative_sanitizer.py`

## frozen / out-of-scope

- `today_narrative_service.py` (промпт, шаблон, _claim) — без изменений;
- selection/grouping/projection/frontend — без изменений;
- запрещённые токены (Transit_/Natal_/Planet/M, …) — без изменений;
- health-diagnosis правило и broad-scope правило — без изменений;
- зависимости модуля: только stdlib (никаких импортов из focus_title_builder —
  список жребиев продублировать константой со ссылкой-комментарием на источник).

## Требования к реализации

1. **Маска имён жребиев.** Добавить `_LOT_NAME_PATTERN` (case-insensitive):
   `жреби\w*\s+(?:фортун\w*|дух\w*|эрос\w*|знани\w*|брак\w*|необходимост\w*|побед\w*|немезид\w*)`.
   В `has_narrative_grounding_violation` facet/sphere-детекция и polarity-scope
   проверки выполняются по маскированной копии текста (совпадения заменяются
   нейтральным плейсхолдером, например одним словом «жребий»). Исходный текст
   для forbidden-token проверок и для возврата не меняется. Маскировка —
   отдельная маленькая функция `_mask_lot_names(text) -> str`.
2. **Окно отрицания для polarity-конфликтов.** Для каждого match'а
   `_POLARITY_CONFLICT_PATTERNS[polarity]`: взять до 40 символов перед match'ем
   внутри того же предложения (границы — `.!?;\n`); если там есть маркер из
   фиксированного списка (`не`, `нет`, `без` как отдельные слова; стемы
   `снизи\w*|снижени\w*|сним\w*|снят\w*|избеж\w*|избег\w*|ослаб\w*|уменьш\w*|отпусти\w*|минимиз\w*|против`),
   match игнорируется. Реализация через `pattern.finditer`, без lookbehind
   переменной ширины. Логика — отдельная функция
   `_has_polarity_conflict(text, polarity) -> bool`.
3. GRACE-разметка: новые функции — START_FUNCTION_CONTRACT; MODULE_MAP
   дополнить (semantic_blocks: GROUNDING — упомянуть lot-mask и negation-window).
4. Тесты (минимум):
   - live-case 1: «Меркурий в гармонии с твоим жребием Брака: сегодня
     ощущается поддержка и легкость в симпатии и свиданиях.» — romance,
     supportive → violation False;
   - маска не протекает: «Жребий Брака активен: брак сегодня выгоден.» —
     romance, supportive → violation True (второе «брак» вне имени);
   - «День помогает снизить напряжение в тренировках.» — sport,
     training_routine, supportive → False;
   - «Сегодня напряжение в тренировках.» — sport, training_routine,
     supportive → True (голый антоним);
   - tense: «Утром будет не легко, к вечеру отпустит.» — health,
     general_condition, tense → False; «День лёгкий и спокойный.» — tense
     блок → True;
   - существующие тесты санитайзера зелёные без ослабления assertions.

## must-preserve invariants

- fail-closed семантика: неизвестные sphere/facet/polarity → True;
  нестроковый ввод → True;
- facet-ownership строгость вне двух описанных исключений (кейс
  «романтических разговорах» должен остаться NULLED — добавить regression-test);
- модуль остаётся чистой функцией без I/O, логов и зависимостей вне stdlib;
- `sanitize_narrative_text` не меняется.

## verification commands

```bash
cd apps/api && .venv/bin/python -m pytest tests/test_narrative_sanitizer.py tests/test_today_narrative_service.py tests/test_today_narrative_content_cap.py -q
python3 scripts/grace_lint.py apps/api/app
```

## expected evidence

- diff scope-файлов; вывод pytest (зелёный); список добавленных тест-кейсов;
  подтверждение, что regression-кейс «романтических разговорах» остаётся null.

## escalation rule

Потребовалось менять narrative service, selection или wire-контракт — СТОП,
доложить ревьюеру.

## no-commit rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
