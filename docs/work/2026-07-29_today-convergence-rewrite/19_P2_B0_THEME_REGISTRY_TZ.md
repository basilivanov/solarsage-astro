# P2-B0 CONTROLLER PACKET — Versioned Today theme registry

Phase / Wave: **P2 · W2-S1 deterministic convergence pipeline**

Modules: `M-TODAY-CONVERGENCE-CANON`, `M-TODAY-CONVERGENCE-UNITS`,
`M-TESTS`, `M-GRACE-PROJECT-ADAPTER`.

## Goal

Закрыть обязательную входную границу для frozen `grouping.link=theme_intersection`:
добавить отдельный versioned Today theme registry и сохранить вычисленные
canonical `theme_keys` в `CanonicalUnit`. Наблюдаемый результат: production
grouping следующего packet сможет проверять узкую тему без импорта legacy
Today/horizon runtime и без подмены theme intersection пересечением широких
product spheres.

Это additive materialization уже использованных frozen replay semantics. Оно не
меняет hero-rate, пороги, eligibility, grouping или tone. Initial registry
должен быть semantic-identical существующим reference mapping
`grace/canon/horizon_selection.v1.yml::{technical_sphere_themes,target_planet_themes}`,
после чего новый Today path не импортирует этот horizon canon в runtime.

## Authoritative inputs

- `00_MASTER_TZ.md` W1 criterion: versioned theme registry;
- `grace/canon/today_convergence.v1.yml`: `grouping.link` содержит
  `theme_intersection`;
- `audit/00_PREIMPLEMENTATION_AUDIT.md` GAP-6 и SOL cross-check;
- frozen replay relation in `analysis/ablation_harness.py::_connected`;
- initial reference maps in `grace/canon/horizon_selection.v1.yml`.

## Exact write scope

Кодер может создавать/изменять только:

1. `grace/canon/today_convergence_themes.v1.yml` (new);
2. `apps/api/app/services/today_convergence_canon.py`;
3. `apps/api/app/services/today_convergence_units.py`;
4. `apps/api/tests/test_today_convergence_canon.py`;
5. `apps/api/tests/test_today_convergence_units.py`;
6. `grace/verification-matrix.md`;
7. `grace/knowledge-graph.xml` только если ownership/path dependency реально
   требует уточнения.

Файл этого packet не редактировать. Нужен иной файл — остановиться и доложить.

## Required implementation

### 1. Dedicated registry

Создать strict YAML с:

- `schema_version=today_convergence_themes.v1`;
- `status=frozen_w1`;
- `formula_version=today-convergence-2`;
- unique `canonical_order` узких theme keys;
- `technical_sphere_themes` и `target_planet_themes`.

Initial mappings и их порядок должны byte/semantic-equivalent одноимённым
секциям `horizon_selection.v1.yml`. Это migration source assertion в тесте, а
не runtime dependency. После materialization изменение старого horizon canon не
должно менять Today runtime.

Loader читает registry рядом с двумя текущими YAML, валидирует exact top-level
shape, versions, unique order, unknown theme references, non-empty unique map
values и нормализованные keys. Missing/malformed registry —
`TodayConvergenceCanonError`; fallback/implicit theme запрещены.

### 2. Pure theme projection

Добавить helper `map_factor_to_theme_keys(canon, technical_spheres,
source_key, target_key) -> tuple[str, ...]`. Он:

- использует technical map, затем source/target planet map;
- удаляет дубли и возвращает только canonical order;
- strip `Transit_`/`Natal_` и case-normalization совпадают с sphere helper;
- unknown input даёт `()`, никогда `general`, `work` или product sphere;
- не импортирует horizon/legacy services и YAML во время вызова.

### 3. Canonical unit boundary

`CanonicalUnit` получает immutable `theme_keys: tuple[str, ...]`, вычисленные
helper'ом из уже нормализованных physical inputs. Theme keys:

- не входят в `canonical_event_id` и `semantic_key` identity payload;
- не меняют significance/eligibility;
- сохраняются для следующего direct-grouping packet;
- неизвестный technical key не создаёт relation; unit может оставаться валидной,
  если её factor/sphere mapping валиден через source/target.

Producer/provenance/technical annotation mutation сохраняет canonical ID.
Изменение derived themes допускается как enrichment и позже разрешается
producer precedence при dedup; в этом packet merge ещё не реализуется.

## Frozen / out of scope

- Не менять `today_convergence.v1.yml`, `horizon_selection.v1.yml`, formula,
  fingerprint или replay artifacts.
- Не реализовывать grouping, dedup/producer precedence, hero, projection группы,
  selection, tone, adapter, snapshot, HTTP или frontend.
- Не использовать product sphere intersection вместо narrow theme intersection.
- Не импортировать legacy Today schemas/services или analysis runtime.
- Не ослаблять и не удалять существующие тесты.

## Must preserve

- Все P2-A identity, significance, eligibility и fail-closed tests.
- Theme registry — отдельный source of truth нового Today после initial parity.
- Unknown theme никогда не создаёт связь.
- GRACE headers/maps/owned_tests остаются истинными; pure layer emits no logs.

## Tests / acceptance

Тесты обязаны доказать:

1. repository registry strict-load и immutable typed extraction;
2. malformed version/order/unknown theme/missing file fail closed;
3. committed initial mappings semantic-identical двум reference maps старого
   horizon canon, без production import;
4. known technical/source/target mapping, canonical order и dedup;
5. unknown technical/factor mapping не создаёт theme fallback;
6. unit получает expected themes, tuple immutable/deterministic;
7. изменение technical annotation может менять themes, но не canonical ID;
8. producer/prefix parity и весь P2-A suite остаются зелёными.

## GRACE sync

Обновить `UC-TODAY-CONVERGENCE-W2-UNITS`: registry parity/theme boundary входит
в gate. Knowledge graph менять только если новый canon asset требует явного
ownership path; не создавать фиктивный runtime module для YAML.

## Verification commands

```bash
cd apps/api && /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_convergence_canon.py \
  tests/test_today_convergence_units.py -q

cd /tmp/solarsage-convergence-impl
/opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check \
  apps/api/app/services/today_convergence_canon.py \
  apps/api/app/services/today_convergence_units.py \
  apps/api/tests/test_today_convergence_canon.py \
  apps/api/tests/test_today_convergence_units.py
python3 scripts/grace_lint.py apps/api/app --quiet
bash scripts/grace/check-markers.sh
git diff --check
```

## Expected evidence

Точный changed-file list; focused test count; registry parity assertion; пример
mapped theme tuple и unknown `()`; подтверждение unchanged canonical ID при
annotation mutation; ruff/grace/marker/diff results; `git status --short`.

## Escalation and no-commit rule

Если initial maps не semantic-identical reference, нужен новый theme key вне
reference union или для корректности требуется grouping/adapter file —
**остановиться**, не менять W1 formula и доложить архитектору.

**Ничего не коммить и не пушить — коммит и push делает ревьюер.**
