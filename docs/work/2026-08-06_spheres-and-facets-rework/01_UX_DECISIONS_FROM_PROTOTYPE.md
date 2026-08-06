# 01 — UX-решения по итогам sandbox-прототипа (владелец, 2026-08-06)

Статус: решения владельца, обязательны к реализации вместе с `00_MASTER_TZ.md`.
Прототип: `fixture=17_spheres_facets_finance&hero=unified` и `18_quiet_facets_new_spheres`,
скриншоты `artifacts/prototype-spheres/`. Прототипный код — референс реализации
(компоненты уже написаны в боевых файлах, см. §8).

## 1. Convergence-день: unified-подача вместо hero-плиты

- Hero-карточка «Что сошлось» (тинт на всю карточку) **удаляется полностью**:
  компонент `ConvergenceHero` выводится из кода, варианты full/band были только
  прототипной разведкой.
- `convergence_today` рендерится тем же языком, что quiet day: секция
  «Что сошлось <дата>» + маркер «Доказательность: высокая|средняя» + карточки
  сфер (`<Сфера> · N сигналов сегодня`), сфера с большим числом сигналов — первая.
- Карточка сигнала: facet label (или label сферы при facet=null) + чип его
  полярности + заголовок астро-факта + пик/окно + summary; клик → drilldown.
- Референс: `components/today-convergence/convergence-unified-list.tsx`
  (testids: `convergence-unified-list`, `unified-group-<sphere>`,
  `unified-signal-<groupId>`, `convergence-evidence-badge`).
- Плоский narrative-список из 9 абзацев под hero удаляется; per-signal тексты
  живут в карточках сигналов (summary/meaning/action группы).
- Прототипный шов `heroVariant` из продового пути убрать (оставить unified как
  единственную ветку).

## 2. Модалки везде; страницы сфер выводятся

- Все 12 тайлов навигатора — кнопки, открывающие drilldown-шторку
  (`aria-haspopup="dialog"`). Пустая сфера открывает ту же шторку с блоком
  «Сегодня сигналов нет» (`impulse-drilldown-empty`, `data-state="empty"`).
- Ссылка «Полный разбор сферы» из шторки удалена.
- Маршрут `app/(grace)/day/spheres/[key]` и компоненты sphere-page удалить;
  ссылки на него (hero SphereLink и пр.) уходят вместе с hero.
- Backend endpoint `GET /api/spheres/<key>` **сохранить** — он источник
  «Контекста сферы» для шторки. Endpoint `today_sphere_drilldown`
  (`/api/day/snapshots/...` drilldown) фронтендом не используется — удалить со
  схемой и тестами.
- Facet label в карточке факта — своей строкой над временем и чипом полярности.

## 3. Контекст сферы: содержательный, человеческий

Канон расширяется (backend `today_sphere_page_service`):

- `periodSynthesis: string | null` — синтез одновременно действующих периодов
  сферы («их сумма»), рендерится первым блоком «Сейчас действует»
  (`impulse-drilldown-period-synthesis`).
- `period.note: string | null` — простым языком, что значит планета/техника
  периода и что это даёт в этой сфере («Венера — планета денег…»), внутри
  карточки периода (`impulse-drilldown-period-note-<id>`).
- Сроки периодов — русская локализация «15 января 2026 — 15 января 2027»
  (сейчас сырые ISO на проде).
- Generic-блок техники («Что это/Как влияет/Что можно заметить») остаётся
  вторичным, после note.
- Обязательный контент per сфера: натальные абзацы с объяснением домов
  (чем дом отвечает + что там стоит) без template-глитчей.
- Найденные на проде баги натальных текстов починить в генераторе:
  «в prefixes у знака Козерога», «в знак Страсти со Сагитария»,
  «Четвёртая часть домов», опечатка «ответственой».
  Регрессионный тест: narrative/sphere-page тексты не содержат английских
  шаблонных остатков (расширить sanitizer-стиль проверки).

## 4. «Как это рассчитано»: статистика + колесо

- Строка статистики из существующего payload (без новых API):
  «Для этого дня собрано N физических факта неба; из них по правилам
  доказательности отобрано M публичных сигналов» + честная строка по
  birth-time mode (exact/bucket/unknown). Testid `how-calculated-stats`.
- Интерактивное колесо `NatalChartWheel` внутри disclosure
  (`how-calculated-chart`). Рендерить client-only: координаты SVG через
  sin/cos расходятся на 1 ULP между Node SSR и браузером → hydration mismatch
  (воспроизведено и починено в прототипе). Если колесо когда-либо SSR'ится в
  проде — округлять координаты в `pointAt`.
