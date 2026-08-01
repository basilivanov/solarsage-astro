# Packet: date-aware Today EventTime

## Phase / Wave

`W-TODAY-HUMAN-FIRST / P1-WIRE-TIME`

## Modules

- `M-TODAY-CONVERGENCE-SCHEMAS`
- `M-TODAY-CONVERGENCE-PROJECTION`
- `M-TODAY-NARRATIVE-SERVICE`

## Goal

Актуальная exact-проекция Today отдаёт абсолютные timezone-aware моменты пика и границ окна, чтобы UI однозначно показывал календарные даты для переходящих через полночь и сутки окон.

## Exact Write Scope

- `apps/api/app/schemas/today_convergence.py`
- `apps/api/app/services/today_convergence_projection.py`
- `apps/api/app/services/today_narrative_service.py`
- `apps/api/tests/test_today_convergence_contract.py`
- `apps/api/tests/test_today_convergence_projection.py`
- `apps/api/tests/test_today_narrative_service.py`
- generated artifacts, изменяемые только `pnpm contracts:generate`:
  - `packages/contracts/openapi.json`
  - `packages/contracts/_generated.ts`
  - `packages/contracts/_generated.zod.ts`

## Frozen / Out Of Scope

- Не менять React-компоненты, CSS, e2e screenshots и visual baselines.
- Не менять выбор событий, астрологический расчёт, snapshot storage или LLM prompt semantics.
- Не удалять текущие `peak/start/end` clock-поля.
- Не трогать unrelated worktree files и untracked `.codex/`, `.tmp-*`.

## Must Preserve Invariants

- Изменение контракта аддитивное: optional camelCase wire-поля `peakAt`, `startAt`, `endAt` с timezone-aware datetime; старый payload без них валиден.
- Для `mode=exact` текущая projection заполняет `peakAt`; `startAt/endAt` соответствуют доступным границам. Clock-поля соответствуют тем же local instants.
- Для midpoint fallback `peakAt` равен midpoint абсолютного окна.
- Для `partofday` и `date` абсолютные поля отсутствуют/null; validator запрещает несовместимые сочетания.
- Если все три exact instant заданы, validator отклоняет порядок `startAt > peakAt` или `peakAt > endAt`.
- Narrative-проекция получает те же поля/семантику, чтобы prompt input не расходился с публичной projection.
- GRACE contracts/maps остаются точными; новое поведение покрыто тестами.

## Verification Command

```bash
cd /opt/solarsage-astro && pnpm contracts:generate && cd apps/api && source .venv/bin/activate && python -m pytest tests/test_today_convergence_contract.py tests/test_today_convergence_projection.py tests/test_today_narrative_service.py -q
```

## Expected Evidence

- Список изменённых файлов.
- Короткий пример JSON EventTime для окна через две даты.
- Полный итог targeted-команды и число passed tests.
- Подтверждение, что generated artifacts обновлены только генератором.

## Escalation Rule

Если нужны frontend-файлы, изменение snapshot schema/storage, иной wire shape или соседний scope — остановиться и доложить архитектору; не расширять packet самостоятельно.

## No Commit Rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
