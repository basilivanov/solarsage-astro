# Architecture review 01 — three-horizon Why preview

Статус: **REWORK REQUIRED**
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Reviewed state: незакоммиченный diff после `READY_FOR_ARCH_REVIEW_THREE_HORIZON_WHY`

## Итог

Основная UX-модель принята: representative fixture корректно раскладывается как
`2 long / 2 medium / 1 fast`, сроки видимы, Нептун больше не скрывается, technical
disclosure объясняет сигналы обычным языком, а preview на `3003` визуально читаем.

До commit/final push необходимо исправить перечисленные ниже контрактные и
traceability-проблемы. Расширять scope за их пределы не нужно.

## P1. `whyToday` без полного `v2` теперь небезопасен

### Проблема

`WhyExpanded` сохраняет публичный prop `whyToday?: TodayV2WhyTodayItem[]`, однако
новая реализация определяет:

```ts
const hasV2 = Boolean(v2 || effectiveWhyToday.length > 0)
```

и затем вызывает:

```tsx
<V2WhyContent v2={v2!} ... />
```

Если вызывающая сторона передала `whyToday`, но не передала `v2`, non-null
assertion маскирует реальный `undefined`. `TechnicalCalculation` обращается к
`v2.activationEvidence` и может упасть. Старая версия компонента поддерживала
human-only `whyToday` без полного V2 block.

### Требуемое исправление

Развести состояния:

1. `hasHorizonStory`: полный `v2` существует и `selectWhyTimeHorizons(v2)` вернул
   хотя бы одну зону;
2. `hasSafeWhyItems`: переданы безопасные `v2.whyToday` либо standalone
   `whyToday`;
3. legacy `sections`.

Запрещён `v2!` в human-only пути.

Поведение:

- если есть horizons — показывать новый three-speed UX и technical disclosure;
- если horizons нет, но есть safe why items — показывать безопасный human-only
  fallback в стиле прежнего numbered Why list; не заявлять «три скорости» и не
  показывать пустой technical disclosure;
- если нет horizons, why items и legacy sections — вернуть `null`;
- legacy sections работают как раньше.

Добавить component tests:

1. standalone `whyToday` без `v2` рендерится и не падает;
2. `v2` с evidence, не прошедшими пороги, но с why items использует human-only
   fallback и не показывает three-speed headline/technical toggle;
3. пустой `v2` без why/evidence и без legacy sections не рендерит блок.

## P1. Неполный словарь поддерживаемых техник

### Проблема

`TECHNIQUE_LABELS` поддерживает больше техник, чем
`getTechnicalEvidenceExplanation`. Сейчас generic fallback получают как минимум:

- `transit_to_angle`;
- `transit_to_lot`;
- `transit_planet_in_house`;
- `monthly_profection`.

Это противоречит ТЗ: пользователь не должен увидеть название известной системе
техники без нормального объяснения.

### Требуемое исправление

Для **каждого** ключа `TECHNIQUE_LABELS` добавить содержательное определение:

- `transit_to_natal` — текущее положение относительно натальной планеты;
- `transit_to_angle` — текущее положение относительно ASC/MC/другого угла карты;
- `transit_to_lot` — текущее положение относительно расчётной чувствительной
  точки/жребия;
- `transit_planet_in_house` — прохождение планеты по жизненной сфере дома;
- annual/monthly profection;
- firdar major/minor;
- solar/lunar return;
- secondary progression;
- solar arc;
- eclipse window.

Для current fixture расширить смысл, а не оставлять одно предложение:

- annual profection: техника не обещает событие; здесь показывает годовой фокус
  темы Плутона;
- firdar: не обещает событие; здесь независимо подтверждает долгий фон той же
  темы;
- transit: отвечает за timing — почему тема активнее именно в текущем периоде;
- orb: техническая строка остаётся, а смысл малого orb уже объясняется в current
  context.

Добавить безопасные planet definitions для всех десяти известных планет из
`PLANET_LABELS_NOMINATIVE`, чтобы следующий реальный payload не деградировал до
пустого meaning. Aspect definitions уже покрывают пять аспектов и должны
сохраниться.

Unit test должен пройти по всем ключам `TECHNIQUE_LABELS` и доказать, что известная
техника не получает generic definition. Отдельно проверить все десять planet keys.

## P1. Human copy средней волны не полностью связан с evidence

### Проблема

Representative medium body содержит смысл Нептуна:

> может быть сложнее понять, какая опора реальна...

Но `why-structure-resource.activationIds` содержит только
`act-pluto-trine-saturn`. При этом technical medium zone показывает и
`act-neptune-opp-saturn`.

### Требуемое исправление

В обоих fixture-файлах синхронно установить:

```ts
activationIds: ["act-pluto-trine-saturn", "act-neptune-opp-saturn"]
```

