# S11 TZ — replay smoke + candidate gates

## packet title
S11-replay-candidate

## Phase / Wave
W-SPHERES-FACETS-REWORK

## goal
Candidate-код (текущий HEAD) проходит replay gates мастер-ТЗ §10.4–10.5:
smoke без ошибок/unmapped/old-keys, затем полный корпус и сравнение physical
signatures с baseline.

## Контекст
- Replay instrumentation: S1 (уже в main). Baseline крутится: output
  `/var/tmp/spheres-baseline/` (physical_signatures.jsonl + aggregate.json),
  worktree `.worktrees/spheres-baseline` (pre-change commit 05c8664a).
- Analysis-пайплайн (`docs/work/2026-07-29_today-convergence-rewrite/analysis/convergence_canon.py`)
  ещё на СТАРОЙ fan-out модели — replay gates требуют parity с production
  resolver'ом. Это часть этого среза: синхронизировать analysis projection с
  production `resolve_product_sphere` (мастер-ТЗ §10.1) и перегенерировать
  candidate manifest.

## exact write scope
- `docs/work/2026-07-29_today-convergence-rewrite/analysis/convergence_canon.py`
- связанные analysis helpers/tests (`analysis/test_convergence_canon.py` и др.)
- `docs/work/2026-08-06_spheres-and-facets-rework/` (verification notes)

## frozen / out-of-scope
- `apps/api/**` (production заморожен), frontend
- baseline-вывод `/var/tmp/spheres-baseline/` — не трогать
- physical формула (classify/tone/grouping) не меняется — только product projection

## must-preserve invariants
- Analysis и production resolver дают одинаковые (sphere, facet) на одинаковых
  входах — parity fixtures обязательны.
- Physical signature поля (event IDs, group IDs, hero, dayTone, polarity, state)
  candidate обязаны совпасть с baseline на одинаковых входах.

## Требования
1. Синхронизировать `analysis/convergence_canon.py` с production resolver'ом
   (та же таксономия product_spheres.v1.yml; убрать planet_to_product fan-out,
   _MAX_PLANET_SPHERES и пр.). Parity-тесты: одинаковые входы → одинаковый выход
   с production `resolve_product_sphere`.
2. Перегенерировать candidate manifest штатным генератором (fingerprint нового кода).
3. Smoke replay candidate (команда мастер-ТЗ §10.4): errors=0, unmapped=0,
   old keys (decisions/shopping)=0, facet валиден или null, repeated-sphere
   группы не теряются. Отчёт в
   `docs/work/2026-08-06_spheres-and-facets-rework/replay-smoke-candidate.md`.
4. Если baseline ещё бежит — НЕ ждать; полный candidate replay запустит ревьюер.

## verification commands
```bash
cd /opt/solarsage-astro
apps/api/.venv/bin/python docs/work/2026-07-29_today-convergence-rewrite/analysis/corpus_replay.py \
  --output-dir /var/tmp/spheres-smoke --residues 0,1,2,3,4 --limit-charts 5 \
  --from-date 2026-07-01 --to-date 2026-07-30 --workers 4
cd apps/api && .venv/bin/python -m pytest ../docs/work/2026-07-29_today-convergence-rewrite/analysis/ -q -k "canon or parity" 2>/dev/null || true
```

## expected evidence
- diff analysis-файлов; parity test вывод; smoke replay aggregate (errors=0,
  unmapped=0, old keys=0); заметка о готовности к полному прогону.

## escalation rule
Несовпадение physical signatures на smoke с baseline-поведением — стоп,
доложить (product projection вмешалась в формулу — запрещено ТЗ).

## no-commit rule
Ничего не коммитить и не пушить — коммит делает ревьюер.
