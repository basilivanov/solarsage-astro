# S1.W3 Architecture Amendment — additive timing contract prerequisite

Дата: 2026-07-11

Статус: обязательная архитектурная поправка к S1.W3. Она изменяет только
последовательность additive wire fields, но не переносит calculation work из
S2.W1.

## 1. Обнаруженный фактический конфликт

Canonical preview JSON:

```text
e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json
```

содержит `activeFrom/activeUntil` для трёх activation evidence entries.

Текущая canonical API schema:

```text
apps/api/app/schemas/activation.py::ActivationEvidence
```

содержит только `exact_at`. `CamelModel` использует `extra="forbid"`.

Независимый запуск:

```text
TodayPayload.model_validate(JSON fixture)
```

даёт 6 validation errors:

```text
v2.activationEvidence.0.activeFrom
v2.activationEvidence.0.activeUntil
v2.activationEvidence.1.activeFrom
v2.activationEvidence.1.activeUntil
v2.activationEvidence.3.activeFrom
v2.activationEvidence.3.activeUntil
```

Следовательно, исходный S1.W3 invariant

```text
JSON -> canonical Pydantic TodayPayload -> generated Zod
```

невыполним без изменения wire contract.

## 2. Отвергнутые обходные решения

Запрещено:

1. стриппить timing fields до Pydantic validation и приклеивать после;
2. создавать test-only Pydantic subclass с `extra="allow"`;
3. хранить второй timing overlay JSON;
4. ослаблять `CamelModel.extra="forbid"`;
5. оставлять timing только ручным TypeScript extension;
6. переносить весь transit solver в S1.W3.

Все эти варианты либо создают второй wire contract, либо скрывают drift.

## 3. Принятое решение — consumer-first additive rollout

В S1.W3 раньше срока добавить только optional contract fields в обе canonical
ActivationEvidence schemas:

```py
active_from: str | None = None
exact_at: str | None = None
active_until: str | None = None
```

Файлы:

```text
apps/api/app/schemas/activation.py
apps/solarsage/solarsage/schemas/activation.py
```

После этого regenerate:

```text
packages/contracts/openapi.json
packages/contracts/_generated.ts
packages/contracts/_generated.zod.ts
```

Это стандартный additive consumer-first rollout:

```text
schema/consumers can accept fields
  -> producer still emits null/omits them
  -> S2.W1 starts calculating real values
```

## 4. Что строго остаётся в S2.W1

S1.W3 не реализует и не меняет:

- Swiss Ephemeris timing solver;
- transit orb-window search;
- exact hit refinement;
- retrograde/multiple-pass selection;
- annual/monthly/firdar/return boundary calculation;
- activation producer population;
- calculation batching/cache;
- timing/phase consistency logic;
- performance benchmark;
- calculation or activation-layer version bumps.

S2.W1 по-прежнему полностью владеет реальной семантикой и значениями timing.

## 5. Version policy для S1.W3

Поля optional и production producer их пока не заполняет, поэтому S1.W3 не
меняет:

```text
CALCULATION_VERSION
ACTIVATION_LAYER_VERSION
SCORING_V2_VERSION
TODAY content/payload versions
```

Версии повышаются в S2.W1 одновременно с реальным calculation behavior.

## 6. Temporary frontend bridge

После regeneration generated `ActivationEvidence` знает все три timing fields.
`getEvidenceTimingPreview` больше не должен использовать `Reflect.get`.

В S1.W3 сохранить его как маленькую typed presentation projection либо удалить
и читать fields напрямую. Предпочтение для минимального consumer diff:

```ts
return {
  activeFrom: evidence?.activeFrom,
  exactAt: evidence?.exactAt,
  activeUntil: evidence?.activeUntil,
}
```

Удалить формулировки `temporary additive-preview compatibility` и tests для
invalid hidden extra values. Wrong known field types теперь обязан отвергать
generated runtime validator.

## 7. Acceptance implication

S1.W3 принимается только если один canonical JSON:

```text
passes strict Pydantic TodayPayload
  -> normalizes deterministically by_alias=True
  -> passes generated TodayPayloadWireSchema
  -> preserves IDs, timing and verdicts
  -> feeds the frontend adapter and visual specs
```
