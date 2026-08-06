# S6 TZ — narrative + sanitizer под sphere/facet

## packet title
S6-narrative-sanitizer

## Phase / Wave
W-SPHERES-FACETS-REWORK (docs/work/2026-08-06_spheres-and-facets-rework/)

## Modules
- M-TODAY-NARRATIVE (`apps/api/app/services/today_narrative_service.py`)
- sanitizer (`apps/api/app/services/narrative_sanitizer.py`)

## goal
Narrative prompt получает `sphere`/`facet`/`polarity`/fact IDs каждого сигнала;
sanitizer знает новые 12 ключей и facets, запрещает foreign sphere/facet и
распространение полярности на всю сферу; facet=null — только общий язык сферы.
Существующий pipeline не раздваивать.

## exact write scope
- `apps/api/app/services/today_narrative_service.py`
- `apps/api/app/services/narrative_sanitizer.py`
- их тесты (apps/api/tests/*narrative*)

## frozen / out-of-scope
- units/groups/selection/canon (готово), sphere page service (S7), frontend
- capability-модель не ослаблять: capabilities.houses=false → дома не упоминаются
  в тексте (дома могут идти в prompt только как grounding, не как разрешённый claim)
- одна регенерация → summary=null — поведение сохранить

## must-preserve invariants
- `TODAY_NARRATIVE_PROMPT_VERSION` bump (новая версия шаблона).
- Fail-closed: неизвестная sphere/facet в sanitizer → grounding violation.
- Нет упоминания дома/события, которого нет в fact-pack.

## Требования
1. Prompt каждого блока: `sphere`, `facet|null`, `polarity`, source fact IDs,
   houses/planets как deterministic grounding с учётом capability-правил.
2. `narrative_sanitizer.py`: `_SPHERE_PATTERNS`/`_RELATED_SPHERES` на новые 12
   ключей + facet patterns; удалить money↔shopping, decisions связи; запрет
   foreign sphere/facet; запрет «вся сфера supportive/tense» обобщений;
   facet=null → только общий язык сферы; health — без диагнозов.
3. Тесты (мастер-ТЗ §9.3): personal_money без кредита/налога;
   financial_obligations не объявляет напряжение во всех финансах; facet=null
   не превращается в покупку/долг; houses=false — без домов; health без диагноза;
   foreign sphere/facet → reject; валидные новые keys не отклоняются.

## verification commands
```bash
cd /opt/solarsage-astro/apps/api && .venv/bin/python -m pytest tests/ -q -k "narrative"
python3 scripts/grace_lint.py apps/api/app
```

## expected evidence
- diff; pytest вывод; 2-3 примера focused fixture → verdict санитайзера.

## escalation rule
Изменение capability-модели или количества регенераций — стоп, доложить.

## no-commit rule
Ничего не коммитить и не пушить — коммит делает ревьюер.
