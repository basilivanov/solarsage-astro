# ТЗ: «Синастрия» — исправление post-implementation дефектов UI, контента и data contract

**Дата:** 2026-07-26  
**Статус:** ready for implementation  
**Приоритет:** P0/P1  
**Зона:** React frontend, API projection, sidecar contract, LLM pipeline, versioning, visual/E2E tests  
**Связанные документы:**

- `00_TZ_REACT_PARITY.md` — основной visual/product source of truth;
- `01_TZ_INTERACTIVE_SVG_WHEEL.md` — нормативный контракт интерактивной карты;
- HTML-reference: ветка `prototype/synastry-html`, `public/prototypes/synastry/`.

---

## 1. Причина нового этапа

Первичная реализация формально добавила основные блоки HTML-прототипа, однако в текущем продукте остаются дефекты трёх разных классов:

1. **Mobile layout:** элементы не помещаются в доступную ширину, появляются горизонтальный скролл, переносы и визуально обрезанные подписи.
2. **Data projection:** backend рассчитывает или запрашивает часть данных, но не сохраняет либо не отдаёт их frontend.
3. **Content routing:** экран подробного аспекта получает технический fallback вместо полноценного drill-down.
4. **Legacy data:** уже созданные отчёты и aspect detail сохраняют старую неполную структуру и не исправятся одной заменой React-компонентов.

Работу нельзя закрывать локальными изменениями CSS. Нужно восстановить полную цепочку:

`sidecar facts → scoring → narrative generation → persistence → API projection → React presentation → visual/E2E contract`.

---

## 2. Definition of Done

Работа считается завершённой, когда одновременно выполнены условия:

1. На ширинах **320, 360, 375, 390/393 и 430 px** ни один экран синастрии не имеет горизонтального overflow.
2. Все фильтры списка видны без горизонтального свайпа.
3. Score и три индикатора баланса визуально читаются и не ломают карточку при значениях от `0` до `100`.
4. Ни в одном пользовательском UI нет строк вида `sun conjunction sun`, `Sun square Moon`, engine id или другого сырого технического английского текста.
5. У каждого аспекта есть русская подпись, корректный символ, орбис и короткое понятное описание.
6. Для отчёта с точным временем рождения раздел наложения домов содержит реальные рассчитанные cross-house overlays либо явную диагностическую ошибку; вечного текста «Наложения домов рассчитываются» в состоянии `ready` нет.
7. Human translation содержит связку `астрологический фактор → понятное поведение → жизненная сцена` и открывает drill-down по стабильному `aspectId`.
8. Drill-down показывает значения обеих планет, механику аспекта, 3–4 жизненные сцены, 3–5 repair-действий и блок «Это не означает».
9. Accordion «Где легко, где придётся работать» при открытии всегда показывает содержательный текст.
10. Старые активные отчёты автоматически обновляются до нового schema/prompt version без повторного списания кредита.
11. Visual tests действительно проверяют карточки и detail screen, а не маскируют проблемные области.

---

## 3. Зафиксированные root causes

### P0-1. Endpoint drill-down обходит полноценный service

Текущий route:

`GET /api/synastry/{partner_id}/aspect/{aspect_id}`

в `apps/api/app/api/synastry.py` самостоятельно читает `SynastryAspectDetail` и при отсутствии payload возвращает фиктивный fallback:

- `Взаимодействие двух энергий в натальных картах.`;
- `Повседневный контакт двух личностей.`;
- `Сохраняйте взаимное уважение и диалог.`

При этом полноценная генерация уже реализована в:

`SynastryService.get_aspect_drilldown(...)`.

**Требование:** route обязан делегировать запрос service и возвращать полный `AspectDrilldown`. Generic fallback удалить. При реальной ошибке генерации возвращать диагностируемую ошибку с возможностью повторной попытки, а не выдавать выдуманный «успешный» текст.

### P0-2. Полный drill-down обрезается в API projection

Даже когда `SynastryAspectDetail.payload_json` существует, текущий route отдаёт только:

- title;
- tone;
- tech signature;
- explanation;
- scenario;
- advice.

Теряются:

