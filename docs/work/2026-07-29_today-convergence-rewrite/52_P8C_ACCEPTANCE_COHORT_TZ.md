# 52 — P8-C ACCEPTANCE COHORT SEEDER TZ — Today Convergence Rewrite

Controller packet по coder-loop §10.7. Архитектор: main agent. Кодер: codex CLI
(первый), cwd `/tmp/solarsage-convergence-impl`, ветка `work/today-convergence-2`.

ВАЖНО: ты и есть coder. Skill coder-loop использовать НЕЛЬЗЯ — задачу
выполняешь сам и отчитываешься здесь ревьюеру.

## 1. Packet title

P8-C infra — воспроизводимый acceptance cohort seeder: exact/bucket/unknown
профили × full/preview/locked access на фиксированных датах через
существующий Telegram HMAC + profile flow, с учётом в существующем E2E
cleanup ledger.

## 2. Phase / Wave

W-TODAY-CONVERGENCE-REWRITE / P8-C (product acceptance infra).

## 3. Modules

- Новый: `M-E2E-ACCEPTANCE-COHORT` — `e2e/acceptance-cohort.ts`
- Tests: `e2e/acceptance-cohort.spec.ts` (self-check, skipped без
  E2E_BASE_URL)

## 4. Goal

Playwright-пригодный helper `seedAcceptanceCohort(baseURL)` создаёт через
РЕАЛЬНЫЙ API (никаких test-only routes, никакого route interception):

- 3 пользователя с профилями: `exact` (HH:MM), `bucket` (morning),
  `unknown` (без времени) — через Telegram HMAC auth (существующий
  генератор initData) + `PUT /api/profile` с соответствующим
  `birthTimeMode`;
- access-покрытие по датам без манипуляций с ledger: full = сегодня
  (trial referral entry), preview = прошлая дата до начала доступа или
  истёкший доступ, locked = далёкая будущая дата (см. §8.2);
- фиксированные даты для hero/quiet reference;
- все созданные user IDs записываются в существующий cleanup ledger
  (`E2E_CREATED_USERS_FILE`), чтобы acceptance cleanup их учитывал.

## 5. Норматив (прочитать перед кодированием)

- `docs/work/2026-07-29_today-convergence-rewrite/06_DEV_RELEASE_EXECUTION_PLAN_TZ.md`
  P8-C (строки 340-371): cohort состав и запрет test-only API route.
- Существующее:
  - `e2e/fixtures.ts` — `deriveTelegramUserId`, generateInitData,
    CREATED_USERS_FILE ledger, паттерн cleanup.
  - `e2e/auth-helper.ts` — TelegramAuthContext flow.
  - `apps/api/app/api/profile.py` — PUT /api/profile wire (birthTimeMode
    exact/bucket/unknown — P1, в HEAD; проверь фактические поля
    ProfileWrite).
  - `apps/api/app/services/access_service.py:60-130` — access семантика
    (нет entries → preview для past/today, locked для future; trial
    referral entry → full в окне).
  - `scripts/generate-telegram-test-initdata.py` — генерация initData.

## 6. Exact write scope

- `e2e/acceptance-cohort.ts` (новый)
- `e2e/acceptance-cohort.spec.ts` (новый, self-check)

## 7. Frozen / Out of scope

- Backend/frontend production код не менять. Новых test-only API routes НЕ
  создавать. Никакого route interception. Никаких прямых SQL-записей
  (только публичный API; если какой-то access state недостижим через
  публичный API — эскалация §12, не обход).

## 8. Функциональные требования

### 8.1 Cohort builder

```typescript
export interface CohortUser {
  label: "exact" | "bucket" | "unknown";
  telegramUserId: number;
  userId: string;       // внутренний UUID из /api/auth/telegram
  initDataRaw: string;
}
export interface AcceptanceCohort {
  baseURL: string;
  users: CohortUser[];
  heroDate: string;   // YYYY-MM-DD — фиксированная дата с hero reference
  quietDate: string;  // фиксированная quiet reference
}
export async function seedAcceptanceCohort(baseURL: string): Promise<AcceptanceCohort>
```

- Для каждого label: свежий HMAC initData (уникальный telegram user id —
  переиспользуй `deriveTelegramUserId` или собственный salted generator в
  том же стиле), `POST /api/auth/telegram`, `PUT /api/profile` с
  birth-данными в соответствующем режиме; unknown — профиль без
  birthTime (mode unknown), bucket — `birthTimeBucket: "morning"`.
- User IDs дописываются в CREATED_USERS_FILE в ТОМ ЖЕ формате, что пишет
  e2e/fixtures.ts (проверь формат записи — JSONL).
- heroDate/quietDate: фиксированные константы (например, ближайшие
  stable даты); зафиксировать их выбор комментарием (reference snapshot
  будет создан live при первом запросе — seeder НЕ обязан предвычислять
  hero; но он обязан вернуть даты детерминированно).
- Идемпотентность повторного вызова в одном run: новые telegram IDs на
  каждый seed (run-salt), не падает при существующих данных.

### 8.2 Access states helper

```typescript
export function accessDatesFor(user: CohortUser, today: string): {
  fullDate: string; previewDate: string; lockedDate: string;
}
```

- `fullDate`: сегодня (новый пользователь получает trial referral window —
  проверь, что trial стартует сегодня; если не стартует автоматически —
  full недостижим без ledger → эскалация).
- `previewDate`: дата до начала trial window (вчера до старта доступа) —
  по access_service: для нового пользователя entries могут отсутствовать
  до первого гранта → preview на past/today; если trial стартует с
  сегодня, то ВЧЕРА — preview (нет covering entry).
- `lockedDate`: далёкое будущее (today + 400 дней) — locked
  (outside_access_window).
- Каждое предположение подтверждается self-check spec вызовом
  `GET /api/day/{date}` и чтением `access.state` (assert full/preview/
  locked соответственно).

### 8.3 Self-check spec

`e2e/acceptance-cohort.spec.ts`:

- skip без E2E_BASE_URL (как существующие real specs).
- seed → 3 пользователя существуют (GET /api/profile 200, birthTimeMode
  соответствует).
- access матрица: exact/fullDate → full; exact/previewDate → preview;
  exact/lockedDate → locked (через GET /api/day/{date} envelope
  `access.state`).
- cleanup ledger содержит 3 новых IDs (прочитать JSONL tail).

## 9. Must-preserve invariants

- Никакого route interception/test-only routes. Существующие e2e не
  ломаются (playwright config не менять; spec подхватывается тем же
  testDir — проверь, что он не попадает в CI default run без
  E2E_BASE_URL — skip обязателен).
- TypeScript чист (`npx tsc --noEmit`).

## 10. Verification

```bash
cd /tmp/solarsage-convergence-impl
npx tsc --noEmit 2>&1 | tail -3
# без E2E_BASE_URL — должен skip:
npx playwright test e2e/acceptance-cohort.spec.ts 2>&1 | tail -3
# против dev runtime (после deploy, может быть deferred в отчёте):
# E2E_BASE_URL=http://localhost:3002 npx playwright test e2e/acceptance-cohort.spec.ts
```

## 11. Expected evidence

- Файлы, вывод §10 (skip без base URL; если dev уже на новом коде —
  полный прогон). Формат ledger записи (пример строки, без PII).

## 12. Escalation rule

Access state недостижим через публичный API (напр. preview требует
истёкший доступ, которого нет у свежего trial) → СТОП, доложить с
фактическими ответами access.state — решит архитектор (вариант: грант
через существующий promo/referral flow, не SQL).

## 13. No-commit rule

Ничего не коммить и не пушить — коммит делает ревьюер.
