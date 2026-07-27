# V2 TZ: M-DAY-FACTOR-LEDGER — canonical factor identity + cross-source dedup

Дата: 2026-07-27
Phase / Wave: **W2-VALENCE**, срез V2
Master: `docs/work/2026-07-27_today-premium-first-screen/11_TZ_W2_MASTER_VALENCE.md`
Норматив: `docs/work/2026-07-25_today-sphere-valence-correction/00_TZ.md` §5
Modules: новый `M-DAY-FACTOR-LEDGER`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Goal

Чистый модуль строит canonical factor ledger из day signals + active
activations: semantic identity, нормализация, cross-source dedup по
нормативу §5. Без runtime-интеграции (это V4).

## 2. Exact write scope

- `apps/api/app/services/day_factor_ledger.py` — **новый**
  `M-DAY-FACTOR-LEDGER`:
  - `build_factor_ledger(day_signals, activations) -> FactorLedger`
    (factors list + duplicate count + invalid count).
  - Semantic keys по §5.2: `aspect:<planet>:<aspect_type>:<target_type>:<target_key>`,
    `house:<planet>:<house_number>`, `activation:<activation_id>`.
  - Нормализация §5.2: strip `Transit_`/`Natal_`, uppercase planet keys,
    lowercase aspect type; без display labels; missing обязательная часть →
    factor invalid (не падает, считается в invalid count).
  - Dedup §5.3: active ActivationEvidence побеждает AstroSignal при
    совпадении semantic key; повторный activation ID отклоняется (count);
    одинаковые day signals с одним key → max strength; tie → factor_id asc;
    excluded duplicates только в counter.
- `apps/api/tests/test_day_factor_ledger.py` — unit + property fixtures:
  - signal↔activation parity для `transit_to_natal`, `transit_to_angle`,
    `transit_to_lot`, `transit_planet_in_house` (§5.3);
  - duplicate activation ID отклоняется;
  - permutation входа не меняет ledger (determinism);
  - invalid factor fail-closed без исключений.

## 3. Frozen / out-of-scope

- Valence-математика (V3), интеграция в scoring (V4), canon файл (V1 —
  использовать через его loader, не дублировать константы).
- Любые существующие сервисы, LLM, frontend.

## 4. Must-preserve

- Ledger НЕ содержит human/LLM text и ПДн (§5.1).
- Чистые функции, без I/O, без логирования факторов (только counters).
- GRACE-разметка + owned_tests.

## 5. Verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_day_factor_ledger.py -q
```

## 6. Expected evidence

- Файлы, вывод verification, список property fixtures с результатами.

## 7. Escalation rule

Нужен файл вне §2 или существующий runtime — стоп, доложить. Ничего не
коммить и не пушить.
