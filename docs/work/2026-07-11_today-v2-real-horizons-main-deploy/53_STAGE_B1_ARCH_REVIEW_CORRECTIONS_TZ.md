# Stage B1 — architect review corrections

Дата ревью: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Базовый HEAD: `f0d8bef19ec4f0806039cf44a173a22bb4f60a1c`
Предыдущее ТЗ: `52_STAGE_B1_HORIZON_CONTRACT_CONSUMER_TZ.md`

## 0. Режим работы

Это correction-wave внутри B1. Не начинать B2.

- Не запускать субагентов.
- Не делать `git add`, commit, push, merge или rebase.
- Не менять production services, systemd, nginx, env и порты.
- Не менять backend population: `TodayService`/`SemanticV2Service` по-прежнему
  не должны заполнять `v2.horizons`.
- Не трогать unrelated paths:
  `.grace/`, `artifacts/design/`,
  `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`,
  `grace.db`, `skills/`.
- Сохранить все уже корректные B1 изменения. Исправить только findings ниже.
- Полные отчёты и evidence складывать в текущий `docs/work/.../b1/` только если
  они действительно нужны. Не создавать второй fixture payload.

Перед изменениями:

```bash
git status --short --branch
git diff --cached --name-only
git log -1 --format='%H %s'
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
```
Ожидание: index пустой, HEAD и origin feature равны `f0d8bef...`.

## 1. Finding F1 — provenance sphere integrity неполная

### Подтверждённый дефект

Сейчас `TodayV2Horizon.validate_horizon` проверяет `sphere_keys` только у
manifestation и её provenance. Следующие заведомо неверные payload'ы проходят:

```text
strength.provenance.sphereKeys = [shopping]
risk.provenance.sphereKeys = [shopping]
actions.do[*].provenance.sphereKeys = [shopping]
actions.avoid[*].provenance.sphereKeys = [shopping]
```

при `likelySpheres = [work, decisions, money]`.

Это нарушает точный контракт из `52`: все nested provenance sphere keys должны
быть подмножеством `horizon.likely_spheres`.

### Исправление

В `apps/api/app/schemas/today_horizons.py`:

1. Проверять `provenance.sphere_keys` для каждого nested grounded item:
   `strength`, `risk`, `actions.do`, `actions.avoid`.
2. Сохранить текущую проверку manifestation own `sphere_keys` и manifestation
   provenance.
3. Ошибка должна содержать structural path, stable item ID и reason вроде
   `provenance-spheres-outside-likely-spheres`; не включать human text.
4. Не менять wire shape и generated OpenAPI из-за этого исправления.

Добавить отдельные negative tests минимум для:

- strength provenance;
- risk provenance;
- one `do` action provenance;
- one `avoid` action provenance;
- manifestation provenance (существующий тест сохранить).

## 2. Finding F2 — technical timing нельзя приписывать untimed evidence

### Подтверждённый риск

`act-firdar-major` в canonical fixture имеет все timing fields `null`, но его
`TodayV2TechniqueExplanation.timing` сейчас показывает окно профекции
`12 мая 2026 — 11 мая 2027`. В UI это выглядит как точная дата самого фирдара,
хотя fixture её не подтверждает.

### Исправление контракта

В cross-reference validator:

- если `technique_explanation.timing != None`, среди именно её
  `activation_ids` должен быть хотя бы один evidence item с non-null timing;
- этот evidence по-прежнему должен соответствовать `explanation.technique`;
- existing rule `explanation.timing == horizon.timing` остаётся;
- если все referenced evidence для explanation untimed, timing допускается
  только `None`, иначе ошибка
  `technique-timing-without-timed-evidence` с structural path/technique, без
  human copy.

Fixture:

- у explanation `firdar_major` установить `timing: null`;
- у `annual_profection`, medium и fast оставить подтверждённый timing;
- long horizon timing остаётся агрегированным из `act-annual-profection`.

Tests:

- untimed-only explanation с timing rejected;
- тот же explanation с `timing=None` accepted;
- mixed explanation, где хотя бы один referenced evidence timed, остаётся
  valid.

## 3. Finding F3 — human validation errors могут раскрывать raw copy

### Подтверждённый дефект

Duplicate warning сейчас формирует reason
`duplicate:<полный warning text>`. Проверка с `Секретная личная фраза` показывает
эту строку в `str(ValidationError)`.

Существующий test с очень длинным sentinel даёт ложную уверенность, потому что
Pydantic обрезает repr input.

### Исправление