- `aspect_symbol`;
- `aspect_kind_label`;
- `orb_text`;
- `headline`;
- `owner_planet`;
- `partner_planet`;
- `aspect_mechanics`;
- `scenes`;
- `repairs`;
- `not_means`.

**Требование:** API возвращает schema целиком, без повторной ручной проекции сокращённого legacy DTO.

### P0-3. Описания сфер генерируются, но не сохраняются

`build_report_prompt()` просит LLM вернуть `spheres`, однако `run_report_pipeline()` не переносит их в `narrative_payload_json`. Deterministic payload содержит только `id/title/score/tone`.

В результате `SynastrySphere.description === null`, а React показывает меняющийся chevron без содержимого.

**Требование:** объединять deterministic score/tone и narrative description в единый массив сфер report schema.

### P0-4. Короткие описания аспектов генерируются, но теряются

Prompt запрашивает `aspect_shorts`, однако pipeline их не сохраняет и не связывает с аспектами. API берёт `description` из deterministic payload, где этого поля нет.

**Требование:** сохранять `aspect_shorts` по стабильному `aspectId`, а не по позиции без проверки. Каждый аспект в report response должен иметь русское `short/description`.

### P0-5. Наложения домов не являются детерминированными cross-house facts

Текущий sidecar возвращает `partner_houses`, но не возвращает `owner_houses`. В API-сервисе дом партнёрской планеты вычисляется по домам самого партнёра — это натальная позиция партнёра, а не наложение его планеты на карту пользователя.

Текущие `house_overlays` полностью зависят от LLM и могут быть пустыми. Это нельзя использовать как источник астрологического факта.

**Требование:** house overlay сначала рассчитывается детерминированно, затем LLM только переводит факт на человеческий язык.

### P0-6. Старые payload продолжают отображаться после исправлений

У report уже есть:

- `engine_version`;
- `calculation_version`;
- `prompt_version`;
- `report_schema_version`.

У aspect detail есть отдельный `prompt_version`.

Без version bump пользователи продолжат видеть старые пустые spheres, generic drill-down и отсутствующие overlays.

**Требование:** внедрить version-aware regeneration, описанную в разделе 9.

### P1-1. Filters намеренно сделаны горизонтально скроллируемыми

В `synastry-search-filters.tsx` используется `overflow-x-auto`. На телефоне пользователь видит не весь набор `Все / Хорошо подходит / Нормально / Сложно`.

**Требование:** весь набор виден одновременно без свайпа.

### P1-2. Counter blocks не рассчитаны на узкий mobile viewport

В partner card и score panel три длинные фразы помещены в `grid-cols-3` одной строкой:

- `N поддерживают`;
- `N неоднозначны`;
- `N напрягают`.

На 320–390 px текст сжимается, ломается и визуально обрезается.

### P1-3. Human translation header конфликтует по ширине

Title и `item.tech` стоят в одной строке с `justify-between`, а tech-блок имеет `flex-none`. Длинная подпись вытесняет заголовок и может выходить за карточку.

### P1-4. Aspect glyph presentation нестабильна

Символы выводятся обычным текстом с `font-bold`; квадрат визуально деформируется. `quincunx` ошибочно использует тот же glyph, что sextile.

---

## 4. Экран списка партнёров

### 4.1. Filters

Заменить горизонтальный scroller на адаптивное размещение.

Допустимые варианты:

- `flex-wrap` с естественной шириной чипов;
- двухстрочный grid;
- grid `2 × 2` на ширине до 359 px и compact inline layout выше.

Обязательные условия:

- все четыре фильтра видны одновременно;
- отсутствует горизонтальный scrollbar;
- высота строки не меньше 36 px;
- touch target не меньше 40 px по высоте с учётом внешнего пространства;
- подписи не обрезаются через ellipsis;
- выбранный фильтр остаётся визуально самым сильным.

Не сокращать продуктовые подписи до непонятных `Хорошо / Средне / Плохо` без отдельного продуктового решения.

### 4.2. Score в карточке

Score оформить как единый устойчивый typographic unit:

- основное число: serif, 28–30 px;
- `/100`: 10–11 px, baseline либо отдельной строкой `из 100`;
- контейнер имеет фиксированную/минимальную ширину, чтобы `9`, `61` и `100` не меняли геометрию header;
- score не должен конфликтовать с кнопкой удаления и ribbon;
- не использовать жирное начертание display-serif.

