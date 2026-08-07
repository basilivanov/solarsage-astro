# S13 TZ — hotfix: quiet-day selection падает на unmapped presentation sphere

## packet title
S13-quiet-selection-unmapped-hotfix

## Phase / Wave
W-SPHERES-FACETS-REWORK

## Modules
- M-TODAY-CONVERGENCE-SELECTION

## Контекст (диагностика ревьюера, воспроизведено на dev)

На dev реальный пользователь (Moscow 1990-01-15 14:30 exact) получает
`state=unavailable` на `/api/day/{date}` для всех дат. Прямой вызов
`calculate_today_convergence(profile, date.today())` возвращает:

```
TodayConvergenceCalculationUnavailable
failure_stage  = pipeline
failure_reason = today_convergence_runtime:pipeline:selection
pipeline       = selection / today_convergence_selection:unmapped_presentation_sphere
```

Корень: в `_quiet_selection` (`apps/api/app/services/today_convergence_selection.py`)
кандидаты фильтруются только по polarity (`_public_polarity(...) is None` →
`steady_exclusions`), но НЕ по разрешимости product sphere. Если топ-ранкед
юнит (rare anchor для main или impulse-кандидат) — pool-level событие без
product sphere (пример: `act:t2n__URANUS__SQUARE__URANUS` — нет house/theme
маппинга), то `_selected_event` → `_presentation_sphere_facet` →
`resolve_product_sphere(...) is None` → `_fail("unmapped_presentation_sphere")`
→ весь день unavailable.

По канону реворка pool-level события без product sphere **не публикуются** —
это осознанное поведение. Selection обязан просто не выбирать такие юниты,
а не падать.

## goal

Quiet-day selection пропускает юниты с неразрешимой product sphere (считает
их отдельным счётчиком), день собирается из оставшихся кандидатов; если
кандидатов не осталось — честный quiet day без main/impulses
(`main_event=None, impulses=()`), а не unavailable.

## exact write scope

- `apps/api/app/services/today_convergence_selection.py`
- `apps/api/tests/test_today_convergence_selection.py`

## frozen / out-of-scope

- canon YAML (`grace/canon/*.yml`), resolver `resolve_product_sphere`, grouping,
  projection, runtime, API-слой — НЕ трогать.
- Convergence-day путь (`_selected_convergences`) — НЕ трогать (группы
  sphere-backed по построению, там бага нет).
- Frontend, replay-аналитика, fixtures — НЕ трогать.

## Требования к реализации

1. В `_quiet_selection` в ОБОИХ циклах (rare-anchor кандидаты для main и
   impulse-кандидаты) до ранжирования проверять
   `resolve_product_sphere(canon, house=unit.house, technical_spheres=unit.technical_spheres, theme_keys=unit.theme_keys, source_key=unit.source_key, target_key=unit.target_key)`;
   `None` → пропустить юнит и инкрементировать новый счётчик
   `unmapped_exclusions` (аналогично `steady_exclusions`).
2. Пробросить счётчик наружу: `_quiet_selection` возвращает его дополнительным
   элементом tuple; `select_canonical_presentation` складывает в НОВОЕ поле
   `unmapped_sphere_exclusion_count: int` в `CanonicalSelectionAudit` (для
   convergence-пути значение 0). Поле аддитивное — audit сериализуется в
   snapshot-документ как диагностика, обратно не читается.
3. `_selected_event` и `_presentation_sphere_facet` оставить fail-closed как
   есть — после фильтра это unreachable-инвариант (defense in depth).
4. GRACE-разметку файла сохранить/актуализировать (FUNCTION_CONTRACT для
   изменённых функций).

## must-preserve invariants

- Поведение convergence-day пути байт-в-байт.
- Существующие тесты selection/pipeline/snapshot зелёные (кроме случаев, где
  audit-форму сознательно расширили — тогда обновить assertion в рамках scope).
- Физика не меняется: ledger/units/groups/tone не затрагиваются; меняется
  только выбор presentation-юнитов в quiet path.

## verification commands

```bash
cd apps/api && .venv/bin/python -m pytest tests/test_today_convergence_selection.py tests/test_today_convergence_pipeline.py tests/test_today_convergence_snapshot.py -q
```

Плюс ручной repro (приложить вывод до/после):

```bash
cd apps/api && set -a && source /opt/solarsage-astro/.env && set +a && .venv/bin/python - <<'EOF'
import asyncio, datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import SessionLocal
from app.db.models import User
from app.services.today_convergence_runtime import calculate_today_convergence

async def main():
    async with SessionLocal() as db:
        user = (await db.execute(select(User).options(selectinload(User.profile))
            .where(User.id == "3736262c-f960-438e-8e5f-1e9a91ac45ce"))).scalar_one()
        res = await calculate_today_convergence(user.profile, datetime.date.today())
        print(type(res).__name__, getattr(res, "failure_reason", None))

asyncio.run(main())
EOF
```

Ожидание после фикса: `TodayConvergenceCalculationBuilt` (допустимо quiet day
с малым числом событий — главное, не Unavailable по selection).

## expected evidence

- Дифф двух файлов.
- Новые регрессионные тесты: (а) quiet day, топ-кандидат unmapped → выбран
  следующий разрешимый, счётчик=1; (б) все кандидаты unmapped →
  `main_event=None, impulses=()`, state=quiet_day, без исключения; (в)
  convergence-day путь не тронут (существующие тесты зелёные).
- Вывод pytest и repro-скрипта.

## escalation rule

Понадобился файл вне exact write scope (например, баг окажется в resolver или
grouping) — СТОП, доложить ревьюеру с диагностикой, ждать новый packet.

## no-commit rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
