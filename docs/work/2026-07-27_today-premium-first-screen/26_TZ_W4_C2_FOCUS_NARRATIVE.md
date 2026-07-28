# W4-C2 TZ: LLM core narrative + детерминированные human titles

Дата: 2026-07-28
Phase / Wave: **W4-TODAY-CONVERGENCE**, срез C2 (backend)
Родитель: `docs/work/2026-07-27_today-premium-first-screen/21_TZ_W4_TODAY_CONVERGENCE_EVENTS_PERFORMANCE.md` (§6, §7, §12.1-12.2)
База: `today_focus_builder.py` + payload integration (C1, в main)
Modules: новый `M-FOCUS-TITLE-BUILDER`, `M-API-LLM-SERVICE`, `M-TODAY-SERVICE`, `M-API-LLM-CLAIM-VALIDATOR`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Goal

1. **Human titles детерминированно** (без LLM): события получают
   человеческие названия («Марс напротив твоего Нептуна») вместо
   «Луна Плутон» / «SOLAR Плутон».
2. **Один structured LLM core-вызов**: `convergence.summary`,
   `events[*].meaning`, `featured_spheres[*].summary+action` — атомарно
   валидированный, без fallback. `contentState` ready/unavailable/not_needed.

## 2. Human titles (M-FOCUS-TITLE-BUILDER, pure)

- `apps/api/app/services/focus_title_builder.py` — **новый**:
  `build_event_title(factor) -> (human_title, technical_title)`.
- Aspect-формы (падежи русских названий планет задать константами):
  - square / opposition: «{Source RU} в напряжении с твоим {Target RU-inst}»
    (opposition допускает «{Source RU} напротив твоего {Target RU-inst}»);
  - trine / sextile: «{Source RU} в гармонии с твоим {Target RU-inst}»;
  - conjunction: «{Source RU} сошлась с твоим {Target RU-inst}»;
  - quincunx / semi_square / sesquisquare: «в напряжении с».
- Дом/лот/угол (target_type != natal_planet): «{Source RU} в твоём {N доме}» /
  «{Source RU} у {Lot RU}» — без machine keys (NECESSITY и пр. — только
  human label или скрытие event из public, если title не строится честно).
- Slow layers (firdar/profection/return/solar/lunar): человеческий формат
  «Соляр: {Planet RU} — тема года» / «Профекция: {Planet RU} в фокусе»;
  но public events только anchor_today (уже решено в C1).
- technical_title: короткий technical с human пояснением, БЕЗ Transit_/Natal_
  префиксов и machine ids.
- Тесты: все аспект-формы, падежи, лоты/дома, длинные названия.

## 3. LLM core (один вызов)

- `apps/api/app/services/llm_service.py` — `generate_focus_narrative(
  focus_input) -> dict | None`: строгий structured JSON:
  `{convergence_summary: str, event_meanings: {event_id: str},
  featured_spheres: {key: {summary, action}}}`.
- Input — только compact evidence pack: state, до 3 events (title+kind+time),
  до 3 background/supporting facts, до 3 featured spheres + их verdicts,
  stable IDs (проверка claims).
- Лимиты: summary ≤220, meaning ≤160, sphere summary ≤140, action ≤100.
  Тон §6.4 (может/вероятнее, без фатализма, без астротерминов, без повтора
  одного смысла в summary и action).
- Output budget: max_tokens ≤ 700. Prompt version bump (TODAY_LLM_PROMPT_VERSION 3→4).

## 4. Применение атомарно + contentState

- `apps/api/app/services/today_service.py`: после детерминированного focus:
  - state ∈ {convergence_today, single_impulses} → LLM narrative;
  - иначе → `content_state="not_needed"`, без вызова.
  - Успех+валидация → применить поля, `content_state="ready"`.
  - ЛЮБАЯ ошибка/невалидность одного обязательного поля → ВСЕ LLM-owned поля
    null (summary/meanings/actions), `content_state="unavailable"`
    (детерминированные факты остаются). Никакой частичной публикации.
  - Кеш: `content_state` и поля входят в payload; `unavailable` не
    маскируется под ready.
- `apps/api/app/services/llm_claim_validator.py` — `check_focus_narrative_safety`:
  banned-жаргон (S1), лимиты длины, обязательные ключи по входным IDs
  (каждый event id и каждый featured key обязан иметь свои поля; лишние
  ключи — reject).

## 5. Frozen / out-of-scope

- Frontend (W4-F), sidecar, ranking/grouping (B2 не трогать).
- Новые LLM-вызовы (только один), модель, дедлайны.
- Cache/prompt version bump дальше указанного (по решению ревьюера при rollout).

## 6. Must-preserve

- LLM не владеет facts/time/state/ranking (request spy-тест §15 родителя).
- S1 no-fallback: никакого универсального текста при неуспехе.
- Детерминированные facts доступны при любом contentState.

## 7. Verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q -k "focus"
```

## 8. Expected evidence

- Файлы, вывод verification, 3 примера human titles (из живых anchors
  28.07) и пример narrative JSON (mock).

## 9. Escalation rule

Нужен файл вне §2–§4 / второй LLM-вызов — стоп, доложить. Ничего не
коммить и не пушить.
