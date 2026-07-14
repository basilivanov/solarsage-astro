# Commit и staging rollout — Today рассчитывает только запрошенную дату

Дата: 2026-07-15

Исполнитель: кодер в `tmux astro:0.0`.

Архитектор принял production diff после независимого review:

- `git diff --check` — PASS;
- compile/Ruff — PASS;
- GRACE для `today_service.py` — PASS;
- logging guardrails — PASS;
- targeted backend suite — `104 passed`;
- ранее кодером выполнен полный backend suite — `1458 passed, 4 skipped`;
- runtime/source proof подтверждает отсутствие background week-prefetch surface.

## 1. Цель этой фазы

Сделать один локальный commit и загрузить его в текущий test/staging runtime через перезапуск только `solarsage-api.service`.

После успешного smoke остановиться и отдать handoff архитектору.

## 2. Жёсткие ограничения

- Не делать `push`.
- Не делать merge/rebase.
- Не менять `.env` или `.env.production`.
- Не выполнять Alembic.
- Не очищать и не инвалидировать кэш: schema/content/cache versions не менялись.
- Не перезапускать frontend, sidecar, PostgreSQL или Telegram bot.
- Не добавлять frozen untracked paths:

  ```text
  .grace/
  artifacts/design/
  docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
  grace.db
  skills/
  ```

## 3. Pre-commit boundary

Проверить:

```bash
cd /opt/solarsage-astro
git branch --show-current
git rev-parse HEAD
git status --short
git diff --check
```

Ожидается:

- branch: `fix/today-single-day-no-week-prefetch`;
- parent HEAD: `65ee35983920dd7e7f93c083c64aeea9b3461bf0`;
- modified tracked files — ровно пять файлов ниже;
- untracked task docs — текущий каталог `docs/work/2026-07-15_today-single-day-no-week-prefetch/`;
- frozen untracked paths остаются untracked.

Разрешённый production/test scope:

```text
apps/api/app/services/today_service.py
apps/api/tests/test_day_endpoints.py
apps/api/tests/test_day_no_birthday_fallback.py
apps/api/tests/test_today_preview_transport.py
apps/api/tests/test_wave3_day_pipeline_reuse.py
```

## 4. Stage exact scope

Добавить только пять разрешённых code/test files и task docs:

```bash
git add -- \
  apps/api/app/services/today_service.py \
  apps/api/tests/test_day_endpoints.py \
  apps/api/tests/test_day_no_birthday_fallback.py \
  apps/api/tests/test_today_preview_transport.py \
  apps/api/tests/test_wave3_day_pipeline_reuse.py \
  docs/work/2026-07-15_today-single-day-no-week-prefetch/
```

До commit проверить staged boundary:

```bash
git diff --cached --check
git diff --cached --name-only
git status --short
```

В staged должны быть только перечисленные пять файлов и файлы текущего task-doc каталога. Если там есть любой frozen/unrelated path — остановиться, ничего не коммитить и сообщить архитектору.

## 5. Local commit

Сделать один commit:

```bash
git commit -m "fix(api): calculate only requested Today date"
```

После commit:

```bash
git show --stat --oneline --decorate HEAD
git status --short --branch
```

Frozen untracked paths могут оставаться в status. Tracked/staged изменений быть не должно.

Push запрещён.

## 6. Pre-restart runtime proof

Из корня репозитория выполнить:

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python - <<'PY'
import inspect

import app.services.today_service as module
from app.services.today_service import TodayService

source = inspect.getsource(module)
forbidden = (
    "_prefetch_week",
    "_TODAY_PREFETCH_TASKS",
    "asyncio.create_task",
    "asyncio.gather",
    "SessionLocal",
)

assert not hasattr(TodayService, "_prefetch_week")
assert not any(symbol in source for symbol in forbidden)
assert "week_strip" in source
assert "_get_yesterday_signals" in source
print("today_single_day_surface=ok")
PY
```

Ожидается `today_single_day_surface=ok`.

## 7. Зафиксировать соседние PID

Перед restart сохранить/вывести PID:

```bash
sudo systemctl show solarsage-api.service -p MainPID --value
sudo systemctl show solarsage-frontend.service -p MainPID --value
sudo systemctl show solarsage-sidecar.service -p MainPID --value
sudo systemctl show ductor-astro.service -p MainPID --value
```

Нужно доказать, что после операции изменился только API PID.

## 8. Restart только API

```bash
sudo systemctl restart solarsage-api.service
sudo systemctl is-active solarsage-api.service
sudo systemctl show solarsage-api.service \
  -p MainPID -p ActiveState -p SubState -p ExecMainStatus --no-pager
```

Ожидается:

- `active` / `running`;
- `ExecMainStatus=0`;
- новый ненулевой API PID.

Не использовать ручной `uvicorn` и не трогать порт 8001/18091.

## 9. Live smoke

Проверить canonical API listener и health:

```bash
sudo ss -ltnp '( sport = :8000 )'
curl -fsS http://127.0.0.1:8000/api/health
```

Требования:

- порт `127.0.0.1:8000` слушает новый PID `uvicorn` из systemd;
- health возвращает `status=ok`;
- `git_sha` равен short SHA нового commit.

Проверить последние логи, не печатая environment/secrets:

```bash
sudo journalctl -u solarsage-api.service --since "5 minutes ago" \
  --no-pager -n 120
```

В логах после нового старта не должно быть traceback, import error, bind error или restart loop.

Повторно вывести PID соседних сервисов и сравнить с пунктом 7:

```bash
sudo systemctl show solarsage-frontend.service -p MainPID --value
sudo systemctl show solarsage-sidecar.service -p MainPID --value
sudo systemctl show ductor-astro.service -p MainPID --value
```

Их PID не должны измениться.

Не вызывать специально cold `/api/day/{date}`: это создало бы платный payload только ради smoke. Отсутствие fan-out доказано source/runtime invariant и тестами; реальный пользовательский запрос после rollout уже будет рассчитывать только открытую дату.

## 10. Финальный handoff и остановка

Вернуть:

```text
SINGLE_DAY_NO_PREFETCH ROLLOUT: PASS | FAIL

Git:
- branch:
- parent SHA:
- commit SHA/message:
- push: not performed
- tracked worktree clean: yes/no

Runtime:
- API PID before/after:
- API active/listener:
- /api/health status/git_sha:
- journal errors: none | details
- frontend PID unchanged: yes/no
- sidecar PID unchanged: yes/no
- bot PID unchanged: yes/no

Data/config:
- env changed: no
- Alembic: not run
- cache invalidated: no

Result:
- requested Today date remains foreground calculation;
- adjacent ±3 day background payload calculations are disabled;
- 7-row week navigator and yesterday delta remain available.
```

После handoff остановиться. Никаких дополнительных изменений и push.
