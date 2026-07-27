# V3 TZ: M-DAY-VALENCE — signed valence engine (family reducer, 12 assessments, day status)

Дата: 2026-07-27
Phase / Wave: **W2-VALENCE**, срез V3
Master: `docs/work/2026-07-27_today-premium-first-screen/11_TZ_W2_MASTER_VALENCE.md`
Норматив: `docs/work/2026-07-25_today-sphere-valence-correction/00_TZ.md` §6–7
Modules: новый `M-DAY-VALENCE`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Goal

Чистый движок из factor ledger (V2) и canon (V1) считает:
12 `ProductSphereAssessment` (support/tension/balance/verdict/confidence)
и global day status + breakdown — по нормативной формуле §6, без единого
отклонения. Без runtime-интеграции (это V4/V5).

## 2. Exact write scope

- `apps/api/app/services/day_valence_service.py` — **новый**
  `M-DAY-VALENCE`:
  - aspect magnitude §6.1 (aspect_weight × strength × planet weight;
    target_planet иначе source);
  - activation magnitude §6.2 (strength × family independence_weight ×
    target_weight);
  - polarity split §6.3 (supportive/tense/mixed 50/50/neutral 0);
  - family volume reducer §6.4 (rank 1/2/3 → 1.0/0.5/0.25, >3 → 0;
    отдельно global и per-sphere; neutral не занимает слотов);
  - product projection §6.5 (единый mapping из canon; factor через
    несколько technical → один раз, max magnitude, tie technical key asc);
  - assessment §6.6 (balance, verdict по порядку avoid→caution→good→neutral,
    verdict_rule closed enum, confidence);
  - global day status §6.7 (без умножения на число сфер; thresholds;
    breakdown со всеми полями);
  - сортировки и counts §7.
- `apps/api/tests/test_day_valence_engine.py` — ВСЕ 14 trap cases §14.1
  нормативного ТЗ (neutral/tense high-salience, balanced, mixed 50/50,
  signal+activation один раз, permutation invariance, 4th factor family,
  three families, technical double-map один раз, zero denominator,
  boundaries 0.75/1.30/1.50/2.00, full-precision compare).

## 3. Frozen / out-of-scope

- Константы только из canon loader (V1) — запрещено хардкодить.
- Ledger (V2) — использовать как вход, не менять.
- Runtime-интеграция, LLM, frontend, contracts regen.

## 4. Must-preserve

- salience не участвует в verdict (§6.6); LLM не меняет ничего числового.
- Determinism: permutation входа → тот же результат (тест обязателен).
- GRACE-разметка + owned_tests.

## 5. Verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_day_valence_engine.py -q
```

## 6. Expected evidence

- Файлы, вывод verification, список 14 trap cases с PASS.

## 7. Escalation rule

Нужен файл вне §2 — стоп, доложить. Ничего не коммить и не пушить.
