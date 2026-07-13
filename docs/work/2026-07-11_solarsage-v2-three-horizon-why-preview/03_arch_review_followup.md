# Architecture review follow-up — final copy hardening

Статус: **TWO SMALL FIXES REQUIRED BEFORE COMMIT**

Независимые reviewer gates уже прошли:

- full Vitest: 91 files / 954 tests;
- `npx tsc --noEmit`;
- `git diff --check`;
- mobile Playwright no-update;
- preview `3003` returns 200.

Ниже остаются только две copy/robustness-правки. Scope больше не расширять.

## 1. Убрать необъяснённое английское слово `timing`

Сейчас `transit_to_natal` говорит:

> Он отвечает за timing...

Для пользователя без астрологической подготовки это новый необъяснённый термин.
Заменить определение на полностью русский и одновременно объяснить «натальную
карту»:

> Транзит — это фактическое положение планеты сейчас. Расчёт сравнивает его с
> натальной картой — положением планет в момент вашего рождения — и помогает
> понять, почему личная тема становится заметнее именно в текущий период.

Для остальных transit definitions также не использовать English product copy.

## 2. Не трактовать любой target профекции как планету

Сейчас annual profection definition безусловно вызывает:

```ts
getPlanetLabelRu(evidence.targetPlanet || evidence.targetKey)
```

Если реальный target имеет тип `house`, `angle`, `lot` или `sphere`, это может
показать сырой backend key как будто он название планеты.

Сделать safe target description по `evidence.targetType`:

- `planet` — локализованная планета;
- `house` — `активной жизненной сферы`;
- `angle` — `личного направления и способа проявляться`;
- `lot` — `чувствительной точки карты`;
- `sphere` — локализованная concise sphere label, если она известна, иначе
  `активной личной темы`;
- неизвестный fallback — `активной личной темы`.

Ни один raw `targetKey` не должен попадать в educational definition.

Добавить unit test:

- annual profection с `targetType="sphere"`,
  `targetKey="crisis_transformation_control"`, `targetPlanet=null`;
- definition не содержит `crisis_transformation_control`;
- definition содержит понятное русское описание темы.

После правки обновить affected technical/full-day assets и snapshots, потому что
transit definition видимо изменится.

## Проверки

```bash
npx vitest run __tests__/lib/presentation/today-v2.test.ts __tests__/components/TodayScreen.v2-downstream.test.tsx
npx tsc --noEmit
git diff --check
E2E_BASE_URL=http://127.0.0.1:3003 pnpm exec playwright test e2e/mock-visual/day-v2.spec.ts --project=mobile --update-snapshots
E2E_BASE_URL=http://127.0.0.1:3003 pnpm exec playwright test e2e/mock-visual/day-v2.spec.ts --project=mobile
curl -sS -o /dev/null -w '%{http_code}\n' 'http://127.0.0.1:3003/day/2026-07-08?why=1'
```

Commit/final push пока не делать. Вернуть:

```text
READY_FOR_FINAL_ARCH_ACCEPTANCE_THREE_HORIZON_WHY
fixed: russian transit/natal explanation; target-type-safe profection copy
tests: <results>
preview_url: http://127.0.0.1:3003/day/2026-07-08?why=1
production_untouched: YES
commit: NOT_YET
final_push: NOT_YET
```

После callback остановиться.
