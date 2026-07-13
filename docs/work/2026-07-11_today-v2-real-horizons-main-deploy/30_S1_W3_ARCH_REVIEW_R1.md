# S1.W3 Architect Review R1 — contract pipeline and one-source fixture

Дата: 2026-07-11
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
База ревью: `5ffeebac283f3a95a11f122c7b0ef35923cefecf`
Вердикт: `CHANGES_REQUIRED`
Commit/push: запрещены до повторной архитектурной приёмки.

## 1. Что принято концептуально

Выбранная архитектура остаётся правильной:

```text
API Pydantic wire schema
  -> deterministic OpenAPI
  -> generated TypeScript types
  -> generated runtime Zod
  -> one validation at fetch boundary
  -> typed adapter without a second parse

one canonical JSON fixture
  -> Pydantic validation + alias dump
  -> generated Zod validation
  -> thin TypeScript wrapper
```

Additive optional promotion `activeFrom` / `exactAt` / `activeUntil` в API и
sidecar schemas соответствует consumer-first rollout. Реальный расчёт timing,
producer population и version bump в S1.W3 не добавлены — это правильно.

Ниже перечислены только блокеры реализации и доказательств.

## 2. P0 — `.github/workflows/ci.yml` сейчас не является валидным YAML

В строках 7–43 GRACE-комментарии записаны через `//`. Для YAML допустим только
`#`. В текущем виде GitHub Actions не сможет даже разобрать workflow.

Независимое доказательство архитектора:

```text
yaml.scanner.ScannerError
line 10: //   - .github/workflows/ci.yml
could not find expected ':'
```

Исправить:

1. Все GRACE-комментарии workflow вернуть к YAML syntax `#`.
2. Не переписывать существующие jobs и их команды без необходимости.
3. `contract-tests` оставить отдельным job.
4. Установку API сделать явно через interpreter выбранного setup-python:

   ```bash
   python -m pip install -e ./apps/api
   ```

5. После исправления обязательно выполнить parse proof:

   ```bash
   apps/api/.venv/bin/python -c \
     'import pathlib, yaml; yaml.safe_load(pathlib.Path(".github/workflows/ci.yml").read_text()); print("YAML_OK")'
   ```

Ожидается `YAML_OK`.

## 3. P0 — preview isolation guard ослаблен и пропускает небезопасные варианты

Файл:

```text
__tests__/guardrails/preview-isolation.test.ts
```

Текущая exception logic не выполняет требования S1.W3:

1. Не проверяет exact import specifier. В разрешённом route пройдёт любой
   dynamic import, содержащий `e2e/mock-visual`.
2. Не проверяет `await`; проверяется только начало regex match с `import(`.
3. Не запрещает второй dynamic fixture import в том же route.
4. Проверки ordering ошибочны при отсутствующем guard token:

   ```ts
   text.indexOf(guard) < text.indexOf(import)
   ```

   Если guard удалён, `indexOf` возвращает `-1`, а `-1 < importIndex` даёт
   `true`. То есть тест может подтвердить несуществующую защиту.

Исправить guard так, чтобы он доказал одновременно:

```text
allowed route:
  app/api/dev-fixtures/three-horizon-timing/route.ts

allowed specifier:
  ../../../../e2e/mock-visual/fixtures/day-v2-2026-07-08

allowed form:
  await import("../../../../e2e/mock-visual/fixtures/day-v2-2026-07-08")

allowed import count:
  exactly 1
```

Для каждого guard needle сначала отдельно доказать `index >= 0`, затем
`index < allowedImportIndex`. Проверить development guard, local-host guard,
unsafe-proxy guard и 404 return. Любой другой path/specifier/form/count должен
попадать в violations.

Не добавлять skip всего `app/api`, `dev-fixtures` или route directory.

## 4. P0 — в index попали запрещённые visual artifacts

Callback `forbidden_paths_staged: NO` фактически неверен. Сейчас staged:

