# S1 TZ — replay instrumentation + baseline signatures

## packet title
S1-replay-instrumentation

## Phase / Wave
W-SPHERES-FACETS-REWORK (docs/work/2026-08-06_spheres-and-facets-rework/)

## Modules
- replay analysis tooling (docs/work/2026-07-29_today-convergence-rewrite/analysis/)

## goal
Расширить существующий corpus replay так, чтобы отчёт содержал доказательства,
требуемые мастер-ТЗ §10 (счётчики по sphere, старые ключи, repeated-sphere,
per-day physical signatures), и подготовить fingerprint к новым файлам канона.
Поведение расчёта дня НЕ меняется — только телеметрия/отчётность.

## exact write scope
- `docs/work/2026-07-29_today-convergence-rewrite/analysis/corpus_replay.py`
- `docs/work/2026-07-29_today-convergence-rewrite/analysis/generate_corpus_manifest.py`
- тесты рядом с analysis, если у replay есть свои test-файлы (проверить)

## frozen / out-of-scope
- `apps/api/**` (production код не трогаем в этом срезе)
- `grace/canon/**`
- физическая формула: classify/tone/grouping логика в analysis-файлах не меняется

## must-preserve invariants
- CLI-флаги и их defaults корпуса не ломать (`--residues`, `--workers`, `--resume` и т.д.).
- Существующие поля отчёта не переименовывать (baseline/candidate сравнение опирается на них).
- replay должен по-прежнему проходить на текущем коде без ошибок.

## Что добавить

1. `generate_corpus_manifest.py` `FINGERPRINT_FILES`: добавить
   - `grace/canon/today_convergence_themes.v1.yml`
   - `grace/canon/product_spheres.v1.yml` — include-if-exists (файл появится в S2; отсутствие не должно падать)
   - production projection файлы: `apps/api/app/services/today_convergence_canon.py`, `today_convergence_units.py`, `today_convergence_groups.py`, `today_convergence_selection.py`, `today_convergence_tone.py`
   - include-if-exists для отсутствующих файлов обязателен.
2. `corpus_replay.py` — per-day physical signature export (JSONL, одна строка на день/карту/birth-mode):
   `canonical_event_ids`, `group_ids` (+ member ids), driver/independence keys, hero anchor/confirmation ids,
   hero evidence level, group polarity, `dayTone`, `state`, selected group/event ids.
   Это verification baseline для сравнения baseline→candidate по мастер-ТЗ §10.3.
3. Aggregate-счётчики в финальный отчёт:
   - count выбранных сигналов по sphere;
   - число дней, где в выбранном top-N ≥2 сигнала одной sphere (repeated-sphere days);
   - occurrences старых keys `decisions`/`shopping` (сейчас легальны; после S2 должны стать 0);
   - group-without-sphere / unmapped на стороне analysis-пайплайна (что есть — посчитать честно);
   - поля `facet` пока нет — счётчики facet/null и invalid facet добавить как tolerant-чтение
     (`getattr`-стилем), чтобы S3 мог их наполнить без правки replay.
4. `--allow-source-drift` и проверку fingerprint не трогать.

## verification commands
```bash
cd /opt/solarsage-astro
apps/api/.venv/bin/python docs/work/2026-07-29_today-convergence-rewrite/analysis/corpus_replay.py \
  --output-dir /var/tmp/s1-smoke --residues 0 --limit-charts 2 \
  --from-date 2026-07-01 --to-date 2026-07-05 --workers 2 --allow-source-drift
```
Ожидание: exit 0, в output есть per-day signatures JSONL и aggregate-отчёт с новыми полями.

## expected evidence
- diff двух файлов;
- вывод verification run (кратко: charts ok, errors=0);
- пример одной строки signature JSONL + фрагмент aggregate-отчёта с новыми счётчиками.

## escalation rule
Если для счётчиков нужно менять analysis-pipeline расчёт (не только читать результаты) — стоп, доложить, новый packet.

## no-commit rule
Ничего не коммитить и не пушить — коммит делает ревьюер.