Human copy тогда трассируется к обоим реально выбранным medium evidence.

Добавить assertion, что representative medium why item связан с обоими selected
medium IDs.

## P1. GRACE contract устарел, legacy selector остался мёртвым API

### Проблема

`selectTechnicalCalculationEvidence` больше не используется runtime-кодом, но
остаётся экспортированным и тестируемым. Это сохраняет старую конкурирующую модель
«два аспекта + grouped periods», которую задача должна была заменить.

Одновременно module contract в `today-v2.ts` всё ещё говорит:

- `Never computes ... importance`;
- semantic block `SELECTION` описан как `period-only grouping`.

Новый код действительно не пересчитывает астрологию или backend score, но делает
presentation ranking на основании backend contributions/strength/phase/orb. Это
должно быть честно отражено в GRACE.

### Требуемое исправление

1. Удалить `selectTechnicalCalculationEvidence`, его import/test и entrypoint из
   module map. После исправления `rg selectTechnicalCalculationEvidence` должен
   находить только историческое описание в docs/TZ, но не runtime/test code.
2. Обновить `M-LIB-PRESENTATION-TODAY-V2`:
   - purpose/outputs включают three-horizon model, duration/stage/education copy;
   - invariant: модуль не пересчитывает астрологию, convergence или backend
     scores; он только ранжирует уже рассчитанные evidence для presentation;
   - semantic blocks описывают horizon classification/ranking вместо
     `period-only grouping`.
3. Обновить invariant `M-TODAY-WHY-EXPANDED`: technical vocabulary разрешена в
   выделенном disclosure control/content, но не в human narrative. Сейчас subtitle
   toggle намеренно содержит «Профекция, фирдар...», поэтому утверждение «только в
   opened content» неверно.

## P1. Ranking test не доказывает заявленный tie-break

### Проблема

Тест `ranks selected evidence by contribution, strength, phase, orb, then backend
order` создаёт пять medium candidates, но лимит medium равен двум. Assertion
доказывает только, что выбраны contribution и strength. Он не доказывает:

- exact выше applying при равных contribution/strength;
- меньший orb выше backend order при равных предыдущих полях;
- backend order стабилен при полном равенстве.

### Требуемое исправление

Сделать отдельные pairwise/parameterized cases:

1. contribution побеждает более высокий strength;
2. strength побеждает более высокий phase;
3. exact побеждает applying при равных contribution/strength;
4. меньший orb побеждает более ранний backend order при равных предыдущих полях;
5. backend order сохраняется при полном равенстве.

Каждый кейс должен работать с максимум двумя кандидатами, чтобы assertion реально
проверял нужный критерий.

## P2. Полнота duration/classification tests

Расширить table-driven tests без изменения runtime scope:

- fast planets: Moon, Sun, Mercury, Venus, Mars;
- medium transit planets: Jupiter, Saturn, Uranus, Neptune, Pluto;
- все duration mappings из раздела 7 исходного ТЗ;
- все stage mappings.

## Визуальная часть

Текущий human visual принят по направлению: три слоя считываются, сроки видимы,
горизонтального overflow нет. Technical visual также понятен, хотя закономерно
длинный.

После текстовых исправлений current fixture technical copy изменится, поэтому:

1. обновить `02-why-three-horizons-calculation-mobile.png` и full-day capture;
2. обновить соответствующие Playwright snapshots;
3. снова выполнить mobile update, затем mobile no-update;
4. лично открыть итоговые 01/02/03 assets.

## Финальные проверки rework

Выполнить:

```bash
npx vitest run __tests__/lib/presentation/today-v2.test.ts __tests__/components/TodayScreen.v2-downstream.test.tsx
npx tsc --noEmit
git diff --check
E2E_BASE_URL=http://127.0.0.1:3003 pnpm exec playwright test e2e/mock-visual/day-v2.spec.ts --project=mobile --update-snapshots
E2E_BASE_URL=http://127.0.0.1:3003 pnpm exec playwright test e2e/mock-visual/day-v2.spec.ts --project=mobile
curl -sS -o /dev/null -w '%{http_code}\n' 'http://127.0.0.1:3003/day/2026-07-08?why=1'
rg -n 'selectTechnicalCalculationEvidence' components lib __tests__ e2e
```

Последний `rg` должен вернуть пусто.

## Callback

Commit/final push всё ещё запрещены. После rework вернуть:

```text
READY_FOR_ARCH_REVIEW_THREE_HORIZON_WHY_REWORK_1
fixed: <list>
tests: <exact results>
preview_url: http://127.0.0.1:3003/day/2026-07-08?why=1
screenshots: <paths>
production_untouched: YES
known_untracked_untouched: YES
commit: NOT_YET
final_push: NOT_YET
```

После callback остановиться.