```text
docs/work/2026-07-11_solarsage-v2-three-horizon-why-preview/assets/01-why-three-horizons-mobile.png
docs/work/2026-07-11_solarsage-v2-three-horizon-why-preview/assets/02-why-three-horizons-calculation-mobile.png
docs/work/2026-07-11_solarsage-v2-three-horizon-why-preview/assets/03-full-day-three-horizons-mobile.png
e2e/mock-visual/day-v2.spec.ts-snapshots/03-full-day-three-horizons-mobile-mobile-linux.png
```

Первые два docs assets визуально pixel-identical старым версиям; отличаются
только несколько RGB-значений под полностью прозрачными пикселями. Их нужно
восстановить byte-for-byte из `HEAD` и не коммитить.

Для третьего docs asset и full-page Playwright snapshot найден отдельный
предсуществующий baseline gap:

- текущая страница выше старого snapshot на `84 CSS px`;
- вставка начинается около `y=993`;
- visual crop показывает только уже принятые в S1.W0 публичные статусы
  `Внимание` на плитке и `Требует внимания` в раскрытой сфере;
- этот UI уже находится в commit `5de571a` и принят в
  `docs/work/2026-07-11_preview-visible-sphere-status-labels/01_ARCH_ACCEPTANCE.md`;
- старый full-page snapshot был сохранён без этих уже принятых строк.

Следовательно, нельзя ни удалить принятый UI ради старого snapshot, ни тайно
включить snapshot update в contract commit.

Требуемое разделение:

1. `01-*` и `02-*` docs assets восстановить из `HEAD`.
2. Текущие новые версии только этих двух full-page файлов сохранить для
   отдельного baseline-repair checkpoint:

   ```text
   docs/work/2026-07-11_solarsage-v2-three-horizon-why-preview/assets/03-full-day-three-horizons-mobile.png
   e2e/mock-visual/day-v2.spec.ts-snapshots/03-full-day-three-horizons-mobile-mobile-linux.png
   ```

3. Не включать эти два файла в S1.W3 contract commit.
4. Не делать baseline-repair commit до отдельного разрешения архитектора.
5. После baseline repair повторить browser gate строго с
   `--update-snapshots=none`; он должен пройти без дальнейшего изменения
   snapshot.

## 5. P1 — frontend round-trip test содержит `any` и слабый SoT guard

Файл:

```text
__tests__/contracts/today-fixture-roundtrip.test.ts
```

### 5.1 Запрещённый `any`

Сейчас есть:

```ts
{} as Record<string, any>
```

Это прямо запрещено ТЗ. Использовать generated public type, локальный точный
`TimingTriple`, `satisfies` или типизированный `Object.fromEntries`, но без
`any`, double casts и suppression directives.

### 5.2 Test не доказывает единственный JSON source

Сейчас assertion:

```ts
expect(jsonFiles).toContain("day-v2-2026-07-08.json")
```

Он останется зелёным при двух, трёх и десяти копиях. Нужно отфильтровать именно
sources этого fixture и потребовать exact equality с единственным canonical
filename.

Также явно доказать отсутствие manual initializer:

```text
HERO_HEADLINE отсутствует
previewTiming отсутствует
dayPayloadV2 = { ... } отсутствует
```

Сохранить exact JSON import и `TodayPayloadWireSchema.parse` assertions.

## 6. P1 — backend tests не проверяют заявленную безопасность normalizer

Файл:

```text
apps/api/tests/test_today_fixture_contract.py
```

Исправить:

1. `test_invalid_fixture_sanitized_error` сейчас тестирует прямой вызов
   `TodayPayload.model_validate`, а не фактический normalizer output.
2. Создать invalid temp JSON с sentinel, вызвать `normalize_file(...)`, снять
   реальный stdout/stderr через `capsys`, проверить typed non-zero code и
   отсутствие sentinel/raw payload в обоих streams.
3. После `check_only=True` для drifted copy сравнить bytes до/после и доказать,
   что check mode ничего не изменил.
4. Исправить `understrict` в module contract.
5. Привести imports/long comprehensions к читаемому Python formatting без
   изменения смысла.

## 7. P1 — shell wrapper расширяет authority и имеет неточный GRACE contract

