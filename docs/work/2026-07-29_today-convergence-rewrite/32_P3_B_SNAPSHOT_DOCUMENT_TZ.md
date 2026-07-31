# 32 — P3-B Deterministic snapshot document

Статус: **controller packet / implementation-ready**

Исполнитель: Codex CLI, `gpt-5.6-luna`, effort `high`

Depends on: packets 29–31, frozen W1 canon, schema 0028

## 1. Локальная цель

Добавить одну pure boundary между успешным runtime calculation и будущей
PostgreSQL publication:

```text
validated profile + TodayConvergenceCalculationBuilt + frozen canon files
  -> mode-aware profile_hash
  -> exact canon_hash
  -> privacy-safe canonical factor pack + input_hash
  -> normalized deterministic result
  -> TodayConvergenceSnapshotDocument
```

Документ не получает `snapshot_id`, timestamps или narrative: их атомарно
создаст следующий persistence-срез. Этот пакет не пишет БД и не строит public
wire payload.

## 2. Exact write scope

- `apps/api/app/services/today_convergence_snapshot.py` (new)
- `apps/api/app/services/today_convergence_canon.py`
- `apps/api/tests/test_today_convergence_snapshot.py` (new)
- `apps/api/tests/test_today_convergence_canon.py`
- `grace/knowledge-graph.xml`
- `grace/verification-matrix.md`
- этот packet

## 3. Frozen / out of scope

- не менять W1 YAML, formula/tone/selection, version constants, runtime,
  activation layer, DB models или migration 0028;
- не добавлять repository/service, transaction, endpoint, lease, impression,
  check-in, access projection, LLM, lookahead или localized copy;
- не использовать legacy `TodayPayload`, cache key, scoring/normalization,
  old `NatalContextService.compute_profile_hash` или 12:00 fallback;
- не хранить raw profile, Telegram identity, user ID, coordinates, birthday,
  raw sidecar response или secrets в JSON-документе;
- не коммитить и не push.

## 4. Canon artifact fingerprint

В `today_convergence_canon.py` добавить public pure function:

```python
def compute_today_convergence_canon_hash(canon_dir: Path | None = None) -> str:
    ...
```

Она:

- сначала вызывает существующий strict loader для тех же трёх файлов
  (`today_convergence.v1.yml`, `aspect_rules.v1.yml`,
  `today_convergence_themes.v1.yml`), чтобы malformed/draft canon fail-closed;
- SHA-256 считает по exact bytes всех трёх файлов в фиксированном порядке с
  включённым filename boundary, возвращает 64 lowercase hex;
- hash меняется при изменении любого из трёх artifacts и не зависит от cwd;
- не кэширует скрыто и не принимает произвольный список файлов.

Обновить module contract/map/`__all__`.

## 5. Snapshot profile identity

Новый модуль принимает direct profile object и уже рассчитанный
`BirthTimeResolution`. Mode-aware profile hash строится только из calculation
identity:

```text
schema=today-profile-identity.v1
birthday
birth latitude/longitude/timezone
house_system=PLACIDUS
birth resolution: mode, bucket, exact birth_time or null, range start/end
```

- JSON canonical: UTF-8, `ensure_ascii=False`, keys sorted, compact separators,
  `allow_nan=False`; SHA-256 full 64 hex;
- exact/bucket/unknown и разные buckets обязательно дают разные hashes;
- `-0.0` нормализуется в `0.0`; finite coordinates and IANA timezone required;
- current location, gender, user ID и Telegram data в natal profile hash не
  входят;
- profile resolution обязан byte/value-equal `calculation.birth_time`, иначе
  fail closed; raw identity нигде не возвращается и не логируется.

Не импортировать legacy profile-hash/cache implementation.

## 6. Canonical input and deterministic result

Добавить frozen result boundary:

```python
@dataclass(frozen=True)
class TodayConvergenceSnapshotDocument:
    profile_hash: str
    input_hash: str
    canon_hash: str
    formula_version: str
    calculation_version: str
    ephemeris_artifact_id: str
    birth_time_mode: str
    birth_time_range: dict[str, str]
    canonical_input_json: dict[str, object]
    deterministic_result_json: dict[str, object]
```

Public builder принимает direct profile + `TodayConvergenceCalculationBuilt` +
optional `canon_dir`. `Unavailable`, чужие dataclass-like objects и version/
birth-resolution disagreement запрещены typed
`TodayConvergenceSnapshotError("today_convergence_snapshot:<reason>")`.