### 4.3. Баланс факторов

Каждый counter block строится в две строки:

- крупное число;
- подпись ниже.

Пример:

```text
8
поддерживают
```

Требования:

- одинаковая высота трёх блоков;
- число 17–20 px;
- подпись 9.5–11 px;
- `line-height` задан явно;
- нормальный перенос слов, без `break-all`;
- значение `0` показывается явно;
- на 320 px все три блока помещаются без clipping.

### 4.4. Карточка

- Summary: максимум 2 строки, но обрезка не должна выглядеть как сломанная строка.
- Все внутренние зоны имеют `min-width: 0` там, где используется flex.
- Кнопка удаления доступна на touch-устройстве; не полагаться только на `group-hover:opacity-100`.
- Ribbon не перекрывает score или имя.

---

## 5. Детальный экран

### 5.1. Score panel

На mobile сохранить композицию макета: score слева, verdict/summary справа.

Не переводить верхнюю часть в вертикальную колонку только потому, что viewport меньше `sm`.

Требования:

- score box 72–78 px;
- текстовая колонка `min-width: 0`;
- headline переносится максимум на 2 строки;
- summary не обрезается;
- status pill не дублирует headline;
- counters используют двухстрочную структуру из п. 4.3.

### 5.2. Визуальная иерархия

Сохранить различие функций блоков HTML-макета:

- pair hero — открытая центрированная композиция;
- score — самостоятельная основная карточка;
- wheel — светлая цветная поверхность;
- aspect rows — компактные интерактивные строки;
- house overlays — лавандовые мини-карточки;
- translations — белые смысловые карточки со scene;
- spheres — accordion;
- feedback — спокойный финальный блок.

Не возвращаться к одинаковому `border + bg-card + shadow-sm` для всех уровней.

### 5.3. Wheel

Текущую интерактивную двухкольцевую карту не упрощать и не заменять декоративным кругом.

Проверить только регрессии:

- wheel помещается в 320 px;
- SVG не создаёт overflow;
- центральная подпись не выходит за круг;
- aspect hit-area работает пальцем;
- выбранная линия синхронизирована с aspect card;
- approximate mode не показывает недостоверные дома/ASC.

---

## 6. Аспекты и human translation

### 6.1. Нормализованная view model аспекта

Frontend не должен собирать пользовательскую подпись парсингом engine id при каждом render.

API response для каждого аспекта должен содержать минимум:

```ts
interface SynastryAspectView {
  id: string
  ownerPlanetId: string
  partnerPlanetId: string
  ownerPlanetLabelRu: string
  partnerPlanetLabelRu: string
  aspectType: string
  aspectLabelRu: string
  aspectSymbol: string
  orbDegrees: number
  orbLabel: string
  tone: "good" | "mid" | "bad"
  titleRu: string
  shortRu: string
  techSignatureInternal: string
}
```

`techSignatureInternal` не выводится напрямую в UI.

### 6.2. Aspect row

В строке показывать:

1. корректный glyph;
2. русское название контакта;
3. орбис;
4. короткий человеческий смысл в 1–2 строки;
5. понятный affordance подробного просмотра.

Glyph requirements:

- использовать canonical glyph map проекта;
- `conjunction: ☌`;
- `trine: △`;
- `sextile: ⚹`;
- `square: □`;
- `opposition: ☍`;
- `quincunx: ⚻` либо другой единый canonical symbol, но не glyph sextile;
- не применять `font-bold`, искажающий геометрию символа;
- glyph центрирован оптически, а не только через line box.

### 6.3. Human translation

Перестроить header карточки:

- первая строка: tone dot + человеческий title;
- вторая строка: локализованный технический фактор + кнопка `Что значит?`;
- затем основной текст;
- затем отдельный scene block.

Обязательные поля каждой карточки:

- `aspectId`;
- `tone`;
- `title`;
- локализованный `techLabelRu`;
- `text`;
- `scene`.

Если `aspectId` отсутствует, payload считается невалидным и не должен тихо попадать в готовый report.