Файл:

```text
scripts/contracts/today_fixture.sh
```

ТЗ требует, чтобы wrapper всегда работал только с canonical JSON и прозрачно
поддерживал только normal mode/`--check`. Текущая ветка `else` позволяет
передать произвольный path.

Сделать exact CLI:

```text
no args   -> normalize canonical JSON
--check   -> check canonical JSON
anything else -> usage + exit 2
```

GRACE contracts сделать truthful:

- `today_fixture.sh` в normal mode может атомарно переписать canonical JSON;
- `today_fixture.sh --check` не пишет;
- `check.sh` запускает `generate.sh`, поэтому generated artifacts могут быть
  перезаписаны перед drift comparison;
- `check.sh` никогда автоматически не нормализует fixture.

Сейчас `side_effects: none` и `drift detection ... without writing files` для
этих scripts неверны.

## 8. P1 — README неточно связывает calculation rollout и version bump

Файл:

```text
packages/contracts/README.md
```

Фраза о том, что version bump не делается «until timing calculations are
implemented», создаёт неверное правило. Само начало population уже добавленных
optional fields не является breaking change.

Зафиксировать:

```text
- additive optional field: consumer-first rollout, version bump не нужен;
- последующее заполнение этого optional field producer'ом само по себе не
  требует version bump;
- version bump нужен только при реально breaking shape/semantic change;
- generated artifacts коммитятся вместе с Pydantic change;
- frontend не объявляет wire type/runtime schema вручную.
```

Сохранить полезные прежние правила про primitive JSON/ISO strings и contract
version discipline; удалить только устаревшее утверждение, что API response не
валидируется runtime Zod.

## 9. Повторные gates

После исправлений, без commit/push:

```bash
apps/api/.venv/bin/python -c \
  'import pathlib, yaml; yaml.safe_load(pathlib.Path(".github/workflows/ci.yml").read_text()); print("YAML_OK")'

cd apps/api && .venv/bin/python -m pytest \
  tests/test_activation_contracts.py \
  tests/test_today_fixture_contract.py -q

cd /opt/solarsage-astro/apps/solarsage && \
  python -m pytest tests/test_activation_schema.py -q

cd /opt/solarsage-astro
pnpm contracts:fixture:check
pnpm contracts:check
npx vitest run
npx tsc --noEmit

rg -n '\\bas any\\b|Record<string, any>|as unknown as|@ts-ignore|@ts-expect-error' \
  __tests__/contracts/today-fixture-roundtrip.test.ts \
  e2e/mock-visual/fixtures/day-v2-2026-07-08.ts \
  lib/presentation/today-v2.ts

E2E_BASE_URL=http://127.0.0.1:3003 \
  npx playwright test \
    e2e/mock-visual/day-v2.spec.ts \
    e2e/dev-timing-fixture.spec.ts \
    --project=mobile \
    --update-snapshots=none

git diff HEAD --check
git diff --cached --check
git status --short --branch
```

Если browser gate снова меняет любой snapshot/asset или падает после
baseline repair — остановиться и вернуть artifacts; ничего не обновлять
повторно.

## 10. Callback R2

Вернуть:

```text
READY_S1_W3_REVIEW_R2
head: <sha>
yaml_parse: PASS
guard_exact_route: PASS
guard_exact_specifier: PASS
guard_await_dynamic: PASS
guard_exact_count_one: PASS
guard_missing_token_fails: PASS
frontend_any_scan: 0
single_fixture_source: PASS
normalizer_actual_stderr_sanitized: PASS
check_mode_bytes_unchanged: PASS
wrapper_canonical_only: PASS
grace_contracts_truthful: PASS
readme_version_rule_corrected: PASS
api_tests: <count>
sidecar_tests: <count>
full_vitest: <files/tests>
tsc: PASS
contracts_check: PASS
visual_e2e_no_update: <count>
binary_split:
  restored_pixel_identical_assets: 2
  baseline_repair_files_only: 2
  s1_w3_binary_files: 0
commit: NOT_YET
push: NOT_YET
```