1. Warning uniqueness error не должен включать значение warning. Использовать
   structural reason (`duplicate-warning`, индекс допустим), но не сам текст.
2. Для horizon-моделей и `TodayV2Block` обеспечить, что
   `str(ValidationError)` не печатает raw input values. Использовать локальное
   для этого feature расширение Pydantic config (`hide_input_in_errors=True`)
   без изменения глобального `CamelModel` и без изменения wire/OpenAPI.
3. Не логировать и не сериализовать `.errors()`/`.json()` в рамках B1.
4. Усилить tests короткими sentinel strings, которые без защиты точно попали бы
   в repr:
   - duplicate warning;
   - duplicate action human text;
   - invalid opaque fact input.
5. Assertions проверяют `str(exc_info.value)` и structural reason/path.

Изменение касается только error rendering/privacy; validation semantics и
response payload не меняются.

## 4. Finding F4 — прежняя component test matrix была удалена

### Подтверждённый дефект

`__tests__/components/TodayScreen.v2-downstream.test.tsx` был переписан:
11 прежних tests удалены и заменены 11 новыми. ТЗ требовало **extend**, а не
заменить matrix. Потеряны, в частности:

- activation contribution integrity;
- legacy human-safe technical disclosure details;
- `?why=1&astro=1` legacy deeplink;
- standalone `whyToday`;
- empty V2 safety;
- no-timing legacy behavior;
- visible 12-sphere verdict labels/statuses.

### Исправление

Восстановить исходную matrix из:

```bash
git show HEAD:__tests__/components/TodayScreen.v2-downstream.test.tsx
```

и **добавить** к ней B1 backend-horizon tests. Не удалять ни одну прежнюю
логическую проверку. Допустимо убрать точный duplicate assertion только если
оно буквально покрывается более строгим test в том же файле; это нужно явно
указать в callback.

Практически предпочтительно:

- сохранить original `loadFixture()` и tests на tracked audit fixture;
- B1 tests продолжать строить из canonical `dayPayloadV2`;
- legacy tests, использующие canonical fixture, при необходимости клонируют
  `v2` и ставят `horizons = null`;
- сохранить test `renders normalized visible verdict statuses...` полностью.

Ожидание: focused component suite содержит старые + новые scenarios, а не те же
11 tests под другими названиями.

## 5. Finding F5 — tone виден текстом, но не различается цветом

### Подтверждённый дефект

Все backend horizon cards/badges используют одинаковую violet style map.
Master-TZ `50` требует, чтобы tone был различим **и текстом, и цветом**, причём
style выбирается enum, а не анализом текста.

### Исправление

В `why-time-horizon-card.tsx` создать explicit enum-owned presentation map:

```text
supportive -> emerald/green family
neutral    -> slate/zinc neutral family
tense      -> rose/red or strong amber family
mixed      -> violet family
```

Требования:

- map индексируется только `horizon.tone`;
- root сохраняет `data-status={horizon.tone}`;
- visible label остаётся точным;
- tone badge получает стабильный
  `data-testid="why-horizon-tone" data-status="..."`;
- light/dark contrast должен оставаться читаемым;
- не определять tone из Russian copy;
- обновить mobile screenshot тем же Playwright test.

Component test должен проверять visible label и semantic data-status. Цвет не
проверять по случайному generated classname; он принимается screenshot review.

## 6. Finding F6 — fast human dates не совпадают с product timezone

Fast timing machine window:

```text
2026-07-07T21:00:00Z .. 2026-07-09T21:00:00Z
timezone=Europe/Moscow
rangeLabel=8–10 июля по Москве
```

Но `whyItMattersNow` сейчас пишет `С 7 по 9 июля`. Исправить на человеко-
читаемое окно `С 8 по 10 июля по Москве ...`. Machine values не менять.

Добавить assertion, что fast `rangeLabel` и `whyItMattersNow` используют одну
и ту же product-timezone date semantics.

## 7. Finding F7 — GRACE contracts неполные/несогласованные

Исправить только затронутые feature sections:

1. `resolveWhyExpandedMode` — exported public function, нужен полный
   `START_FUNCTION_CONTRACT`/`END_FUNCTION_CONTRACT`.
2. У `LegacyWhyTimeHorizonCard` исправить ошибочный END ID:
   сейчас он заканчивается ID `WhyTimeHorizonCard`.
3. Обновить module contract/map `why-time-horizon-card.tsx`: inputs,
   dependencies, outputs и invariants должны описывать backend + legacy paths,
   а не только legacy raw evidence.
