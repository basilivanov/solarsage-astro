# W2-VALENCE V6 Shadow Report

Дата: 2026-07-27
Статус: Shadow Audit Complete (V6)

## 1. Обзор canary-прогона

Сравнение вычислений legacy scoring (`ss-scoring-2.0`) и нового valence engine (`day-valence-1.0`) на 3 обезличенных canary-fixtures.

| Fixture | Legacy Status | Valence Status | Legacy Verdict Counts | New Valence Verdict Counts | Duplicate Factors |
|---|---|---|---|---|---|
| `P-BASIL-2026-07-25` | `steady` | `supportive` | `good=11, caution=1, avoid=0` | `good=3, caution=0, avoid=0, neutral=9` | 0 |
| `P-BASIL-2026-07-23` | `tense` | `tense` | `good=11, caution=1, avoid=0` | `good=0, caution=2, avoid=3, neutral=7` | 0 |
| `synthetic_low_evidence` | `steady` | `steady` | `good=0, caution=0, avoid=0` | `good=0, caution=0, avoid=0, neutral=12` | 0 |

---

## 2. Ключевые выводы

1. **Устранение ложного `good=11` при `day_status=tense` (`P-BASIL-2026-07-23`)**:
   - В старой схеме salience ошибочно маркировалась как `good`, в результате чего для напряжённого дня (где действуют квадры и оппозиция Марса/Плутона к Сатурну) UI показывал 11 вердиктов «Поддержка».
   - Новый valence engine считает честный signed valence из factor ledger: напряжённые факторы правильно формируют вердикты `avoid` и `caution` для сфер `work`, `money`, `decisions`, `crisis_transformation_control`.

2. **Grounded low-evidence fallback (`synthetic_low_evidence`)**:
   - При отсутствии достаточных подтверждающих сигналов (total valence < 0.75) все 12 сфер честно переходят в `neutral` с решением `neutral_low_evidence`.

3. **Grounded LLM & Observability boundary**:
   - Никакие числовые оценки valence, `support_score`, `tension_score` или `balance` не передаются в LLM.
   - LLM генерирует только живые бытовые истории (`story`) и конкретные рекомендации (`advice`), полностью опираясь на детерминированно рассчитанные факты (`why[]`).

---

## 3. Готовность к релизу

- Все 14 trap cases и canary fixtures зелёные.
- PII-скан подтверждает 100% обезличенность canary fixtures.
- Contracts перегенерированы (`npm run contracts:generate`) и проверены (`pnpm contracts:check`).
