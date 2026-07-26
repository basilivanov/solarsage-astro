# R1_TZ: ruff — конфиг и полная чистка apps/api + sidecar

## 1. Packet title
Ruff gate: конфиг, 0 ошибок `ruff check` в apps/api/app и apps/solarsage/solarsage. Реальные F821 (undefined name) разобрать как баги.

## 2. Phase / Wave
Lint hardening. Решение владельца: ruff — блокирующий гейт; mypy — отдельно (R2, non-blocking).

## 3. Modules
- `apps/api/pyproject.toml` (ruff config)
- `apps/api/app/**` (фиксы)
- `apps/solarsage/**` (pyproject + фиксы)

## 4. Goal
1. **Конфиг** `apps/api/pyproject.toml` `[tool.ruff]`: `target-version = "py312"`, `line-length = 120`, `select = ["F", "E4", "E7"]` (текущий дефолтный профиль репо по факту), `exclude` для миграций alembic НЕ делать (они тоже чистые/почти).
2. **Автофикс**: `ruff check app/ --fix` (без --unsafe-fixes).
3. **Ручные фиксы** всех оставшихся, приоритет:
   - **3× F821 `Undefined name User`** — сначала РАЗОБРАТЬ: это латентный баг (реальный NameError при выполнении пути) или мёртвая ветка. Если путь живой — починить как баг и сказать в отчёте где; если мёртвый — удалить/заглушить осмысленно.
   - E402 (import не наверху) — перенести/обосновать локальный импорт (если intentional — `# noqa: E402` с комментом почему).
   - E701 multiple statements — развернуть.
   - F811 redefinition — переименовать переменную.
   - E714/F541 — автофиксом.
   - F401 — удалить неиспользуемые импорты (проверить GRACE header DEPENDENCIES строки обновить если релевантно).
4. **Sidecar**: `apps/solarsage` — то же самое (20 ошибок: F841/F401/F541/E741); конфиг если есть pyproject, иначе ruff defaults.
5. НЕ менять поведение. Фиксы — только линт-уровень (кроме F821 если реальный баг).

## 5. Exact write scope
- `apps/api/pyproject.toml`
- `apps/api/app/**.py` (только lint-фиксы)
- `apps/solarsage/pyproject.toml` (если существует) + `apps/solarsage/solarsage/**.py`
- Тесты НЕ трогать, кроме если фикс F821 их затрагивает.

## 6. Frozen / Out of scope
- CI wiring (срез R3), mypy (срез R2), frontend, поведенческие изменения.

## 7. Must-preserve invariants
- `python -m pytest tests/ -q` в apps/api — полный прогон зелёный после фиксов.
- `python -m pytest tests/ -q` в apps/solarsage — зелёный.
- `python3 scripts/grace_lint.py apps/api/app` — PASS.
- Никаких `# noqa` без комментария-причины.

## 8. Verification commands
```bash
cd apps/api && source .venv/bin/activate
ruff check app/
python -m pytest tests/ -q
cd ../solarsage && source venv/bin/activate
ruff check solarsage/
python -m pytest tests/ -q
python3 scripts/grace_lint.py apps/api/app
```

## 9. Expected evidence
- `ruff check` — 0 ошибок в обоих пакетах (вывод).
- Разбор 3× F821: баг или мёртвая ветка, что сделано.
- Вывод тестов.

## 10. Escalation rule
Фикс требует поведенческого изменения → стоп, доложить.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