4. Обновить module map `why-expanded.tsx` для backend mode/resolver.
5. Добавить function contracts минимум для non-trivial validators:
   - `TodayV2HorizonTiming.validate_timing`;
   - `TodayV2HorizonActions.validate_actions`;
   - `TodayV2Horizon.validate_horizon`;
   - `TodayV2HorizonsBlock.validate_block`;
   - `TodayV2Block.validate_optional_horizons`;
   - нового technique timing cross-reference helper, если он появится.
6. START/END IDs должны совпадать буквально.

Не переписывать старые модули целиком ради GRACE.

## 8. Minor cleanup

В `TodayScreen` передавать `payload.concreteAdvice` без type assertion, если
TypeScript уже знает `ConcreteAdviceBlock`. Удалить ставший ненужным import.
Если assertion реально нужен, в callback привести exact compiler reason; не
оставлять cast как маскировку типа.

## 9. Exact correction allowlist

Разрешены изменения только здесь:

```text
apps/api/app/schemas/today_horizons.py
apps/api/app/schemas/today.py
apps/api/tests/test_today_horizons_contract.py

components/today/today-screen.tsx
components/today/why-expanded.tsx
components/today/why-time-horizon-card.tsx

e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json
__tests__/components/TodayScreen.v2-downstream.test.tsx
__tests__/contracts/today-fixture-roundtrip.test.ts
e2e/dev-timing-fixture.spec.ts
e2e/mock-visual/day-v2.spec.ts

docs/work/2026-07-11_today-v2-real-horizons-main-deploy/53_STAGE_B1_ARCH_REVIEW_CORRECTIONS_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/b1/01-backend-contract-horizons-mobile.png
```

Generated OpenAPI/TS/Zod должны остаться byte-identical после исправлений.
Если generator создаёт diff, остановиться и сообщить до расширения scope.

## 10. Mandatory correction gates

### Backend focused

```bash
apps/api/.venv/bin/python -m pytest \
  packages/py-contracts/tests \
  apps/api/tests/test_contract_registry.py \
  apps/api/tests/test_today_horizons_contract.py \
  scripts/contracts/test_check_compat.py \
  -q
```

Дополнительно отдельным test/snippet доказать, что four grounded provenance
sphere escape cases rejected.

### Generated stability

Снять SHA256 трёх generated files, выполнить `pnpm contracts:generate`, снова
снять hashes. Они должны совпасть с состоянием до correction-wave и после
второго generate. Никакого generated diff из-за corrections.

### Frontend focused/full

```bash
npx vitest run \
  __tests__/components/TodayScreen.v2-downstream.test.tsx \
  __tests__/contracts/generated-runtime.test.ts \
  __tests__/contracts/today-fixture-roundtrip.test.ts \
  __tests__/lib/presentation/today-v2.test.ts

npx tsc --noEmit
npx vitest run
```

### Browser

```bash
E2E_BASE_URL=http://127.0.0.1:3003 npx playwright test \
  e2e/dev-timing-fixture.spec.ts \
  --project=mobile
```

Проверить screenshot визуально через image viewer. В нём long/mixed,
medium/mixed и fast/tense должны различаться не только текстом; минимум tense
визуально не должен выглядеть тем же violet badge/card, что mixed.

### Scope/static

```bash
git diff --check
git diff --cached --name-only
git diff --name-only
git status --short --branch
```

Index должен остаться пустым. Forbidden paths не должны появиться.

Полные sidecar/API suites повторять в correction-wave не обязательно, если
focused backend, full Vitest, typecheck и browser green; архитектор повторит
полные suites после приёмки corrections. Если затронуто что-либо вне allowlist,
полные suites обязательны и работа считается scope breach.

## 11. Callback

После выполнения вернуть ровно один итоговый блок и остановиться:

```text
READY_STAGE_B1_REVIEW_FIXES
branch: ...
head: ...
origin_feature: ...
provenance_sphere_matrix: PASS <counts>
untimed_technique_timing: PASS
validation_error_privacy: PASS
component_legacy_tests_restored: PASS old=<count> new=<count> total=<count>
tone_text_and_color: PASS
fast_timezone_copy: PASS
grace_contracts: PASS
generated_hashes: IDENTICAL
backend_focused: <counts>
frontend_focused: <counts>
frontend_full: <counts>
typecheck: PASS
browser_mobile: PASS
screenshot: docs/work/2026-07-11_today-v2-real-horizons-main-deploy/b1/01-backend-contract-horizons-mobile.png
diff_paths: ...
index: EMPTY
commit: NOT_YET
push: NOT_YET
```
