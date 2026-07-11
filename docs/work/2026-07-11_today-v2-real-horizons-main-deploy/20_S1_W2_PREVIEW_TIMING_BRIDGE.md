# S1.W2 Architecture Guidance — temporary preview timing bridge

Дата: 2026-07-11

Статус: обязательное переходное решение до S2.W1. Не commit/push, S1.W3 не
начинать.

## Причина

`exactAt` уже существует в canonical API ActivationEvidence. `activeFrom` и
`activeUntil` пока присутствуют только как additive fields test/dev preview
fixture. Canonical Pydantic/OpenAPI получит эти поля в S2.W1.

После удаления manual raw schemas generated `ActivationEvidence` правильно не
знает `activeFrom/activeUntil`. Нельзя возвращать их в `lib/contracts/today.ts`
как ручное wire extension и нельзя cast-ить evidence к выдуманному interface.

## Решение

В `lib/presentation/today-v2.ts` добавить presentation-only reader:

```ts
export type EvidenceTimingPreview = {
  activeFrom: string | null | undefined
  exactAt: string | null | undefined
  activeUntil: string | null | undefined
}

export function getEvidenceTimingPreview(
  evidence: ActivationEvidence | null | undefined,
): EvidenceTimingPreview
```

Implementation rules:

- `exactAt` читать из generated typed property;
- `activeFrom/activeUntil` читать через `Reflect.get(evidence, key)`;
- принимать только `string`, `null`, `undefined`;
- invalid number/object/array → `undefined`;
- no `any`, no cast, no mutation;
- function is pure and explicitly documented as temporary additive-preview
  compatibility until S2.W1.

Добавить function contract и public entrypoint/module map.

## Consumers

`components/today/why-time-horizon-card.tsx`:

- удалить cast `as ActivationEvidence | undefined`;
- получить `const timing = getEvidenceTimingPreview(horizon.evidence[0])`;
- `phase` по-прежнему читать typed из `horizon.evidence[0]?.phase`;
- format/render behavior не менять.

Если `lib/presentation/today-v2.ts` duration/ranking logic обращается к
`activeFrom/activeUntil`, использовать тот же reader — один источник temporary
compatibility, никаких повторных Reflect helpers.

Не добавлять timing fields в:

```text
packages/contracts/index.ts
lib/contracts/today.ts
packages/contracts/runtime.ts
```

Они появятся автоматически через Pydantic/OpenAPI в S2.W1.

## Tests

В `__tests__/lib/presentation/today-v2.test.ts` доказать:

- valid additive strings возвращаются;
- `exactAt` сохраняется;
- null сохраняется;
- invalid additive field types становятся undefined;
- input object не мутируется.

Существующий dev timing Playwright/Vitest должен продолжить показывать
даты/пики.

## Gate addition

К S1.W2 gates добавить:

```bash
npx vitest run __tests__/lib/presentation/today-v2.test.ts
```

Callback дополнить:

```text
preview_timing_bridge: presentation-only
manual_wire_timing_extension: NO
bridge_removal_wave: S2.W1
```
