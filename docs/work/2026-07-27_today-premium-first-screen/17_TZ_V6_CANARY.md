# V6 TZ: sanitized fixtures + canary shadow report + missing acceptance tests

Дата: 2026-07-27
Phase / Wave: **W2-VALENCE**, срез V6
Master: `docs/work/2026-07-27_today-premium-first-screen/11_TZ_W2_MASTER_VALENCE.md`
Норматив: `docs/work/2026-07-25_today-sphere-valence-correction/00_TZ.md` §8.3, §14.2–14.3, §16 Release A
Modules: fixtures/audit tooling, `M-DAY-VALENCE`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Goal

- Sanitized factor-входы (без birth data/ПДн) для 3 canary-дней построены и
  сохранены как repo fixtures; на них зафиксирован old/new shadow отчёт.
- Пробел приёмки V5 закрыт тестами: 12 assessments в selected payload,
  counts==12, LLM spy (LLM не владеет numeric/verdict полями).

## 2. Exact write scope

- `apps/api/tests/fixtures/day_valence/` — 3 sanitized canary fixtures:
  - `P-BASIL-2026-07-25` (balanced, tense medium/fast);
  - `P-BASIL-2026-07-23` (tense day при старом good=11 trap);
  - один synthetic low-evidence day.
  Формат: normalized day signals + activations (factor-вход V2 ledger),
  БЕЗ birth data, городов, имён — уже обезличенный вход.
  Источник: извлечь из dev/prod БД владельца нормализованные
  signals/activations за эти даты (только factor-поля).
- `apps/api/tests/test_day_valence_canary.py` — canary тесты: на каждом
  fixture ledger→engine, фиксация day status, 12 verdict, duplicate count;
  snapshot-допуск без hardcoded распределения (§13: нельзя требовать
  целевое распределение).
- `apps/api/tests/test_day_valence_selected_payload.py` — acceptance V5:
  selected (ENABLED=true) payload: 12 assessments, counts==12,
  verdict_rule closed enum, audit.valence_version,
  audit.day_status_breakdown заполнены.
- `apps/api/tests/test_day_valence_llm_boundary.py` — spy: LLM request
  shape не содержит numeric assessment/verdict/balance полей.
- `docs/work/2026-07-27_today-premium-first-screen/shadow-report-v6.md` —
  отчёт: на canary fixtures old/new day status, verdict-count diff,
  duplicate counts, выводы (текстом).

## 3. Frozen / out-of-scope

- Включение флагов где-либо (делает ревьюер отдельно на деве).
- Изменение runtime-кода (должен пройти на существующем; баг — стоп,
  доложить).
- ПДн в fixtures — категорически.

## 4. Must-preserve

- Fixtures sanitized (тест-скан на запрещённые поля: birth*, name, city,
  lat/lon, username).
- Все существующие тесты зелёные.

## 5. Verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_day_valence_canary.py tests/test_day_valence_selected_payload.py tests/test_day_valence_llm_boundary.py -q
```

## 6. Expected evidence

- Вывод verification; shadow-report-v6.md; подтверждение sanitized-скана.

## 7. Escalation rule

Нужен runtime-fix — стоп, доложить с фактом failing case. Ничего не
коммить и не пушить.