Запрещено показывать пользователю:

- `sun conjunction sun`;
- `sun_conjunction_sun_0`;
- `Sun trine Moon`;
- пустую или универсальную формулировку, подходящую к любому аспекту.

---

## 7. Наложения домов

### 7.1. Sidecar contract

Расширить sidecar response:

```ts
interface SynastrySidecarResponse {
  ownerPlanets: PlanetPoint[]
  partnerPlanets: PlanetPoint[]
  ownerHouses: HouseCusp[]
  partnerHouses: HouseCusp[] | null
  crossAspects: CrossAspect[]
  precisionFlags: PrecisionFlags
}
```

### 7.2. Deterministic overlay facts

Рассчитать два направления:

1. `partner planet → owner house` — когда карта пользователя полная;
2. `owner planet → partner house` — только если время партнёра точное и partner houses доступны.

Формат:

```ts
interface HouseOverlayFact {
  id: string
  direction: "partner_to_owner" | "owner_to_partner"
  planetOwner: "user" | "partner"
  planetId: string
  planetLabelRu: string
  targetOwner: "user" | "partner"
  house: number
  reliable: boolean
  techLabelRu: string
}
```

LLM получает только готовые facts и создаёт `humanText`, не меняя planet/house/direction.

### 7.3. UI states

Для `report.state === ready` допустимы только состояния:

- `ready_exact`: показаны реальные overlays;
- `ready_partial`: показано доступное направление и объяснено, какое недоступно;
- `unavailable`: указана конкретная причина/ошибка данных.

Строка `Наложения домов рассчитываются.` допустима только в настоящем loading/pending state. В ready report её быть не должно.

---

## 8. Drill-down аспекта

### 8.1. Routing

В route использовать service:

```py
service = SynastryService(db)
return await service.get_aspect_drilldown(
    user_id=user.id,
    partner_id=partner_id,
    aspect_id=aspect_id,
)
```

Не дублировать service logic в API-файле.

### 8.2. Обязательная schema

```ts
interface AspectDrilldownData {
  aspectId: string
  tone: "good" | "mid" | "bad"
  aspectSymbol: string
  aspectKindLabel: string
  orbText: string
  headline: string
  ownerPlanet: PlanetInfo
  partnerPlanet: PlanetInfo
  aspectMechanics: string
  explanation: string
  scenes: Array<{ title: string; text: string }>
  repairs: string[]
  notMeans: string[]
}
```

Обязательные ограничения:

- scenes: 3–4;
- repairs: 3–5;
- notMeans: ровно 3;
- все пользовательские поля на русском;
- headline не равен raw engine id;
- explanation описывает конкретную пару планет и аспект;
- никакого fake-success fallback.

### 8.3. Error state

Если LLM generation не удалась:

- показать `Не удалось подготовить подробный разбор`;
- кнопку `Попробовать ещё раз`;
- логировать error code;
- не подменять ошибку универсальным текстом.

---

## 9. Сферы «Где легко, где придётся работать»

Report schema сферы:

```ts
interface SynastrySphereView {
  id: "intimacy" | "communication" | "daily_life" | "finance"
  title: string
  score: number
  tone: "good" | "mid" | "bad"
  description: string
  support?: string
  friction?: string
  repair?: string
}
```

Минимальное требование — непустой `description` для каждой сферы.

UI:

- первая сфера открыта по умолчанию;
- click по всей строке переключает состояние;
- контент существует независимо от truthy-проверки случайно потерянного поля;
- chevron соответствует реальному состоянию;
- `aria-expanded` и `aria-controls` корректны;
- при открытии появляется текст, а не только меняется иконка.

---

## 10. Content validation

### 10.1. Full report validator

Validator обязан проверять наличие и типы:

- verdict;
- summary;
- translations: 3–5;
- spheres: все четыре обязательные сферы;
- для каждой translation: `title`, `tone`, `tech/aspect reference`, `text`, `scene`;
- связь translation с существующим `aspectId`.

Нельзя принимать report как valid, если обязательный массив отсутствует или пуст.

### 10.2. Drill-down validator

Проверять не только количество, но и обязательное наличие:

- intro/explanation;
- scenes;
- repairs;
- not_means;
- непустые title/text внутри сцен.

### 10.3. Запрет engine copy в user-facing полях

Для полей `title`, `headline`, `short`, `text`, `scene`, `description`, `techLabelRu` отклонять сырой английский словарь:

```text
sun, moon, mercury, venus, mars, jupiter, saturn, uranus,
neptune, pluto, ascendant, conjunction, conjunct, trine,
sextile, square, opposition, quincunx
```

Исключение — внутренние IDs и internal signatures, которые не рендерятся пользователю.

### 10.4. Запрет generic placeholders

Не принимать как содержательный результат фразы:

- `Взаимодействие двух энергий в натальных картах`;
- `Повседневный контакт двух личностей`;
- `Сохраняйте взаимное уважение и диалог`;
- другие заранее определённые универсальные fallback-фразы.

---

## 11. Versioning и обновление существующих отчётов

Ввести новые версии, например:

```text
calculation_version = "2"
prompt_version = "2"
report_schema_version = "synastry/v2"
aspect_detail.prompt_version = "2"
```

Точные значения можно выбрать иные, но они обязаны отличаться от текущих.

### 11.1. Поведение для старого report

При запросе активного партнёра, если report version устарела:

1. не отдавать старый payload как окончательно готовый;
2. создать/запустить новый report для того же partner;
3. не списывать дополнительный кредит;
4. сохранить partner record;
5. сохранить либо перенести user feedback, если он относится к той же паре;
6. показать нормальный processing state;
7. после ready переключить UI на новый report.

### 11.2. Aspect details

Detail с legacy `prompt_version` не использовать. При первом открытии генерировать payload новой версии.

### 11.3. Операционная миграция

Добавить idempotent backfill/job для активных ready reports старой версии. Job должен быть безопасен при повторном запуске и не создавать несколько одновременных report на одну пару/version.

---

## 12. Тесты

### 12.1. Backend unit/integration

Обязательные тесты:

1. Aspect route вызывает `SynastryService.get_aspect_drilldown`.
2. Full structured drill-down не теряет поля в API response.
3. При отсутствии detail не возвращается generic fake-success fallback.
4. Pipeline сохраняет `aspect_shorts` и связывает их с aspect IDs.
5. Pipeline сохраняет descriptions всех четырёх spheres.
6. Translation без aspect link отклоняется validator.
7. Exact sidecar response формирует оба допустимых направления overlays.
8. Approximate partner time не формирует owner→partner overlays, но сохраняет partner→owner, если оно достоверно.
9. Ready report не отдаёт indefinite `calculating` placeholder.
10. Version mismatch запускает regeneration без credit spend.

### 12.2. Frontend component tests

1. Filters рендерятся все четыре и не используют horizontal overflow container.
2. Score корректно отображает `0`, `9`, `61`, `100`.
3. Counter blocks корректны для `0/0/0`, `12/3/11`, трёхзначных edge values.
4. Aspect title и tech line не выводят raw English signature.
5. Square/quincunx glyph соответствуют canonical map.
6. Translation вызывает callback с `aspectId`, не с tech string.
7. Sphere click показывает description.
8. House overlays имеют отдельные exact/partial/unavailable states.

### 12.3. Visual/E2E matrix

Снимать snapshots минимум на:

- 320 × 700;
- 375 × 812;
- 393 × 852;
- 430 × 932.

Сценарии:

1. List с несколькими карточками и score `61`.
2. List с длинным именем и длинным summary.
3. Detail exact.
4. Detail approximate.
5. Aspect drill-down с максимальной длиной контента.
6. Spheres: первая открыта, затем открыта другая.
7. House overlays exact/partial.

Для каждого viewport assertion:

```js
expect(
  await page.evaluate(() => document.documentElement.scrollWidth)
).toBeLessThanOrEqual(
  await page.evaluate(() => document.documentElement.clientWidth)
)
```

### 12.4. Исправить текущий visual test

Сейчас screenshot списка маскирует всю partner card, поэтому не может обнаружить дефекты score, counters и текста.

Требование:

- не маскировать карточку целиком;
- стабилизировать только действительно динамические значения точечными masks;
- добавить screenshots detail/drill-down;
- добавить assertions, что accordion content видим;
- добавить assertion отсутствия строк `sun`, `conjunction`, `square` в пользовательском тексте страницы.

---

## 13. Файлы для изменения

### Frontend

- `components/synastry/synastry-search-filters.tsx`
- `components/synastry/synastry-partner-card.tsx`
- `components/synastry/synastry-score-panel.tsx`
- `components/synastry/synastry-aspect-row.tsx`
- `components/synastry/synastry-translations.tsx`
- `components/synastry/synastry-house-overlays.tsx`
- `components/synastry/synastry-spheres.tsx`
- `components/synastry/aspect-drilldown-sheet.tsx`
- `components/synastry/synastry-detail-screen.tsx`
- `lib/api/synastry.ts`

### API / services

- `apps/api/app/api/synastry.py`
- `apps/api/app/services/synastry_service.py`
- `apps/api/app/services/synastry_llm.py`
- `apps/api/app/schemas/synastry.py`
- при необходимости models/migration/version constants.

### Sidecar

- `apps/solarsage/solarsage/services/synastry.py`
- `apps/solarsage/solarsage/schemas/synastry.py`

### Tests

- `e2e/mock-visual/synastry.spec.ts`
- `__tests__/synastry/*`
- `apps/api/tests/test_synastry_api.py`
- `apps/api/tests/test_synastry_service.py`
- `apps/api/tests/test_synastry_llm.py`
- `apps/solarsage/tests/test_synastry.py`

---

## 14. Порядок реализации

### Этап A — P0 routing и data preservation

1. Перевести aspect route на service.
2. Исправить full DTO projection.
3. Сохранять aspect shorts и sphere descriptions.
4. Ужесточить validators.

### Этап B — P0 deterministic house overlays

1. Расширить sidecar owner/partner houses.
2. Рассчитать cross-house facts.
3. Добавить narrative translation поверх facts.
4. Ввести exact/partial/unavailable UI states.

### Этап C — P0 versioning

1. Bump report/aspect versions.
2. Реализовать no-charge regeneration.
3. Добавить idempotent backfill.

### Этап D — P1 responsive UI

1. Filters без horizontal scroll.
2. Score/counters.
3. Translation header.
4. Aspect glyphs/labels.
5. Detail composition parity.

### Этап E — tests и visual acceptance

1. Backend integration.
2. Frontend interaction.
3. Полная mobile visual matrix.
4. Сверка с HTML reference.

---

## 15. Запрещённые способы «закрыть» задачу

Нельзя:

- просто уменьшить весь шрифт, чтобы текст формально влез;
- оставить скрытый horizontal scroll у filters;
- скрыть counters на маленьких экранах;
- заменить отсутствующий контент generic copy;
- считать `partner planet in partner natal house` наложением домов пары;
- просить LLM придумать house number;
- показывать raw engine signature пользователю;
- чинить только новые отчёты, оставив старые payload без migration/versioning;
- маскировать проблемные блоки в screenshot tests;
- объявлять accordion работающим, если меняется только chevron.

---

## 16. Финальный acceptance checklist

- [ ] 320 px: filters видны полностью, overflow отсутствует.
- [ ] Score `61/100` выглядит цельно на list и detail.
- [ ] Три counter block не обрезаны.
- [ ] Detail screen соответствует композиции HTML-reference.
- [ ] Wheel не регрессировал.
- [ ] Aspect glyphs ровные и корректные.
- [ ] Все aspect labels и tech labels локализованы.
- [ ] У аспектов есть содержательные short descriptions.
- [ ] Exact house overlays рассчитаны детерминированно.
- [ ] Approximate state честно показывает доступную/недоступную часть.
- [ ] Human translation содержит title, text и scene.
- [ ] Кнопка `Что значит?` передаёт `aspectId`.
- [ ] Drill-down содержит все структурные разделы.
- [ ] Generic fallback удалён.
- [ ] Каждая sphere раскрывается с текстом.
- [ ] Старые reports обновляются без повторного списания кредита.
- [ ] Visual tests покрывают list, detail, overlays, spheres и drill-down.
- [ ] Partner cards больше не скрыты общей mask в screenshot test.
