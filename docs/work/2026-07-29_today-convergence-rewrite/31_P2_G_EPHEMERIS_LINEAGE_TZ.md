# 31 — P2-G Ephemeris lineage through runtime

Статус: **controller packet / implementation-ready**

Исполнитель: Codex CLI, `gpt-5.6-luna`, effort `high`

Depends on: packets 29–30, `04_W2_W3_RUNTIME_CONTRACT_TZ.md` §7.1

## 1. Локальная цель

Закрыть один обнаруженный перед P3-B lineage-gap: таблица snapshot честно
требует `ephemeris_artifact_id`, но activation-grid transport и runtime сейчас
его не несут. Провести уже проверенный sidecar artifact identity через один
существующий grid response до immutable runtime result:

```text
sidecar verified EphemerisIdentity.artifact_id
  -> activation-grid meta
  -> typed API ActivationGridBatch
  -> TodayConvergenceCalculationBuilt.ephemeris_artifact_id
```

Никакого дополнительного HTTP health-call и никакого fallback ID.

## 2. Exact write scope

- `apps/solarsage/solarsage/api/activation_layer.py`
- `apps/solarsage/tests/test_activation_grid.py`
- `apps/api/app/clients/solarsage_client.py`
- `apps/api/app/services/today_convergence_runtime.py`
- `apps/api/tests/test_solarsage_client.py`
- `apps/api/tests/test_today_convergence_runtime.py`
- `grace/knowledge-graph.xml`
- `grace/verification-matrix.md`
- этот packet

## 3. Frozen / out of scope

- не менять activation evidence/layer shared contract, W1 canon, calculation
  formula, version constants или schema 0028;
- не менять single-layer endpoint: W2 runtime использует только grid;
- не добавлять новый sidecar/API request, startup cache, env field или literal
  `unknown`/`moshier-only` fallback;
- не строить snapshot JSON/hash и не писать БД;
- не менять legacy Today/Calendar/LLM/frontend;
- не коммитить и не push.

## 4. Sidecar grid contract

В `ActivationLayerGridMeta` добавить required:

```python
ephemeris_artifact_id: str = Field(min_length=1, max_length=128)
```

`post_activation_layer_grid` получает identity через канонический accessor
`solarsage.core.ephemeris_runtime.get_identity()` ровно один раз на request и
пишет `identity.artifact_id` в meta. Accessor использует уже верифицированный
process identity и не создаёт второй расчёт/HTTP-call.

- artifact берётся из того же sidecar runtime, который выполняет grid;
- production SWIEPH и разрешённый test-only Moshier возвращают их реальный ID;
- empty/missing identity fail-closed в существующий generic 500;
- raw manifest/path/engine details в response не добавлять;
- sample payload и shared `ActivationLayerContract` не менять.

## 5. API client batch contract

Оставить `ActivationGridSample` без изменений. Добавить frozen:

```python
@dataclass(frozen=True)
class ActivationGridBatch:
    calculation_version: str
    activation_layer_version: str
    ephemeris_artifact_id: str
    samples: tuple[ActivationGridSample, ...]
```

`get_activation_layer_grid(...) -> ActivationGridBatch`:

- required meta теперь включает `ephemeris_artifact_id`;
- ID — `str`, после strip непустой, длина `<=128`; сохраняется без изменения;
- существующие version/sample-count/order/layer parity gates остаются;
- `samples` — tuple в исходном порядке;
- malformed/missing/empty/oversized artifact даёт stable
  `SolarSageClientError` token `solarsage_client:activation_grid:ephemeris_artifact_id`;
- не принимать artifact из sample/debug и не запрашивать `/health`.

Обновить module contract/map/`__all__` на batch output.

## 6. Runtime composition

`_request_activation_grid` получает batch. Facts builder получает ровно
`batch.samples`. В `TodayConvergenceCalculationBuilt` добавить required:

```python
ephemeris_artifact_id: str
```

и заполнить из batch. `calculation_version` и `activation_layer_version` также
брать из batch, а не повторно из первого sample. Client уже доказал их parity.

Unavailable records artifact не раскрывают и не получают новое nullable поле:
при transport contract failure остаётся `activation_grid/unavailable`.
Один sidecar call, deterministic equality и frozen result сохраняются.

## 7. Required tests

1. Sidecar grid meta отдаёт exact artifact ID canonical accessor; accessor и
   calculation grid вызываются по одному разу;
2. настоящий test-only Moshier endpoint сообщает `moshier-only`, без hardcode в
   production function;
3. empty artifact/identity error -> generic 500 без raw details;
4. API client возвращает frozen `ActivationGridBatch`, exact versions/artifact
   и ordered tuple samples;
5. missing/empty/non-string/oversized artifact fail closed exact token;
6. остальные malformed meta, version disagreement, order/count gates не
   ослаблены;
7. exact/bucket/unknown runtime happy paths передают `batch.samples` в facts и
   сохраняют exact artifact in Built;
8. fake/default client вызывается один раз; malformed artifact не доходит до
   facts/pipeline;
9. runtime deterministic equality теперь включает artifact ID;
10. source guard: runtime/client не вызывают health и не содержат fallback
    artifact literal.

Не переписывать birth-time-facts API на batch: он по-прежнему принимает
sequence samples и остаётся pure extraction boundary.

## 8. GRACE and verification

- обновить contracts/maps/outputs для sidecar grid, API client и runtime;
- graph edge `M-EPHEMERIS-RUNTIME -> M-SIDECAR-ACTIVATION-GRID ->
  M-TODAY-CONVERGENCE-RUNTIME` с `ephemeris-artifact-lineage`;
- расширить существующую UC P2-F, не создавать дублирующую продуктовую UC.

Команды:

```bash
git diff --check
cd apps/solarsage && PYTHONPATH=. /opt/solarsage-astro/apps/solarsage/venv/bin/python -m pytest \
  tests/test_activation_grid.py -q
cd ../api && PYTHONPATH=. /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_solarsage_client.py \
  tests/test_today_convergence_runtime.py \
  tests/test_today_birth_time_facts.py -q
cd ../.. && /opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check --no-cache \
  apps/api/app/clients/solarsage_client.py \
  apps/api/app/services/today_convergence_runtime.py \
  apps/api/tests/test_solarsage_client.py \
  apps/api/tests/test_today_convergence_runtime.py \
  apps/solarsage/solarsage/api/activation_layer.py \
  apps/solarsage/tests/test_activation_grid.py
python3 scripts/grace_lint.py apps/api/app/clients/solarsage_client.py apps/api/app/services/today_convergence_runtime.py apps/solarsage/solarsage/api/activation_layer.py
bash scripts/grace/check-markers.sh
```

## 9. Expected evidence

- exact one-request lineage path and fail-closed token;
- sidecar/API focused counts, Ruff, GRACE, markers, diff-check;
- no version/canon/schema diff and exact changed paths;
- no commit/push.
