# 51 — W6 CONTENT-CAP GATE TZ — Today Convergence Rewrite

Controller packet по coder-loop §10.7. Архитектор: main agent. Кодер: codex CLI
(первый), cwd `/tmp/solarsage-convergence-impl`, ветка `work/today-convergence-2`.

ВАЖНО: ты и есть coder. Skill coder-loop использовать НЕЛЬЗЯ — задачу
выполняешь сам и отчитываешься здесь ревьюеру.

## 1. Packet title

W6 content-cap gate — максимальные legal payload shapes (hero 3 сферы,
quiet mainEvent + 3 импульса + lookahead) проходят bounded narrative
pipeline при `TODAY_NARRATIVE_MAX_OUTPUT_TOKENS=700` без truncation и
schema failure; per-field 220/221 gate подтверждён на границе.

## 2. Phase / Wave

W-TODAY-CONVERGENCE-REWRITE / W6 gate (05 §4, строки 170-183) — до W8.

## 3. Modules

- Tests: `apps/api/tests/test_today_narrative_content_cap.py` (новый)
- Только при необходимости: `apps/api/app/services/today_narrative_service.py`
  (если gate выявит дефект — сначала эскалация, см. §12).

## 4. Goal

Один тестовый модуль доказывает, что при max legal shapes:
1. prompt, построенный `generate_today_narrative`, содержит только selected
   units (не весь ledger) и укладывает max ответ в 700 output tokens;
2. max валидный narrative (все claims заполнены) проходит всю валидацию
   (`contentState=ready` на уровне service result);
3. `summary.text` 220 chars принимается, 221 — отклоняет весь narrative
   (boundary, уже частично покрыто — здесь зафиксировать рядом с cap);
4. измерение output tokens фиксируется тем же механизмом, что и
   production path (`output_tokens` в Success/log payload).

## 5. Норматив (прочитать перед кодированием)

- `docs/work/2026-07-29_today-convergence-rewrite/05_W5_W8_OPERATIONS_AND_RELEASE_TZ.md`
  §4 (:170-183) — content-cap gate условия.
- `apps/api/app/services/today_narrative_service.py` (P6, в HEAD):
  `generate_today_narrative`, `build_today_narrative_prompt`,
  TodayNarrativeSuccess/Failure, error codes.
- `apps/api/tests/test_today_narrative_service.py` — fake LLM pattern.
- Frontend fixtures №4/№8 как эталон shapes:
  `__tests__/fixtures/today_convergence_v2/04_hero_three_spheres.json`,
  `08_quiet_main_max.json` — для формы blocks (wire), НЕ для прямого
  импорта (backend snapshot builder ниже).

## 6. Exact write scope

- `apps/api/tests/test_today_narrative_content_cap.py` (новый, только он)

## 7. Frozen / Out of scope

- Production код не менять (при дефекте — эскалация §12). Frontend не
  трогать. Реальный LLM не вызывать.

## 8. Требования к тестам

### 8.1 Max-shape snapshots (in-memory builders)

Построить два `TodaySnapshot`-подобных объекта (по образцу
test_today_narrative_service.py builders):

- `hero_max`: convergence_today, 3 группы × evidence пара, union 3 сфер
  (соответствует fixture №4 shape), exact birth mode, каждый event с
  полным окном.
- `quiet_max`: quiet_day, mainEvent + 3 импульса + (lookahead в snapshot
  не входит — это projection-поле, в narrative prompt не участвует —
  зафиксировать это комментарием), все events с partofday (bucket mode).

### 8.2 Content-cap доказательства

- Fake LLM: принимает prompt, возвращает max валидный narrative (claims
  для всех блоков, summary ~200 chars, meaning/action заполнены,
  sourceEventIds корректные) и сообщает `output_tokens` через
  provider-ответ (тот же механизм, что production извлекает — смотри
  `_provider_text`/`_output_tokens` в service).
- Assert: fake получил `max_output_tokens == 700` (assert на
  settings/fake capture).
- Assert: result — `TodayNarrativeSuccess`, `content_json` проходит
  round-trip валидацию projection-стороны
  (`today_convergence_projection._apply_narrative` НЕ вызывать — вместо
  этого проверь, что content проходит собственную валидацию service и
  claims ⊆ block ids).
- Assert: возвращённый `output_tokens` равен значению из provider-ответа
  (механика измерения).
- Assert: prompt НЕ содержит `factor_units`/audit ключи и количество
  `evt_` вхождений == selected events count (не весь ledger).
- Boundary: summary 220 chars принят; 221 — `TodayNarrativeFailure` с
  claim/schema кодом (уточнить фактический error_code из service).
- Truncation guard: fake возвращает JSON, обрезанный на середине
  (невалидный JSON) → typed failure (schema_invalid), не частичный
  accept.

### 8.3 GRACE

Тестовый модуль с MODULE_CONTRACT/MAP (owned_tests: self).

## 9. Must-preserve invariants

- Полный backend suite зелёный; ruff/grace lint по файлу PASS.

## 10. Verification

```bash
cd /tmp/solarsage-convergence-impl/apps/api
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_narrative_content_cap.py -q -p no:cacheprovider 2>&1 | tail -2
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest tests/ -q \
  -m "not integration and not benchmark" -p no:cacheprovider 2>&1 | tail -2
/opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check \
  tests/test_today_narrative_content_cap.py
cd /tmp/solarsage-convergence-impl && \
  python3 scripts/grace_lint.py apps/api/tests/test_today_narrative_content_cap.py
```

## 11. Expected evidence

- Вывод §10; список asserts по §8.2 с отметками; фактические значения
  output_tokens/max_output_tokens из тестового прогона.

## 12. Escalation rule

Max legal shape НЕ проходит pipeline при 700 (дефект prompt/валидации) →
СТОП, зафиксировать фактический дефицит/дефект в отчёте — это повод для
owner-решения (сокращение prompt/полей, НЕ повышение cap без измерения).
Нужно менять production файлы → эскалация.

## 13. No-commit rule

Ничего не коммить и не пушить — коммит делает ревьюер.
