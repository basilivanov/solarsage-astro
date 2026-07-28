# W4-F1 Amendment: frontend migration на TodayFocus без двойного сюжета

Дата: 2026-07-28  
Phase / Wave: **W4-TODAY-CONVERGENCE**, F1 migration amendment  
Родитель: `27_TZ_W4_F1_TODAY_FOCUS_UI.md`  
Семантический backend-контракт: `27_TZ_W4_AMENDMENT_PUBLIC_EVENT_SELECTION.md`  
Производительность/rollout: `29_TZ_W4_O1_PREGEN_CACHE_RELIABILITY.md`  
Роль: frontend coder + reviewer. Ничего не коммитить и не пушить — коммит
делает ревьюер.

## 1. Почему нужен amendment

Backend уже отдаёт `focus` в generated API contract, но старый UI adapter и
старый `ActivationEvidenceCard` исторически читают `v2.activationSummary`.
Если просто вставить новую карточку, пользователь увидит два конкурирующих
сюжета: новый «Что сошлось именно сегодня» и старый headline. Это нарушает
канон единого source of truth и делает canary бессмысленным.

Цель этого документа — определить миграцию потребителя, а не новый дизайн.
Визуальная модель может выбрать композицию, отступы и motion, но не может
изменить state, cardinality, порядок событий или fallback policy.

## 2. Entry gate и зависимости

1. Backend C2 должен быть принят clean commit-ом; незакоммиченный diff
   текущего кодера не считается контрактом.
2. F1 проверяется на payload, прошедшем OpenAPI/TS parity и sanitized fixtures
   из `30_TZ_W4_CANARY_SANITIZED_FIXTURES.md`.
3. До production routing должен быть принят O1 cache/pregen gate. В dev можно
   проверять UI на fixture с `contentState="unavailable"`.
4. Если wire schema меняется, сначала обновляется generated contract, затем
   adapter и только потом компоненты. Рукописные дубли `TodayFocus` запрещены.

## 3. Единственный потребитель сюжета

### 3.1. Adapter boundary

`lib/adapters/today-payload.ts` обязан передать `api.focus` в адаптированный
payload без пересчёта и без текстового fallback:

```text
api.focus отсутствует → payload.focus = undefined/null (legacy-compatible)
api.focus присутствует → payload.focus = тот же validated TodayFocus
api.focus невалиден → adapter возвращает contract error по существующему
                         policy; не подставляет activationSummary
```

Adapter не должен:

- выбирать top-3 события или сферы;
- сортировать events/featuredSpheres;
- форматировать `occursAt` в часы;
- строить human title из machine key;
- превращать `contentState=unavailable` в ready.

В `lib/contracts/today.ts` и `packages/contracts/index.ts` используется один
generated `TodayFocus`/`TodayFocusEvent`. Поля `focus` остаются optional/nullable
для старых cache rows и старых API payloads.

### 3.2. Screen routing

`components/today/today-screen.tsx` применяет ровно одну ветку:

| Payload | Что рендерится | Что запрещено |
|---|---|---|
| `focus != null` | `TodayFocusCard` как единственный focus-story | headline из `activationSummary` в том же story-slot |
| `focus == null/undefined` | controlled legacy `ActivationEvidenceCard` для старого payload | выдавать legacy как новый «Что сошлось» |
| `focus.contentState=unavailable` | TodayFocus facts + честное сообщение | legacy headline/шаблонный прогноз |
| `focus.state=background_only/no_accent` | компактное deterministic состояние | рисовать fake convergence card |

Legacy-компонент и его API-поля не удаляются в этом срезе. Их consumer audit и
удаление — отдельная задача после того, как все cache/API versions имеют
`focus`.

## 4. Structural UI contract

Корневой блок:

```tsx
<section
  data-testid="today-focus"
  data-state="convergence_today|single_impulses|background_only|no_accent|unavailable"
  data-content-state="ready|pending|unavailable|not_needed"
>
```

Обязательные дочерние selectors/attributes:

- `data-testid="today-focus-event"` на каждой public event row;
- `data-event-id`, `data-event-kind`, `data-event-relation` — стабильные
  machine attributes для тестов, не видимый текст; relation имеет только
  `convergence_event|independent_event`;
- `data-testid="today-featured-sphere"` и `data-sphere-key` на каждой featured
  sphere row;
- retry только через `data-testid="today-focus-retry"`, `role="button"` и
  существующий refetch callback;
- `pending`: `role="status"`, `aria-busy="true"`;
- `unavailable`: `role="alert"` либо связанный status region;
- disclosure «Как это рассчитано»: `aria-expanded` + `aria-controls`.

Динамический LLM-текст не является единственным test oracle. Тест проверяет
state attributes, IDs, kind, cardinality и порядок DOM.

## 5. Семантика и отображение

### 5.1. Convergence

`convergence_today` показывает:

1. один заголовок сюжета и summary (если `ready`);
2. от 0 до 3 backend-selected events в полученном порядке;
3. от 0 до 3 `featuredSpheres`, затем полный независимый список 12 сфер ниже;
4. action только если для первой featured sphere пришёл validated action.

Позиция строки не определяет роль события. `data-event-relation` вычисляется
чистым presentation helper из provenance partition (§3.5 amendment):
intersection `event.sourceActivationIds` и
`focus.convergence.sourceActivationIds` даёт `convergence_event`, остальные —
`independent_event`. Это не client ranking и не астрологический пересчёт.
Если позже backend добавит relation в wire, helper обязан проверить parity, а
не поддерживать два разных правила. Для `single_impulses` relation всегда
`independent_event`.

### 5.2. Single/background/no accent

- `single_impulses`: eyebrow «СОБЫТИЯ ДНЯ», events без слов «сошлось» и без
  convergence summary.
- `background_only`: контекст периода допускается в technical disclosure, но
  не становится timed event.
- `no_accent`: короткое спокойное состояние без пустых event placeholders.
- `unavailable`: deterministic facts (если они есть) остаются видимыми,
  LLM-owned поля не показываются.

### 5.3. Content states

| State | UI policy |
|---|---|
| `ready` | показать validated copy и facts |
| `pending` | deterministic skeleton; не выдумывать title/meaning |
| `unavailable` | показать факты и ровно «Персональный разбор пока не готов» |
| `not_needed` | не показывать LLM-секции; не считать ошибкой для background/no-accent |

Текст сообщения фиксирован и не зависит от provider error details. Никаких
универсальных fallback-абзацев, `activationSummary.headline` или ручного
пересказа на фронтенде.

## 6. Время и порядок

- Backend сохраняет canonical `occursAt` instant и timezone.
- Frontend переводит instant в локальные часы только через существующий
  date/time utility; нельзя использовать `new Date(...).toISOString()` как
  пользовательское время.
- Display order уже задан backend. Клиент отображает массив как есть.
- `occursAt=null` отображается без часов (или с нормативным kind-label из
  дизайна) и всегда после timed rows; `00:00` нельзя подставлять.
- Нельзя сортировать по title, strength, relation или индексу featured sphere.

## 7. Exact write scope

Если соответствующий файл уже изменён текущим кодером, reviewer сверяет его с
этим контрактом и не создаёт второй parallel implementation.

- `lib/contracts/today.ts` — только generated-derived type/schema parity;
- `lib/adapters/today-payload.ts` — прокинуть/провалидировать `focus`, без
  fallback и без ranking;
- `components/today/today-focus.tsx` — semantic rendering states/rows;
- `components/today/today-screen.tsx` — branch routing и один story-slot;
- `__tests__/lib/adapt-payload.test.ts` и/или
  `__tests__/contracts/today-fixture-roundtrip.test.ts` — adapter parity;
- `__tests__/components/TodayFocus.test.tsx`,
  `__tests__/components/TodayScreen.test.tsx` и downstream suite — coexistence.

Не менять backend, sidecar, generated OpenAPI вручную, SphereDetailsSheet,
legacy API removal или visual baseline без отдельного TZ.

## 8. Acceptance matrix

Обязательны проверки:

1. `focus` с canary 28.07 даёт один focus-story и три rows с теми же IDs/order.
2. Payload без `focus` сохраняет legacy branch и не ломает старые tests.
3. Payload с `focus.contentState=unavailable` не показывает legacy headline.
4. `convergence_today` и `single_impulses` не получают одинаковый eyebrow или
   текст «сошлось».
5. 0/1/2/3 events и 0/1/2/3 featured spheres не создают phantom rows.
6. Null `occursAt` не получает fake time и не вызывает render exception.
7. Клик featured sphere вызывает существующий `onSphereSelect` ровно один раз.
8. Accessibility tree видит root/state/status/disclosure, а icon-only controls
   имеют `aria-label`.
9. Permutation payload в UI не меняет backend order и не запускает client sort.
10. Real e2e не импортирует `lib/mocks` в production path; fixture route остаётся
    test-only.

Минимальная команда проверки:

```bash
npx vitest run \
  __tests__/components/TodayFocus.test.tsx \
  __tests__/components/TodayScreen.test.tsx \
  __tests__/lib/adapt-payload.test.ts \
  __tests__/contracts/today-fixture-roundtrip.test.ts
```

## 9. Rollout и rollback

1. Выпустить adapter/component с legacy compatibility.
2. На dev проверить sanitized fixtures A–H из документа 30.
3. После O1 pregen/coverage gate включить focus consumer для новой cache
   identity.
4. При rollback скрыть только новый focus branch либо вернуть старый payload
   по его старой identity; не смешивать новый narrative со старым ranking.

## 10. Evidence и escalation

Reviewer получает diff, Vitest output, accessibility snapshot и таблицу
payload→render branch. Любая попытка добавить client ranking, fallback-copy,
второй headline или изменение wire schema — стоп и отдельное согласование.
