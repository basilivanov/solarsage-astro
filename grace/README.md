# GRACE Artifact Pack — Solar Sage

This folder is the GRACE-project binding plan for Solar Sage.

## State

- **legacy/ has been physically removed** (commit `a211e86`) — frontend migration from the old snapshot is complete.
- Legacy migration packets (W-2.x) are archived under `packets/archive/`.
- Active development continues on current slices: shell/navigation, Today, Calendar, Horary/Readings, Profile/Onboarding, backend API, contracts, logging spine.

## Source-of-truth order

1. `docs/GRACE_CANON.md` — methodology canon (portable, transferable)
2. `docs/10_GRACE_Project_Agent_Guide.md` — local adaptation for this project
3. Artifacts in this folder — the binding plan
4. `docs/00..13_*.md` — domain truth
5. Code under `app/`, `components/`, `apps/api/app/`, `packages/contracts/`, `scripts/`

If a code artifact contradicts a higher-priority artifact, the higher-priority one wins.

## Files

| File | GRACE clause | Purpose |
|---|---|---|
| `requirements.xml` | §13.A | Use cases, business rules, invariants, NFRs |
| `technology.xml` | §13.B | Stack, boundaries, version policy, local adaptations |
| `development-plan.xml` | §13.C | Current slices, phases, future waves |
| `knowledge-graph.xml` | §13.D | Modules, dependencies, contracts, versions |
| `verification-matrix.md` | §13.E | UC ⇄ module gates ⇄ scenarios |
| `canon.yaml` | §13.C | GRACE linter gate mode, exclusions, adoption path |
| `orchestrator/project.yml` | §10, §13 | Project-adapter for the portable orchestration runtime |
| `orchestrator/verification_profiles.yml` | §10, §13 | Named verifier profiles mapped to guardrails commands |
| `orchestrator/packet.schema.json` | §10.7 | Machine-readable packet metadata contract |
| `orchestrator/roles/*.md` | §10 | Role contracts/prompts for multi-agent execution |

## Current module families

| Slice | Modules | Paths |
|---|---|---|
| Shell/Navigation | AppShell, TabBar, bottom nav | `components/app-shell.tsx`, `components/today/tab-bar.tsx` |
| Today | TodayScreen, WeekStrip, DateHeader, DayReading | `components/today/*.tsx`, `lib/today.ts`, `packages/contracts/today.ts` |
| Calendar | CalendarScreen, MoodIcon | `components/calendar/*.tsx` |
| Horary/Readings | NatalSection, BlockRenderer, NatalTOC | `components/readings/natal/*`, `apps/api/app/readings/*` |
| Profile/Onboarding | ProfileScreen, OnboardingFlow | `components/profile/*`, `components/onboarding/*` |
| Backend API | Day, Calendar, Natal, Cities, Profile endpoints | `apps/api/app/**/*.py` |
| Contracts | TodayPayload, CalendarPayload, NatalPayload, etc. | `packages/contracts/` |
| Logging Spine | Envelope, correlation, redactor | `lib/grace/log.ts` |
| Guardrails | Lint, typecheck, test, GRACE canon | `scripts/grace_lint.py`, `scripts/grace_front_lint.py`, `scripts/guardrails.sh` |

## How a business feature becomes a GRACE packet

1. Business-level feature request enters through the GRACE runner or architect API.
2. Architect (LLM) generates a plan: waves, packets, write-scope, frozen-scope, gates.
3. Context-builder (Stage 0) collects a bounded bundle of relevant source files.
4. Coder agents run in isolated worktrees, modifying only the allowed files.
5. Each wave passes T0 (scope + cheap checks), T1 (targeted tests), T2 (full gates).
6. Evidence verifier confirms contract compliance.
7. Merged into main via GRACE pipeline.

## Guardrails commands

```bash
bash scripts/guardrails.sh docs          # docs manifest + frontmatter + orchestrator contracts
bash scripts/guardrails.sh orchestrator   # orchestrator adapter/profile/schema/roles
bash scripts/guardrails.sh frontend      # ESLint + typecheck + GRACE canon lint
bash scripts/guardrails.sh normal        # frontend + backend lint + typecheck
bash scripts/guardrails.sh strict        # full: lint + typecheck + test
```

## Current packet backlog

Active and planned packets live under `packets/`. W-1.x packets describe the current baseline state. W-3.x and above describe future work. W-2.x migration packets are archived under `packets/archive/` — the legacy frontend migration is complete.

## Anti-drift gates

```bash
python3 scripts/grace_front_lint.py <changed files>   # GRACE marker checks
python3 scripts/grace_lint.py <changed files>          # backend marker checks
python3 scripts/check_docs_manifest.py                  # docs/MANIFEST.md ⇄ docs/
    python3 scripts/check_orchestrator_contracts.py     # orchestrator adapter/profile/schema/roles
```

## Staged GRACE canon adoption

See `canon.yaml`. Current gate mode: `changed-files` — GRACE linters run only on files touched by coder agents.
First adoption targets: `components/today/`, `__tests__/components/`, `app/(grace)/today/`.
Vendor/shime paths (`components/ui/`, `alembic/`, `migrations/`) are excluded.
