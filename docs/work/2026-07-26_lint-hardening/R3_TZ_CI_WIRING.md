# R3_TZ: CI wiring — ruff блокирующий гейт, mypy non-blocking

## 1. Packet title
CI: вернуть ruff (блокирующий, apps/api + sidecar) и mypy (continue-on-error, apps/api services) в `.github/workflows/ci.yml`.

## 2. Phase / Wave
Lint hardening. Зависит от принятых R1 (ruff чист) и R2 (mypy конфиг).

## 3. Modules
- `.github/workflows/ci.yml`

## 4. Goal
1. **Job `backend-lint`** (блокирующий):
   - setup python 3.12;
   - `pip install ruff==0.15.14` (зафиксировать версию как в venv);
   - `ruff check apps/api/app`;
   - `ruff check apps/solarsage/solarsage`;
   - fail job при любой ошибке.
2. **Job `backend-mypy`** (`continue-on-error: true`):
   - setup python 3.12 + deps apps/api (как существующие backend jobs — переиспользовать их кэш/requirements паттерн);
   - `cd apps/api && mypy app/services/`;
   - `continue-on-error: true` (non-blocking, отчёт в лог).
3. Проверить, что новые jobs входят в существующую зависимость воркфлоу (если есть aggregated `ci-success`/required checks — добавить `backend-lint` в needs; `backend-mypy` НЕ добавлять).
4. Не трогать другие jobs.

## 5. Exact write scope
- `.github/workflows/ci.yml`

## 6. Frozen / Out of scope
- Другие workflows (deploy-production, e2e, visual), код приложения.

## 7. Must-preserve invariants
- YAML валиден; существующие jobs/needs не сломаны.
- `backend-mypy` не блокирует (continue-on-error), `backend-lint` блокирует.

## 8. Verification
- После пуша: `gh run list --branch main` — оба новых job присутствуют в CI run; `backend-lint` зелёный, `backend-mypy` зелёный или non-blocking.

## 9. Evidence
- diff ci.yml; ссылка на CI run с новыми jobs.

## 10. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
