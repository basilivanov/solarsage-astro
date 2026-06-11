# GRACE Artifact Pack — Solar Sage

This folder is the current GRACE project binding for Solar Sage.

The files here do **not** define new runtime folders. They define how the existing codebase is understood by GRACE: modules, slices, ownership, contracts, verification gates, and staged adoption waves.

## State

- **`legacy/` has been physically removed** in Solar Sage commit `a211e86`; old frontend migration is complete.
- Old W-2.x legacy migration packets live under `grace/packets/archive/` and are historical only.
- Current work is slice-based: future business features must map to one or more slices before a coder edits files.
- Latest slice coverage audit: `docs/work/REPORT_SOLARSAGE_GRACE_SLICE_COVERAGE_AUDIT.md` / `docs/work/solarsage_grace_slice_coverage.json` at Solar Sage `9dedaf9`.

## Source-of-truth order

1. `docs/GRACE_CANON.md` — portable GRACE methodology canon.
2. `grace/README.md` — this current project map and navigation index.
3. `grace/knowledge-graph.xml` — module/slice/path/dependency ownership map.
4. `grace/verification-matrix.md` — use case and slice gates.
5. `grace/development-plan.xml` — current roadmap and adoption waves.
6. `grace/technology.xml` — stack, boundaries, tools, contracts, banned choices.
7. `docs/10_GRACE_Project_Agent_Guide.md` — local agent operating guide.
8. Code under `app/`, `components/`, `lib/`, `apps/api/app/`, `apps/solarsage/`, `packages/contracts/`, `scripts/`.

When docs and code disagree, use this order. If the disagreement affects execution, create a docs-sync packet before coding.

## Living files

| File | Purpose |
|---|---|
| `requirements.xml` | Business rules, product invariants, NFRs. |
| `technology.xml` | Stack, boundaries, contracts, tooling, banned choices. |
| `development-plan.xml` | Current roadmap and GRACE adoption waves. |
| `knowledge-graph.xml` | Modules, slices, paths, dependencies, logging ownership. |
| `verification-matrix.md` | Use cases and slice gates. |
| `canon.yaml` | GRACE linter mode, exclusions, adoption order. |
| `orchestrator/project.yml` | Project adapter for the GRACE runtime. |
| `orchestrator/verification_profiles.yml` | Named verification profiles. |
| `orchestrator/packet.schema.json` | Machine-readable packet metadata contract. |
| `orchestrator/roles/*.md` | Role contracts/prompts for multi-agent execution. |

## Current slice registry

| Slice | Ownership | Primary paths |
|---|---|---|
| `SLICE-SHELL-NAVIGATION` | App shell, bottom navigation, tab state, active route affordances. | `components/app-shell.tsx`, `components/today/tab-bar.tsx` |
| `SLICE-TODAY-CALENDAR` | Today screen, week strip, calendar grid, day/date payload rendering. | `components/today/`, `components/calendar/`, `app/(grace)/today/`, `lib/today.ts`, `lib/calendar.ts` |
| `SLICE-HORARY-READINGS` | Readings surfaces, natal/horary UI, question/answer rendering. | `components/readings/`, `app/(grace)/readings/` |
| `SLICE-PROFILE-ONBOARDING` | Profile, onboarding, city/timezone/location capture. | `components/profile/`, `components/onboarding/`, `app/(grace)/profile/`, `app/(grace)/onboarding/` |
| `SLICE-FRONTEND-API-FACADES` | Frontend HTTP clients and thin API facades. | `lib/api/`, `lib/access.ts`, `lib/profile.ts`, `lib/chat.ts`, `lib/cities.ts` |
| `SLICE-CONTRACTS` | Pydantic/OpenAPI/TypeScript contract bridge. | `apps/api/app/schemas/`, `scripts/contracts/`, `packages/contracts/` |
| `SLICE-BACKEND-API-ROUTERS` | FastAPI routers and endpoint-level schemas. | `apps/api/app/api/`, `apps/api/app/schemas/`, fallback `apps/api/app/` |
| `SLICE-BACKEND-SERVICES` | Backend business logic and service orchestration. | `apps/api/app/services/`, `apps/api/app/core/` |
| `SLICE-DB-MODELS-MIGRATIONS` | ORM models, DB session, migrations. | `apps/api/app/db/`, Alembic paths when explicitly in scope |
| `SLICE-SIDECAR-CALCULATION` | SolarSage sidecar and calculation parity. | `apps/solarsage/`, `apps/api/calculations/` |
| `SLICE-SCORING-SEMANTIC-LLM` | Scoring, semantic context, LLM narration policy. | `apps/api/scoring/`, `apps/api/normalization/`, `apps/api/semantic/`, related services |
| `SLICE-LOGGING-SPINE` | Frontend/backend logging primitives, correlation, redaction, evidence logging policy. | `lib/grace/`, backend logging helpers when present |
| `SLICE-TESTS` | Backend/frontend/contract/e2e tests. | `__tests__/`, `apps/api/tests/`, `apps/solarsage/tests/` |
| `SLICE-GUARDRAILS-TOOLING` | GRACE lint, coverage audit, docs checks, guardrails scripts. | `scripts/`, `.github/workflows/` when explicitly in scope |
| `SLICE-ORCHESTRATOR-ADAPTER` | Project-local GRACE adapter and role/profile/schema docs. | `grace/orchestrator/`, `grace/*.xml`, `grace/*.md`, `grace/canon.yaml` |

