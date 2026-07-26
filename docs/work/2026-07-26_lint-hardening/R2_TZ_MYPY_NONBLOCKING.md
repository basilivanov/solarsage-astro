# R2_TZ: mypy non-blocking — конфиг и базовая чистота services

## 1. Packet title
Mypy как non-blocking проверка: sane-конфиг, scope `app/services/`, убрать очевидные ошибки/настроить ложные.

## 2. Phase / Wave
Lint hardening. Решение владельца: mypy — НЕ жёсткий гейт, continue-on-error в CI; цель среза — рабочий конфиг без шума и по возможности чистые services.

## 3. Modules
- `apps/api/pyproject.toml` `[tool.mypy]`
- `apps/api/app/services/**` (фиксы по возможности)

## 4. Goal
1. **Конфиг** `[tool.mypy]`: `python_version = "3.12"`, `ignore_missing_imports = true`, `follow_imports = "silent"`, `warn_unused_ignores = false`, `plugins` — НЕ подключать pydantic plugin если его нет в venv (иначе ложные на CamelModel); overrides для `app.schemas.*` и `app.db.models` — `disable_error_code = ["call-arg"]` (CamelModel alias'ы mypy не понимает).
2. **Прогон** `mypy app/services/` с конфигом. Разобрать ошибки по классам:
   - реальные (арность распаковок, неправильные типы, Optional-разыменования) — починить;
   - ложные на pydantic CamelModel — гасить через override (не затыкать `# type: ignore` массово);
   - `type: ignore` только с комментом-причиной.
3. Цель: `mypy app/services/` — 0 ошибок или маленький задокументированный остаток (в отчёте по пунктам). НЕ вылизывать до идеала ценой поведенческих изменений.
4. Sidecar mypy — НЕ в этом срезе (только apps/api).

## 5. Exact write scope
- `apps/api/pyproject.toml` ([tool.mypy] + overrides)
- `apps/api/app/services/**.py` (тип-фиксы без смены поведения)

## 6. Frozen / Out of scope
- CI wiring (R3), ruff (R1 принят), frontend, sidecar, поведенческие изменения, добавление плагинов в venv.

## 7. Must-preserve invariants
- Полный `python -m pytest tests/ -q` — зелёный.
- grace_lint PASS; ruff check чист (не откатить R1).

## 8. Verification commands
```bash
cd apps/api && source .venv/bin/activate
mypy app/services/
python -m pytest tests/ -q
```

## 9. Expected evidence
- Вывод mypy (число ошибок до/после), список оставшихся и почему они ложные/отложенные.
- Вывод тестов.

## 10. Escalation rule
Фикс меняет поведение или требует новой зависимости → стоп, доложить.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
