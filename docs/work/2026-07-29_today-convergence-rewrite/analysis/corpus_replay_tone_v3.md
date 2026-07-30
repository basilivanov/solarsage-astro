# Today convergence — full corpus tone replay v3

Дата завершения: 2026-07-30 01:59 MSK
Статус: **расчёт PASS; tone-inflation fix PASS; W1 freeze REVISE до продуктового решения и двух контрактных gates**.

Этот отчёт фиксирует наблюдаемое распределение, а не квоту, под которую разрешено
подбирать пороги. Корпус синтетический: он проверяет воспроизводимость, целостность
и распределения модели, но не доказывает совпадение прогноза с прожитым днём.

## Lineage и объём

- 120 синтетических карт: 24 географии × 5 карт;
- 2025-01-01 .. 2026-12-31: 730 дней на карту;
- 6 публичных режимов: `exact`, 4 birth-time bucket и `unknown`;
- 87 600 person-days на режим, 525 600 классифицированных mode-days суммарно;
- source fingerprint: `90c691f0a3282f75231668a430a623dbd9bf453273608e5fcc35518740671d0e`;
- checkpoint-set checksum: `f7d74f78713d9f2f6855bdf9980ad841bc4be3f07c53187082324bbc5a8b57c8`;
- machine report: `corpus_replay_tone_v3.json` (SHA-256 `1ee1e0629bd06cc418f7c761584524eee752ffd1983044516ad46d4f745939d1`);
- isolated server image: `solarsage-corpus-replay:90c691f0a3282f75231668a430a623dbd9bf453273608e5fcc35518740671d0e`.

## Integrity

- 120/120 checkpoints `status=ok`, ошибок 0;
- chart IDs уникальны, date range и source fingerprint едины;
- `invalid_ledger=0` во всех режимах;
- `zero_public_days=0` во всех режимах;
- median selected public units = 3 во всех режимах;
- дней без selected public unit: exact 0; каждый bucket 1–2; unknown 2 из 87 600;
- local/server 14-day parity pilot до full run: semantic output идентичен;
- tone-gate audit: 0 случаев `tense` без high-confidence tense anchor или двух
  независимых fresh tense units; 0 аналогичных нарушений для `supportive`;
- max public tense streak: exact 4 дня, bucket 3, unknown 2.

## Итоговое распределение

Tone-колонки взаимоисключающие и суммируются в 30 дней. `hero` — ортогональный
признак и может совпадать с любым tone.

| birth-time mode | hero rate | hero / 30d | steady / 30d | supportive / 30d | mixed / 30d | tense / 30d | legacy tense / 30d |
|---|---:|---:|---:|---:|---:|---:|---:|
| exact | 4.904% | 1.47 | 24.79 | 1.94 | 1.84 | 1.43 | 24.82 |
| night | 1.373% | 0.41 | 28.51 | 0.53 | 0.54 | 0.42 | 24.27 |
| morning | 1.392% | 0.42 | 28.49 | 0.55 | 0.54 | 0.42 | 24.28 |
| day | 1.397% | 0.42 | 28.50 | 0.55 | 0.52 | 0.43 | 24.25 |
| evening | 1.390% | 0.42 | 28.48 | 0.55 | 0.55 | 0.42 | 24.26 |
| unknown | 0.835% | 0.25 | 28.69 | 0.47 | 0.49 | 0.35 | 24.25 |

Разброс между exact-картами (P10–P90, дней на 30): hero 1.02–1.98,
supportive 1.36–2.47, mixed 1.32–2.47, tense 1.07–1.85. Для unknown hero
P10–P90 = 0.08–0.45; минимум одной карты = 0 hero за два года.

## Что доказано

1. Корень «все дни тяжёлые» был в агрегации, а не в эфемеридах. Старое правило
   помечало tense 80.8–82.7% дней; candidate policy оставляет tense 1.2–4.8%.
2. Исправление не обнулило сигнал: exact даёт около 5.2 non-steady tone-days в
   месяц, bucket около 1.5, unknown около 1.3. Hero и обычные импульсы остаются.
3. `steady` не означает пустой экран. Median significant/independent units:
   exact 48/11, bucket 13/7, unknown 11/7; presentation стабильно выбирает 3.
4. Неопределённое время честно снижает смелость вывода, но не лишает пользователя
   персональных фактов.

## Что не доказано и требует решения

1. Population exact hero-rate 4.9% ниже monitoring hypothesis 8–20% и ниже
   owner probe 8/81. Пороги запрещено крутить ради квоты; владелец должен принять
   частоту около 1.5 hero/месяц либо содержательно пересмотреть определение hero.
2. В public API sketch пока нет ортогонального `dayTone`. До W7 требуется контракт:
   `state` × `dayTone` × `contentState`, где `quiet_day + steady` не скрывает
   детерминированные импульсы.
3. Exact имеет 196 hero-days, где объединённый span всех hero-групп дня превышает
   две сферы. Это не доказывает per-group fan-out, но freeze требует отдельного
   group-level gate `primary + secondary_max=1`.
4. Сферы больше не схлопываются в `decisions`, но остаётся естественный/возможный
   mapping skew: среди exact hero sphere mentions лидируют work 2683 и money 1704.
   Нужен group-level primary/secondary отчёт, прежде чем считать mapping закрытым.
5. Sparse-oracle/shifted-grid не запускался на всех 120×730 в этом run; используется
   ранее зелёный стратифицированный oracle. Full dense oracle остаётся отдельным
   дорогим диагностическим прогоном, не условием tone-вывода.

## Вердикт

Candidate `tone-candidate-0.1` можно считать прошедшим корпусную проверку как
лечение tense-inflation: целостность зелёная, gate violations отсутствуют, streak
ограничен. Нельзя молча замораживать весь W1: сначала зафиксировать продуктовую
частоту hero, добавить `dayTone` в public/W7 contract и доказать per-group sphere cap.

## Воспроизведение агрегации

```bash
python docs/work/2026-07-29_today-convergence-rewrite/analysis/aggregate_corpus_shards.py \
  <local-run-dir> <remote-run-dir> \
  --expected-charts 120 \
  --json-output docs/work/2026-07-29_today-convergence-rewrite/analysis/corpus_replay_tone_v3.json \
  --markdown-output /tmp/corpus_replay_generated.md
```

Полные checkpoints не коммитятся; серверный набор сохранён в изолированном
`/var/tmp/solarsage-replay-90c691f0a3282f75231668a430a623dbd9bf453273608e5fcc35518740671d0e/output/full-tone-remote-v3`.
