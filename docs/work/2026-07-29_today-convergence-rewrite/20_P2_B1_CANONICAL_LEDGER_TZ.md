# P2-B1 CONTROLLER PACKET — Canonical ledger, dedup and DayDelta identity

Phase / Wave: **P2 · W2-S1 deterministic convergence pipeline**

Modules: `M-TODAY-CONVERGENCE-LEDGER`, `M-TODAY-CONVERGENCE-UNITS`,
`M-TODAY-CONVERGENCE-CANON`, `M-TESTS`, `M-GRACE-PROJECT-ADAPTER`.

## Goal

Добавить pure canonical ledger между raw boundary и grouping. Наблюдаемый
результат: activation/day_signal представления одного физического события
сворачиваются в одну deterministic `CanonicalUnit`, provenance объединяется,
producer precedence не меняет identity, а DayDelta повышает temporal role только
по полному `semantic_key`, никогда по имени планеты.

Пакет также создаёт компактный immutable audit результата. Он не реализует
physical grouping, hero, sphere projection, tone, presentation или legacy
adapter.

## Authoritative inputs

- `00_MASTER_TZ.md` §4.2–4.4 и mutation fixture 2;
- `today_convergence.v1.yml::canonical_event` (`activation` before
  `day_signal`, `daydelta_contract=semantic_keys`);
- P2-A/P2-B0 production boundaries;
- frozen reference `analysis/ablation_harness.py::apply_fixed_delta_triggers`;
- `06_DEV_RELEASE_EXECUTION_PLAN_TZ.md` P2.

## Exact write scope

Кодер может создавать/изменять только:

1. `apps/api/app/services/today_convergence_ledger.py` (new);
2. `apps/api/tests/test_today_convergence_ledger.py` (new);
3. `grace/verification-matrix.md`;
4. `grace/knowledge-graph.xml`.

Файл этого packet не редактировать. Нужен иной файл — остановиться и доложить.

## Required implementation

### 1. Typed immutable result

Ввести frozen records:

- `CanonicalLedger` с deterministic tuple уникальных units и audit;
- `CanonicalLedgerAudit` как минимум с `raw_fact_count`, `accepted_fact_count`,
  `canonical_unit_count`, `duplicate_fact_count`, `duplicate_conflict_count`,
  `delta_upgraded_count`, `unmatched_delta_trigger_count`, producer counts и
  sorted immutable `excluded_by_reason`;
- typed `TodayConvergenceLedgerError` только для programming/configuration
  misuse (не sequence, invalid trigger collection и т.п.).

Один malformed raw fact не бросает весь ledger: его stable P2-A reason входит в
audit, остальные факты продолжают обрабатываться. Не-`RawPhysicalFact` item и
unknown/empty producer получают отдельные stable ledger reason tokens и не
становятся units.

Audit-only P2-A units (`background`, non-exact time-sensitive) остаются в
ledger с public flags false: audit не должен терять рассчитанный факт.

### 2. Canonical dedup

- Group key — только `canonical_event_id`; semantic key и physical window уже
  проверены P2-A.
- Один ID появляется в `ledger.units` ровно один раз.
- Winner enrichment выбирается strict producer precedence из canon:
  `activation` перед `day_signal`.
- При нескольких rows одного producer выбор deterministic и input-order
  invariant, без случайного `first row wins`. Не добавлять бизнес-эвристику по
  квоте/силе; использовать стабильный canonical comparison non-provenance
  enrichment и увеличить `duplicate_conflict_count`, если enrichment различен.
- `provenance_ids` победителя заменяются sorted union provenance всех валидных
  rows этого ID. Другие enrichment поля не смешиваются между producers.
- Unknown producer fail-closed: он не может победить или обогатить provenance.
- Units сортируются стабильным ключом, минимум `canonical_event_id`.

Producer, provenance, technical/theme enrichment и polarity не входят в event
identity. Изменение порядка raw inputs не меняет byte-equivalent ledger result.

### 3. DayDelta semantic triggers

`build_canonical_ledger(..., delta_trigger_semantic_keys=...)` принимает только
строки semantic keys и после dedup:

- exact match `unit.semantic_key` переводит eligible supporting/unrelated unit
  в `temporal_role=anchor_today` через immutable copy;
- уже anchor остаётся без счётчика upgrade;
- audit-only/background unit никогда не становится publicly eligible и не
  повышается;
- голое `SATURN`, `MOON` или другой planet name ничего не триггерит;
- unmatched unique triggers считаются в audit;
- duplicate trigger keys не удваивают counters;
- canonical ID, semantic key, provenance и eligibility не меняются.

### 4. No hidden integration

Public entrypoint работает только с `RawPhysicalFact` и optional loaded canon.
Он не импортирует `day_factor_ledger`, Today legacy schemas/services, analysis,
DB, logger, HTTP или sidecar. Producer adapter будет отдельным packet после
принятия pure pipeline.

## Frozen / out of scope

- Не менять canon/YAML, P2-A units/theme semantics или W1 rules.
- Не реализовывать direct groups, independence, hero/main_event/impulses,
  group sphere projection, polarity/dayTone, selection, replay adapter,
  snapshot, API, LLM или frontend.
- Не использовать source planet как DayDelta trigger.
- Не превращать malformed input в исключение всего дня.
- Не ослаблять существующие тесты.

## Must preserve

- Producer parity ID и prefix normalization P2-A.
- Eligibility nesting/background/time-sensitive exclusions.
- Unknown values never become `work`, general theme or public evidence.
- Pure module emits no runtime logs and has full GRACE markers/owned tests.
- Canon errors propagate fail-fast; data-row errors aggregate fail-closed.

## Tests / acceptance

Тесты обязаны доказать:

1. activation + day_signal duplicate → one unit, union provenance, activation
   enrichment wins, duplicate counter=1;
2. raw and provenance permutation gives byte-equal ledger/audit;
3. same-producer conflicting enrichment resolves deterministically and increments
   conflict count;
4. distinct physical ID remains distinct even with same driver;
5. malformed unit reasons and unknown producer aggregate without aborting valid
   rows;
6. background/time-sensitive units remain audit-only and cannot be delta-upgraded;
7. exact semantic trigger upgrades one eligible unit, planet name does not;
8. duplicate/unmatched trigger accounting is deterministic;
9. output records are immutable, units unique and sorted;
10. P2-A/P2-B0 focused suites remain green.

## GRACE sync

- Register `M-TODAY-CONVERGENCE-LEDGER` and edges to units/canon.
- Add `UC-TODAY-CONVERGENCE-W2-LEDGER` with the focused command and dedup/delta
  gates. Не выдавать этот packet за полный grouping/classifier.

## Verification commands

```bash
cd apps/api && /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_convergence_canon.py \
  tests/test_today_convergence_units.py \
  tests/test_today_convergence_ledger.py -q

cd /tmp/solarsage-convergence-impl
/opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check \
  apps/api/app/services/today_convergence_ledger.py \
  apps/api/tests/test_today_convergence_ledger.py
python3 scripts/grace_lint.py apps/api/app --quiet
bash scripts/grace/check-markers.sh
git diff --check
```

## Expected evidence

Exact changed paths; focused test count; one duplicate ID/provenance example;
one semantic-trigger/planet-name negative example; audit example; ruff,
grace_lint, marker, diff and status results.

## Escalation and no-commit rule

Если producer precedence недостаточен для deterministic enrichment, требуется
новое normative правило или нужен legacy adapter/grouping file — **остановиться**
и доложить, не изобретать W1 semantics.

**Ничего не коммить и не пушить — коммит и push делает ревьюер.**
