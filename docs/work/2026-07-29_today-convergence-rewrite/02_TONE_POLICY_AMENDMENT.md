# Tone policy amendment — unit → group → day

Статус: **frozen_w1 / owner-approved / full replay и final attestation завершены**.

## Почему текущая агрегация даёт «все дни тяжёлые»

В старой valence-линейке (`day_valence_service`) глобальный статус считается по
всему ledger: persistent/supporting факторы, быстрые аспекты и фон попадают в одну
сумму. В новом replay-классификаторе диагностический `tense` был ещё грубее:
`any(selected_public_unit.polarity == "tense")`. Поэтому один напряжённый unit из
трёх выбранных превращал весь день в `tense`, даже если остальные два были
supportive. Длинный транзит после первого проявления оставался в ledger каждый день.

Это не дефект эфемерид и не дефицит вычислительной мощности. Расчётные polarity
units могут быть корректными; ошибочен слой свёртки и его продуктовая семантика.

## Три разных слоя

1. `unit_polarity` — исходная polarity одной evidence-единицы:
   `supportive | tense | mixed | steady` (neutral/неизвестное → `steady`).
2. `group_polarity` — weighted balance независимых units физической группы;
   дубли одного `driver_key` считаются один раз, background не участвует,
   `mixed` делится 50/50.
3. `day_tone` — осторожная свёртка только свежих событий дня:
   `supportive | tense | mixed | steady`. Это не заменяет polarity каждой сферы
   и не должен красить 12 статических тайлов.

## W1 truth table

| условие | `day_tone` |
|---|---|
| нет свежего non-fast evidence | `steady`; длительные темы остаются context |
| свежий tense + свежий supportive | `mixed`, даже если tense ещё не проходит одиночный порог |
| high-confidence tense hero-anchor | `tense` (если нет свежей поддержки; с поддержкой → `mixed`) |
| ≥2 независимых свежих tense units | `tense` |
| high-confidence supportive hero-anchor или ≥2 независимых supportive units | `supportive` |
| один Moon/Mercury/Venus в одиночку | не меняет `day_tone`; только detail сферы |
| остальные случаи | `steady` |

`supporting`/ongoing units разрешены для `group_polarity` и контекста, но не
перезапускают общий tone ежедневно. Независимость — `distinct_driver`.

## Weighted balance

Implementation: `tone_policy_candidate.py` (`tone-candidate-0.1`).

- anchor_today weight = `strength × 1.0`;
- supporting/context weight = `strength × 0.5`;
- background weight = `0`;
- mixed unit делит свой weight между supportive/tense;
- минимальная сторона group balance = `0.25`, margin mixed = `max(0.25,
  25% от общего баланса)`.

Эти числа — explicit calibration knobs, не квота частот. Полный replay и owner
review пройдены; live-валидность будет проверяться только по snapshot-linked
check-in, не синтетическим распределением.

## Что сохраняем в audit/snapshot

Каждый результат должен хранить:

- `unit_polarity_counts` и выбранные unit IDs;
- `group_polarity`, independent driver keys и scores;
- `day_tone`, `tone_scores`, `tone_trigger_keys`;
- `context_units` отдельно;
- legacy diagnostic `legacy_any_selected_tense` только для before/after сравнения.

`tense_streak` после поправки считается по `day_tone == "tense"`, а не по наличию
одного tense unit. Старый показатель сохраняется как диагностический и не является
публичным статусом.

## Порядок работ

1. Прогнать candidate на сохранённом owner dump (сделано: 68/81 legacy tense →
   4/81 candidate tense, 3 mixed, 6 supportive; числа диагностические).
2. Добавить tone-поля в replay checkpoint и machine-readable canon; поднять
   fingerprint (сделано: `90c691f0…`).
3. Один финальный corpus replay 120 карт × 730 дней × exact/buckets/unknown
   (сделано: 120/120 `ok`, 2026-07-30).
4. Утвердить/скорректировать пороги и правило `supporting=context` по итогам
   full replay — **утверждено владельцем 2026-07-30**.
5. Freeze выполнен: hero/gate/sparse-oracle, sphere-delta и tone-audit зелёные; частота не
   используется как acceptance quota.

## Full corpus replay — результат 2026-07-30

Полный отчёт и machine-readable aggregate:

- `analysis/corpus_replay_tone_v3.md`;
- `analysis/corpus_replay_tone_v3.json`;
- checkpoint checksum `f7d74f78713d9f2f6855bdf9980ad841bc4be3f07c53187082324bbc5a8b57c8`.

Ключевой результат:

| mode | legacy tense | candidate tense | max candidate streak | hero / 30d |
|---|---:|---:|---:|---:|
| exact | 82.74% | 4.77% | 4 | 1.47 |
| bucket (диапазон 4 режимов) | 80.83–80.93% | 1.40–1.42% | 3 | 0.41–0.42 |
| unknown | 80.82% | 1.17% | 2 | 0.25 |

Tone truth-table audit дал 0 нарушений. `invalid_ledger=0`, `zero_public_days=0`,
median selected units = 3. Policy прошёл проверку как лечение tense-inflation.

После freeze остаются только runtime-волны W2–W9:

1. `CALCULATION_VERSION=ss-calc-1.3.0` и source fingerprint delta уже зафиксированы;
2. W1 строка зарегистрирована в verification matrix;
3. старые contracts остаются
   superseded и удаляются отдельным W9 cleanup после атомарного cutover.
