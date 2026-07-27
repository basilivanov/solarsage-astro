# W4-B1 TZ: TodayFactor нормализация + временная классификация (детерминированная)

Дата: 2026-07-28
Phase / Wave: **W4-TODAY-CONVERGENCE**, срез B1 (backend, pure)
Родитель: `docs/work/2026-07-27_today-premium-first-screen/21_TZ_W4_TODAY_CONVERGENCE_EVENTS_PERFORMANCE.md` (§2, §4.1–4.2, §6.3, §12.1)
Modules: новый `M-TODAY-FOCUS-BUILDER`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Goal

Pure-модуль строит нормализованные `TodayFactor` из существующих данных
(factor ledger + ActivationLayer + DayDelta) и классифицирует каждому
фактору `temporal_role` относительно локальной даты пользователя. Без
группировки/ranking/LLM (это B2).

## 2. Exact write scope

- `apps/api/app/services/today_focus_builder.py` — **новый**
  `M-TODAY-FOCUS-BUILDER`:
  - `TodayFactor` dataclass/pydantic по §4.2 (factor_id, activation_ids,
    technique/family, source/target keys, theme_keys, product_spheres,
    polarity, strength, salience, active_from, exact_at, active_until,
    phase, temporal_role).
  - `normalize_factors(ledger, activation_layer, day_delta) -> list[TodayFactor]`
    — merge по canonical factor_id (signal+activation одного фактора = один
    TodayFactor; activation_ids собираются в tuple).
  - `classify_temporal_role(factor, local_day_start, local_day_end) -> role`:
    - `anchor_today`: `exact_at` внутри `[00:00, 24:00)` локальной даты,
      либо `active_from` внутри и фактор имеет смысл «входит в действие»,
      либо DayDelta помечает как `new_today|peak`;
    - `background`: firdar/profection/return/progression/долгий транзит без
      дневного пика;
    - `supporting`: активен, связан потенциально, но не anchor/background;
    - `unrelated`: остальное.
    - Высокий strength/малый orb/многодневность НЕ делают anchor (§2.2).
  - `local_day_bounds(target_date, tzinfo) -> (datetime, datetime)` —
    UTC-границы локальной даты (zoneinfo, DST-safe).
- `apps/api/tests/test_today_focus_builder.py` — unit:
  - signal+activation одного аспекта = один TodayFactor;
  - exact_at до/после полуночи UTC → правильная локальная дата
    (Europe/Moscow и вторая зона, напр. America/New_York);
  - DST gap/fold: нет невозможного/двойного события;
  - `exact_at=None` → не anchor, часы не выдумываются;
  - сильный фактор без timing ≠ anchor;
  - годовой фирдар → background;
  - permutation входа не меняет результат.

## 3. Frozen / out-of-scope

- Группировка, ranking, state, events/spheres assembly (B2).
- Схемы public API/контракты/LLM/frontend.
- Sidecar и astronomy — не трогать.

## 4. Must-preserve

- factor_id/valence/salience/timing не принадлежат LLM (пока чистый код).
- Чистые функции, без I/O/логов факторов (только counters при need).
- GRACE-разметка + owned_tests.

## 5. Verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_today_focus_builder.py -q
```

## 6. Expected evidence

- Файлы, вывод verification, перечень кейсов с PASS.

## 7. Escalation rule

Нужен файл вне §2 — стоп, доложить. Ничего не коммить и не пушить.