`canonical_input_json` — content-addressed normalized factor pack:

```text
schema_version = today-canonical-input.v1
profile_hash
target: date, time, timezone
birth_time: mode, bucket, range, controls, canonical gap, capabilities
versions: formula, calculation, activation-layer, ephemeris artifact, canon hash
factor_units: все CanonicalUnit из ledger в canonical order
```

Все enum/date/datetime/tuple/mapping значения переводятся в deterministic
JSON-compatible values. Datetime сохраняет ISO offset; non-finite floats,
нестроковые mapping keys и unknown objects fail closed. `input_hash` — SHA-256
ровно canonical bytes `canonical_input_json`. В pack нет raw profile/Telegram/
user fields и нет повторного raw sidecar payload.

`deterministic_result_json` — компактная ссылка на factor pack, без дублирования
полных units:

```text
schema_version = today-deterministic-result.v1
state, day_tone
selected:
  convergences: group/event references, spheres, polarity, evidence level
  main_event: event reference or null
  impulses: event references
  selected_unit_ids, selected_spheres
audit:
  birth_time_facts, ledger, grouping, tone, selection
```

Для convergence сохранить `group_id`, `anchor_event_id`, ordered
`member_event_ids`, exact two `evidence_event_ids`, primary/secondary sphere,
polarity и evidence level. Для main/impulse — только event ID, sphere, polarity,
evidence level. Полные CanonicalUnit существуют один раз — только в
`canonical_input_json.factor_units`.

Builder проверяет:

- pipeline formula == loaded canon formula;
- calculation/pipeline state agree;
- selected/group/event references существуют в factor pack;
- selected IDs/spheres уникальны и caps upstream не ослаблены;
- artifact/version/hash strings non-empty and bounded by schema columns;
- повторный build даёт byte-identical canonical JSON and hashes;
- input permutation уже поглощена canonical ledger order.

## 7. Required tests

1. canon hash 64 hex, cwd-independent, stable on repeated load;
2. изменение bytes каждого canon artifact меняет hash; invalid canon не
   получает fingerprint;
3. profile hash меняется exact↔4 buckets↔unknown и при relevant birth identity;
4. current location/gender не меняют profile hash; `-0.0 == 0.0`;
5. profile/calculation resolution mismatch and invalid coordinates/TZ fail
   closed без raw values в error;
6. hero и quiet documents имеют exact normalized selected references and all
   declared audit blocks;
7. canonical factor units встречаются один раз, sorted deterministically; JSON
   не содержит forbidden raw profile/Telegram/user keys;
8. `input_hash == sha256(canonical bytes)`; repeat and permuted raw input yield
   identical document/hash;
9. unknown→exact меняет profile/input hash, старый built document не мутирует;
10. unavailable/runtime impostor, foreign event/group reference, version/state
    disagreement and non-finite value fail closed;
11. source guards: no DB/http/LLM/legacy Today/cache imports and no fallback
    artifact literal.

Tests may construct accepted pipeline records through existing pure builders;
production code must not import test fixtures or analysis dumps.

## 8. GRACE and verification

- new module gets full GRACE header, contract, map, function contracts and
  exact `owned_tests`;
- graph: `M-TODAY-CONVERGENCE-CANON -> M-TODAY-CONVERGENCE-SNAPSHOT-DOCUMENT`,
  `M-TODAY-CONVERGENCE-RUNTIME -> ...`, then future persistence edge is not yet
  declared;
- add one W3 snapshot-document UC row without claiming DB publication.

Commands:

```bash
git diff --check
cd apps/api && PYTHONPATH=. /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_convergence_canon.py \
  tests/test_today_convergence_snapshot.py \
  tests/test_today_convergence_runtime.py -q
cd ../.. && /opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check --no-cache \
  apps/api/app/services/today_convergence_canon.py \
  apps/api/app/services/today_convergence_snapshot.py \
  apps/api/tests/test_today_convergence_canon.py \
  apps/api/tests/test_today_convergence_snapshot.py
python3 scripts/grace_lint.py apps/api/app --quiet
bash scripts/grace/check-markers.sh
```

## 9. Expected evidence

- exact canon/profile/input hash algorithms and privacy scan;
- hero + quiet deterministic snapshots without duplicated factor units;
- mutation/error tokens, repeat/permutation determinism;
- focused counts, Ruff, GRACE, markers, diff-check;
- exact changed paths, no W1/version/schema diff, no commit/push.
