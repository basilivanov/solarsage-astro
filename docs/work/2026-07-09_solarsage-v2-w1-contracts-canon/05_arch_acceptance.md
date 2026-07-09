# Architect Acceptance: Wave W1 Contracts / Canon / Versioning

Status: ACCEPTED

Accepted commit range:

- implementation: `56d6de38b61c0db9b6c3c787195ff5de6b8b8521`
- report: `f7a86f999936d069723d34201ccace536b5081c0`

## Review Summary

W1 Rework 01 resolves the blocking findings from `02_arch_review.md`.

Accepted architecture:

- strict canon validation is wired into the API boot/import path via `apps/api/app/main.py`;
- missing/invalid canon files raise `CanonValidationError` and prevent `app.main` import;
- canonical activation contracts are present in generated OpenAPI/TypeScript;
- legacy Today convergence evidence is renamed to `ConvergenceEvidence`, while canonical `ActivationEvidence` remains attached to `ActivationLayer` and `ScoringV2Result`;
- API and sidecar `ActivationLayer` validate that every `by_planet`, `by_house`, `by_lot`, and `by_angle` id exists in `activations[]`;
- runtime `TodayMeta` includes `canon_versions=get_canon_versions()` for full and preview payloads;
- runtime `/day` does not claim `ss-scoring-2.0` before W4.

## Architect Verification

Fresh commands run by architect:

```bash
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
rg -n 'ss-scoring-2.0' artifacts/audit/2026-07-08/11_final_today_payload.json apps/api/app/services/today_service.py || true
rg -n 'ActivationLayer|ScoringV2Result|SphereScoreV2|SphereContribution|ConvergenceEvidence' packages/contracts/openapi.json packages/contracts/_generated.ts
pnpm contracts:generate
git diff --exit-code -- packages/contracts/openapi.json packages/contracts/_generated.ts
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
cd apps/solarsage && venv/bin/python -m pytest tests/ -q
npx vitest run
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
git diff --exit-code -- artifacts/audit/2026-07-08
```

Results:

- whitespace checks: clean;
- generated contracts: regenerated and clean;
- API tests: `670 passed, 5 skipped`;
- sidecar tests: `26 passed`;
- frontend unit tests: `85 files / 902 tests passed`;
- audit-day: deterministic, no artifact diff;
- `ss-scoring-2.0`: no runtime matches in checked payload/path;
- repository tree: only known unrelated untracked files remain (`.grace/`, `grace.db`, `skills/`, old superpowers plan).

Additional startup failure proof:

```bash
cd apps/api && source .venv/bin/activate && python - <<'PY'
import tempfile
from pathlib import Path
import app.services.canon_service as canon_service
from app.services.canon_service import CanonValidationError

with tempfile.TemporaryDirectory() as tmp:
    canon_service.CANON_DIR = Path(tmp)
    try:
        import app.main  # noqa: F401
    except CanonValidationError as exc:
        print(type(exc).__name__)
        print(str(exc).split(':')[0])
    else:
        raise SystemExit('app.main import unexpectedly succeeded with missing canon')
PY
```

Result:

```text
CanonValidationError
Missing canon file
```

## Notes For Next Wave

- `load_canon_bundle()` is still available as a best-effort helper. It is not used for API startup validation.
- W2 may now build on the accepted contracts/canon base; do not enable `ss-scoring-2.0` runtime metadata until the dedicated scoring wave.
