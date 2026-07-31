# 43 — P7-F1 TODAY CONVERGENCE FIXTURES TZ — Today Convergence Rewrite

Controller packet по coder-loop §10.7. Архитектор: main agent. Кодер: codex CLI
(второй), cwd `/tmp/solarsage-convergence-b`, ветка `work/today-convergence-2b`.

ВАЖНО: ты и есть coder. Skill coder-loop использовать НЕЛЬЗЯ — задачу
выполняешь сам и отчитываешься здесь ревьюеру. Параллельно в другом worktree
идёт работа над Day endpoint — backend файлы НЕ трогать (см. §7).

## 1. Packet title

P7-F1 — эталонная fixture-матрица нового Today: 16 payload fixtures + 3
Yesterday/check-in fixtures с zod-валидацией и per-fixture invariants.
Foundation для всех последующих W7 frontend срезов.

## 2. Phase / Wave

W-TODAY-CONVERGENCE-REWRITE / P7 (W7 frontend), срез F1.

## 3. Modules

- Новый: `M-TEST-TODAY-CONVERGENCE-FIXTURES` —
  `__tests__/fixtures/today_convergence_v2/` + тест-валидатор.
- Никаких production-файлов.

## 4. Goal

Каталог `__tests__/fixtures/today_convergence_v2/` содержит 16 Today payload
fixtures и 3 Yesterday fixtures, каждая валидируется generated zod root и
несёт явные structural invariants. Это единственный эталон для component,
visual и e2e тестов W7.

## 5. Норматив (прочитать перед кодированием)

- `docs/work/2026-07-29_today-convergence-rewrite/03_W7_FRONTEND_DESIGN_TZ.md`
  §13 (строки 295-310): список 16 fixtures + 3 Yesterday fixtures; §2
  (контрактные оси); §11 (test contract).
- `docs/work/2026-07-29_today-convergence-rewrite/04_W2_W3_RUNTIME_CONTRACT_TZ.md`
  §3.1-3.3: envelope, матрица состояний, caps, EventTime, claim shape.
- `docs/work/2026-07-29_today-convergence-rewrite/05_W5_W8_OPERATIONS_AND_RELEASE_TZ.md`
  §4 (строки 170-183): content-cap gate — fixture №4 (hero 3 сферы) и №8
  (quiet mainEvent + 3 impulses + lookahead) — максимальные legal shapes.
- Wire schema (источник истины по полям):
  `packages/contracts/_generated.zod.ts` — `TodayConvergencePayloadWireSchema`
  и `YesterdayCheckinResponseWireSchema` (последний — после P4-D3B уже в
  HEAD этой ветки).
- API-сторона fixtures (reference формы):
  `apps/api/tests/fixtures/contracts/today-convergence-*.json` (5 шт) —
  смотреть для реалистичности, но НЕ копировать placeholder IDs:
  frontend fixtures обязаны использовать канонические формы ID
  (`evt_v1_<32 hex>`, `cvg_v1_<32 hex>`, `mev_v1_<event_id>`).

## 6. Exact write scope

- `__tests__/fixtures/today_convergence_v2/*.json` — 16 Today + 3 Yesterday
  файлов (именование: `01_hero_supportive.json` … `16_locked.json`,
  `yesterday_pre_submit.json`, `yesterday_post_submit.json`,
  `yesterday_no_snapshot.json`)
- `__tests__/fixtures/today_convergence_v2/index.ts` — typed barrel
  (импорт + экспорт fixtures с типами из `packages/contracts/today-convergence.ts`)
- `__tests__/contracts/today-convergence-fixtures.test.ts` — валидатор
- Больше НИЧЕГО (ни production, ни существующие тесты).

## 7. Frozen / Out of scope