- Источник данных колеса в проде: существующие натальные данные клиента
  (те же, что у натального разбора); новых API не нужно.

## 5. Темы и токены (багфиксы, не редизайн)

- `.dark` значения для `--tone-*` (значения из прототипа,
  `app/globals.css:136-141`) — иначе hero/чипы в тёмной теме нечитаемы.
- `--phase-*` токены для лунных глифов/чипов (light = legacy 1:1, dark
  поднятые); `phase-glyph.tsx` переведён на них; хардкод тон-точек календаря
  `#43806d/#b07b36` → `bg-(--syn-good)/bg-(--syn-mid)`.
- `lunar-calendar-strip.tsx`: невалидные alpha-суффиксы `${color}30/0d/14` к
  oklch заменены на `color-mix(in oklch, …)`.
- Sandbox-предпросмотр: `useSandboxTheme` (`?theme=`, prefers-color-scheme) и
  `SANDBOX_ALLOWED_DEV_ORIGIN` в `next.config.mjs` — остаются dev-tooling.

## 6. Что удаляется как legacy (полный список)

- `ConvergenceHero` (hero-плита, варианты full/band, SphereLink на страницы сфер).
- `app/(grace)/day/spheres/[key]` + `sphere-page.tsx` и связанные frontend-модули.
- Backend `today_sphere_drilldown.py` endpoint + схема `today_sphere_drilldown`
  + тесты (frontend его не вызывает).
- Старые product keys `money/decisions/shopping` — везде (ТЗ §3), включая
  `BACKEND_TO_PRODUCT_KEY_MAP`-миграцию check-in по §8.4 мастер-ТЗ.
- Старый tile label «смешанно» (заменён на «поддержка + напряжение», §8.3).
- Старые fixtures/snapshots со старой моделью — заменить; `17/18` фикстуры
  прототипа станут каноническими после регенерации контрактов.

## 7. Тесты (дополнение к §9 мастер-ТЗ)

Frontend (vitest):
- today-screen: unified-лист рендерит группы по сферам (2 finance-сигнала на
  одной карточке сферы), evidence badge, facet/null fallback на label сферы;
  quiet-day не изменился; hero-разметки нет в DOM.
- sphere-navigator: 12 тайлов новых ключей — все кнопки с aria-haspopup,
  пустой тайл открывает empty-state шторки; ссылок `/day/spheres/*` нет.
- drilldown: facet строкой; empty-state; period note/synthesis/русские даты
  (по fixture-override); full-link отсутствует.
- how-calculated: stats line по payload (convergence и quiet), birth-time
  строки для exact/bucket/unknown; колесо рендерится только на клиенте.
- facet-labels: покрытие всех facet keys ТЗ §4, unknown → null.

Backend (pytest):
- sphere context: `periodSynthesis` и `note` присутствуют и fail-closed;
  натальные абзацы не содержат английских шаблонных остатков (регрессия на
  «prefixes»/«Страсти»); даты периодов ISO в payload (локализация — фронт).
- Удаление drilldown endpoint: 404 + схема выпилена из OpenAPI.

E2E: обновить affected specs (navigator/links/tiles), новый сценарий
«пустая сфера → модалка → контекст», visual baselines переснять после
реализации (не раньше).

## 8. Референс-реализация (уже в дереве из прототипа)

- `components/today-convergence/convergence-unified-list.tsx` (новый).
- `today-narrative.tsx`: blocks-режим (per-signal блоки) — в unified не
  используется отдельной зоной; решить при реализации: оставить для
  pending/unavailable состояний, blocks-вёрстку перенести в карточки.
- `impulse-drilldown-sheet.tsx`: empty-state, facet-строка, note/synthesis,
  русские даты, удалён full-link, `contextOverride`-шов.
- `sphere-navigator.tsx`: все тайлы — кнопки.
- `how-calculated.tsx`: stats + wheel.
- `lib/display/facet-labels.ts`, обновлённый `sphere-labels.ts`,
  `sphere-icons.tsx`, `today-formatters.tsx` (новые 12 ключей).
- `app/globals.css`: dark `--tone-*`, `--phase-*`.
- Фикстуры `17_spheres_facets_finance.json` (с `__sandboxSphereContext`,
  `__sandboxChart`), `18_quiet_facets_new_spheres.json`.
- `app/sandbox/*`: страницы today/calendar — dev-tooling, остаётся.
