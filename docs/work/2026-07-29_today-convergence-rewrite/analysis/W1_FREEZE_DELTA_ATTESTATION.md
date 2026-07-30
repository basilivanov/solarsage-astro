# W1 freeze delta-attestation

Статус на 2026-07-30: **frozen_w1**. Этот документ связывает
последний полный replay с финальным W1 source tree и фиксирует, почему
уточнение sphere registry не требовало второго полного прогона эфемерид.

## Lineage

| Артефакт | Идентификатор |
|---|---|
| replay-source checkpoint | commit `803a98a1` |
| replay fingerprint (до финальных изменений) | `90c691f0a3282f75231668a430a623dbd9bf453273608e5fcc35518740671d0e` |
| replay aggregate | `analysis/corpus_replay_tone_v3.json` (исторический report; fingerprint `90c…`) |
| freeze fingerprint | `89be0b8e7dedfc56a8858c2bfeea31c42842a8e47ea78de80350cdf883eb232d` |
| calculation version | `ss-calc-1.2.0 → ss-calc-1.3.0` |

Старый aggregate не перезаписывается: его можно воспроизвести из commit
`803a98a1`. `corpus_manifest.v1.json` в freeze tree указывает на новый
fingerprint; старый manifest и старый report доступны через Git history.

## Что изменилось после полного replay

1. Machine canon получил статус `approved_pending_freeze`, owner decision по
   hero-rate `4.9041%` и `tone-candidate-0.1`, явный `dayTone` matrix и полный
   planet/technical sphere registry.
2. Reference/direct pipeline переключён с legacy Today map на fail-closed
   `analysis/convergence_canon.py`; неизвестный фактор не получает `work`.
3. Общий `CALCULATION_VERSION` поднят до `ss-calc-1.3.0` для инвалидации
   pre-sect-fix cache keys.
4. Старые frontend/API shapes, test IDs, fixtures и fallback adapters не входят
   в новый envelope; они остаются только до атомарного W8 cutover и удаляются
   отдельным W9 allowlisted cleanup.

## Почему sphere delta семантически безопасен

`test_sphere_mapping_delta.py` проверяет четыре условия:

- домены planet keys и technical keys старого replay и нового canon совпадают;
- для любого такого ключа обе карты дают непустой результат, поэтому множество
  factors, допущенных в классификатор, не меняется;
- на representative C1 fixtures совпадают `state`, hero canonical IDs и
  `dayTone`; меняются только projected sphere labels;
- `test_convergence_mutation_fixtures.py` доказывает `len(group.spheres) ≤ 2`
  для каждой физической группы. Старый `hero_sphere_span_gt2_days` был
  day-level диагностикой нескольких групп и не является fan-out violation.

Это не заявление о real-life validity: синтетический replay проверяет механику,
а snapshot-linked check-in (§14) проверит резонанс после запуска.

## Gates

Успешные команды:

```text
PYTHONPATH=packages/py-contracts:docs/work/2026-07-29_today-convergence-rewrite/analysis \
  apps/api/.venv/bin/python -m pytest -q \
  docs/work/2026-07-29_today-convergence-rewrite/analysis/test_convergence_canon.py \
  docs/work/2026-07-29_today-convergence-rewrite/analysis/test_convergence_mutation_fixtures.py \
  docs/work/2026-07-29_today-convergence-rewrite/analysis/test_sphere_mapping_delta.py \
  docs/work/2026-07-29_today-convergence-rewrite/analysis/test_direct_replay_pipeline.py
# 14 passed

PYTHONPATH=packages/py-contracts:apps/api:apps/solarsage \
  apps/api/.venv/bin/python -m pytest -q \
  packages/py-contracts/tests/test_versions.py \
  packages/py-contracts/tests/test_boundary_configs.py \
  apps/solarsage/tests/test_geometric_sect.py \
  apps/solarsage/tests/test_calculation_core.py \
  apps/solarsage/tests/test_activation_transits.py \
  apps/solarsage/tests/test_health.py
# 46 passed
```

До изменения mapping полный replay дал `525 600 mode-days`, `invalid_ledger=0`,
`zero_public_days=0`, exact hero-rate `0.049041`, и этот aggregate остаётся
нормативным population baseline, а не квотой. Любое будущее изменение mapping,
которое нарушит domain/signature gate, обязано запускать полный replay заново.