## Current coverage reality

The latest audit reports 496 audited files:

- full GRACE markers: 41 files / 8.3%;
- partial markers: 51 files / 10.3%;
- no markers: 404 files / 81.5%;
- canonical logging detected: 1 file / 0.2%;
- unmapped: 28 files / 5.6%.

Interpretation:

- The project has a slice model, but most runtime files are not yet fully GRACE-canon marked.
- Do **not** assume “logs are everywhere” until `SLICE-LOGGING-SPINE` revalidates actual logging patterns and updates the audit detector if needed.
- Adoption must be slice-by-slice, not a repo-wide mass marker rewrite.

## How a business feature becomes a GRACE packet

1. Business request enters GRACE.
2. Architect maps the request to one or more slices from the registry above.
3. Architect chooses allowed write scope and frozen scope from `knowledge-graph.xml`.
4. Context-builder collects only relevant modules/contracts/tests.
5. Coder edits only allowed files in an isolated worktree.
6. Gates run according to `verification-matrix.md` and `orchestrator/verification_profiles.yml`.
7. Evidence verifier/reviewer checks artifacts.
8. Successful packet merges; docs update only when module boundaries, contracts, or gates change.

## Guardrails commands

```bash
bash scripts/guardrails.sh docs
bash scripts/guardrails.sh orchestrator
bash scripts/guardrails.sh frontend
bash scripts/guardrails.sh normal
bash scripts/guardrails.sh strict
python3 scripts/grace/coverage_audit.py --check
```

## Adoption waves

Current recommended adoption order:

1. `W-GRACE-SLICE-P0-TODAY-CALENDAR`
2. `W-GRACE-SLICE-P0-BACKEND-API-SERVICES`
3. `W-GRACE-SLICE-P0-CONTRACTS`
4. `W-GRACE-SLICE-P1-LOGGING-SPINE`
5. `W-GRACE-SLICE-P1-HORARY-READINGS`
6. `W-GRACE-SLICE-P1-PROFILE-ONBOARDING`
7. `W-GRACE-SLICE-P2-TESTS-TOOLING`

Do not mass-apply headers/contracts/blocks/logs across all slices in one packet.

## Anti-drift gates

```bash
python3 scripts/grace_front_lint.py <changed files>
python3 scripts/grace_lint.py <changed files>
python3 scripts/check_docs_manifest.py
python3 scripts/check_orchestrator_contracts.py
python3 scripts/grace/coverage_audit.py --check
```

## Archive policy

- `grace/packets/archive/` is historical evidence only.
- New work must not copy old W-2.x migration language.
- If a future agent needs history, it may cite archive files, but it must plan against the current slice registry above.