- НЕ менять: любые production файлы (components/, lib/, app/, apps/),
  существующие __tests__ файлы, packages/contracts/* (generated уже
  синхронизирован в HEAD), e2e/.
- НЕ удалять старые fixtures (W7 replacement — отдельный атомарный changeset).
- НЕ реализовывать компоненты/хуки/адаптеры.

## 8. Функциональные требования

### 8.1 16 Today fixtures (03 §13)

Каждая — полный валидный `TodayConvergencePayload` (wire camelCase):

1. `hero_supportive` — convergence_today, dayTone supportive, 1 группа
   (evidence high), contentState ready с claims.
2. `hero_tense` — то же, tense.
3. `hero_mixed` — mixed, группа с 2 сферами (primary+secondary).
4. `hero_three_spheres` — 3 группы, union сфер ровно 3, готовый narrative
   для всех групп (максимальный hero shape для 700-token gate).
5. `quiet_steady` — quiet_day, steady, 3 импульса + lookahead
   (snapshotId следующего дня).
6. `quiet_tense_impulse` — quiet_day, 1 tense импульс.
7. `quiet_zero_impulses` — quiet_day, mainEvent отсутствует, impulses=0,
   periodContext kind=no_strong_accent (title из реестра — любая
   осмысленная RU строка, versioned).
8. `quiet_main_max` — quiet_day, mainEvent + 3 импульса + lookahead
   (максимальный legal quiet shape).
9. `quiet_general_background` — quiet_day, `personal=false`, unknown mode,
   periodContext active_period, impulses с date/partofday time.
10. `content_pending` — hero, contentState=pending, все LLM-поля null.
11. `content_unavailable` — quiet, contentState=unavailable, LLM null,
    deterministic поля заполнены.
12. `state_unavailable` — state=unavailable: snapshotId/publishedAt/
    dayTone/personal null, блоки пусты, contentState=unavailable.
13. `birth_bucket` — bucket mode (morning), EventTime partofday, без
    HH:MM, capabilities houses/angles/lots/exactTiming=false.
14. `birth_unknown` — unknown mode, rangeStart 00:00 / rangeEnd 24:00,
    EventTime partofday|date.
15. `access_preview` — preview: state/dayTone/personal заполнены,
    previewTeaser ≤3 сфер, контентные блоки пусты, contentState=not_needed.
16. `access_locked` — locked: state=null, всё пусто, contentState=not_needed.

Общие требования к fixtures:

- `events[]` ровно = union ссылок блоков (root-инвариант схемы).
- claims: `sourceEventIds` ⊆ ids блока; summary ≤ 220 chars; RU текст,
  осмысленный, без template-ощущения (это эталон копирайта).
- Время: exact → HH:MM peak/start/end; bucket → partofday; unknown →
  partofday|date. Никаких точных часов вне exact.
- `schemaVersion: 1`, `formulaVersion: "today-convergence-2"`,
  `calculationVersion: "ss-calc-1.3.0"`.
- Даты фиксированные (targetDate 2026-08-01, lookahead 2026-08-02), IANA tz
  Europe/Moscow, publishedAt ISO.

### 8.2 3 Yesterday fixtures

Валидные по `YesterdayCheckinResponseWireSchema`:

- `yesterday_pre_submit`: hadCheckin=false, checkin=null,
  forecastAvailable=true, forecastRecap=null.
- `yesterday_post_submit`: hadCheckin=true, checkin заполнен (минимально
  необходимые поля CheckinResponse — смотри zod), forecastAvailable=true,
  forecastRecap={snapshotId, state, dayTone, sphereKeys≤3}.
- `yesterday_no_snapshot`: hadCheckin=true, checkin заполнен,
  forecastAvailable=false, forecastRecap=null.

### 8.3 Валидатор-тест

`__tests__/contracts/today-convergence-fixtures.test.ts`:

- каждая fixture парсится соответствующим WireSchema (assert success, на
  failure печатать zod issues);
- per-fixture structural invariants из §8.1 (напр. №4: union сфер == 3 и
  convergences.length == 3; №8: mainEvent != null && impulses.length == 3
  && lookahead != null; №12: snapshotId === null; №15: events.length == 0);
- negative guards: fixture №13/14 не содержат HH:MM в events time
  (regex \d{2}:\d{2} отсутствует в peak/start/end); fixture №16 не содержит
  snapshotId;
- barrel index.ts экспортирует все 19 fixtures typed.

## 9. Must-preserve invariants

- `npx vitest run __tests__/contracts` зелёный целиком.
- Полный `npx vitest run` не хуже, чем до packet (1354+ passed).
- Ноль изменений вне §6.

## 10. Verification

```bash
cd /tmp/solarsage-convergence-b
npx vitest run __tests__/contracts/today-convergence-fixtures.test.ts 2>&1 | tail -3
npx vitest run __tests__/contracts 2>&1 | tail -3
npx tsc --noEmit 2>&1 | tail -3
```

## 11. Expected evidence

- Список из 19 fixture файлов + index.ts + тест.
- Вывод команд §10; по одному компактному JSON-примеру для №4, №8 и №15 в
  отчёте (первые ~40 строк каждого).

## 12. Escalation rule

Zod-схема не принимает форму, требуемую нормативом (напр. quiet без
импульсов с periodContext) → НЕ ослаблять fixture под схему молча:
задокументировать расхождение в отчёте и остановиться по этой fixture.
Нужны изменения production/generated файлов → СТОП, доложить.

## 13. No-commit rule

Ничего не коммить и не пушить — коммит делает ревьюер.
