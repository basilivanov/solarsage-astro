# W4-B2 TZ: группировка в сюжет, ranking, состояния, TodayFocus assembly

Дата: 2026-07-28
Phase / Wave: **W4-TODAY-CONVERGENCE**, срез B2 (backend, pure)
Родитель: `docs/work/2026-07-27_today-premium-first-screen/21_TZ_W4_TODAY_CONVERGENCE_EVENTS_PERFORMANCE.md` (§2.5–2.6, §3, §4.3–4.5, §5, §12.1)
База: `apps/api/app/services/today_focus_builder.py` (B1, в main)
Modules: `M-TODAY-FOCUS-BUILDER`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Goal

Из нормализованных TodayFactor (B1) строится детерминированный `TodayFocus`:
группировка связанных факторов, ranking, ровно одно состояние продукта,
0–3 public events и 0–3 featured spheres. Без LLM, без public API wiring
(это W4-C).

## 2. Exact write scope

- `apps/api/app/services/today_focus_builder.py` — доработка:
  - `build_today_focus(factors, *, valence_assessments, tz_name, target_date) -> TodayFocusResult`
    (внутренний typed result; public схемы — W4-C).
  - **Grouping §4.3**: seed на каждый `anchor_today`; связь только строгая
    (общий `target_key` ИЛИ общая узкая `theme_key` + общая product sphere);
    один фактор — только в одну public группу (наиболее связная);
    background присоединяется к готовой группе, не создаёт её;
    группа без второго независимого фактора → single_impulse.
  - **Ranking §4.4** (лексикографический): точность даты → число факторов
    (cap 3) → число families/horizons → target_key-связь выше theme-only →
    сумма effective magnitude (существующий family reducer) → min factor_id.
  - **State §3**: ровно одно из convergence_today / single_impulses /
    background_only / no_accent (unavailable — только при невалидном входе).
  - **Events**: из выбранной группы/импульсов, 0–3, сортировка по occurs_at+id;
    kind exact|starts|peak|building|separating; «пик завтра» только с явной
    пометкой; `local_date` обязана совпадать с target_date для exact|starts|peak.
  - **Featured spheres §4.5**: только при convergence_today, 0–3, порядок:
    factor coverage → anchor coverage → salience → confidence → canonical key.
- `apps/api/tests/test_today_focus_builder.py` — кейсы §12.1 (1–9, 13):
  фирдар→background_only; один exact→single_impulses; два связанных+exact→
  convergence; два несвязанных exact→два события без convergence;
  signal+activation=1 фактор; factor в 3 сферах=count 1; фон не создаёт
  convergence; permutation stable; caps 0..3 featured.

## 3. Frozen / out-of-scope

- Public pydantic/TodayFocus API схемы, payload integration, LLM (W4-C).
- Frontend. Sidecar.

## 4. Must-preserve

- Ranking полностью backend-owned и детерминирован (permutation test обязателен).
- Нет скрытого LLM-score, нет сортировки по тексту.
- B1-функции/контракты не ломать (существующие тесты зелёные).

## 5. Verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_today_focus_builder.py -q
```

## 6. Expected evidence

- Diff файла, вывод verification, список кейсов §12.1 с PASS.

## 7. Escalation rule

Нужен файл вне §2 — стоп, доложить. Ничего не коммить и не пушить.
