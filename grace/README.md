# GRACE Artifact Pack

This folder contains the strict-GRACE artifact pack required by `docs/GRACE_CANON.md` §13 (Definition of Ready).

## Source-of-truth order

1. `docs/GRACE_CANON.md` — methodology canon (portable, transferable).
2. `docs/10_GRACE_Project_Agent_Guide.md` — local adaptation for this project.
3. Artifacts in this folder — the binding plan.
4. `docs/00..13_*.md` — domain truth.
5. Code under `app/`, `apps/api/`, `apps/solarsage/`, `packages/contracts/`, etc.

If a code artifact contradicts a higher-priority artifact, the higher-priority one wins.

## Files

| File | GRACE clause | Purpose |
|---|---|---|
| `requirements.xml` | §13.A | Use cases, business rules, invariants, NFRs |
| `technology.xml` | §13.B | Stack, boundaries, version policy, local adaptations |
| `development-plan.xml` | §13.C | Phases, waves, write-scope, freeze-scope |
| `knowledge-graph.xml` | §13.D | Modules, dependencies, contracts, versions |
| `verification-matrix.md` | §13.E | UC ⇄ module gates ⇄ scenarios |

## Naming conventions (semantic coordinates §6)

- Use cases: `UC-*` (e.g. `UC-DAY-VIEW`)
- Modules: `M-*` (e.g. `M-DAY-SERVICE`)
- Phases: `PHASE-N-NAME` (e.g. `PHASE-1-MOCKED-PIPELINE`)
- Waves: `W-N.M` (e.g. `W-1.1`)
- Contracts: `C-*` (e.g. `C-TODAY-PAYLOAD`)
- Versions: `contract_version`, `calculation_version`, `normalization_version`, `scoring_version`, `prompt_version`, `content_version`, `schema_version`

## Pilot slice

`UC-DAY-VIEW` over `M-DAY-SERVICE` returning fixture-backed `TodayPayload`. See `development-plan.xml` → `PHASE-1-MOCKED-PIPELINE` → `W-1.3`.

## Controller packets

Every wave has a packet under `packets/`. Each packet MUST carry YAML
front-matter (`id`, `status`, `wave`, `last_review`) — validated by
`scripts/check_frontmatter.py`. Status vocabulary: `active` (ready or
merged), `planned` (decided but not implemented), `superseded`, `stale`,
`archived`.

Current packets:

- `packets/W-1.1.md` — Project skeleton
- `packets/W-1.1B.md` — Contract boundary (source of truth)
- `packets/W-1.2.md` — Telegram auth + users + user_profiles
- `packets/W-1.3.md` — Pilot `GET /api/day/:date`
- `packets/W-1.4.md` — `GET /api/calendar?month=YYYY-MM`
- `packets/W-1.5.md` — Frontend leaves fixtures mode
- `packets/W-1.6.md` — Logging Spine (envelope · correlation · redactor)
- `packets/W-1.7.md` — Frontend → backend log shipping
- `packets/W-2.0.md` — Frontend GRACE conformance
- `packets/W-2.1.md` — Frontend types reconciliation
- `packets/W-2.2.md` — Shell + Today migration
- `packets/W-2.3.md` — Calendar + Day pages
- `packets/W-2.4.md` — Chat (screen + hook + reducer)
- `packets/W-2.5.md` — Readings (general + natal + widgets)
- `packets/W-2.6.md` — Profile + Paywall + Trial + Telegram-init
- `packets/W-2.7.md` — Onboarding flow (5 steps)
- `packets/W-2.8.md` — (see file)
- `packets/W-CHAT-INTAKE.md` — AI assistant chat intake (spec-only)
- `packets/W-CANON-LOG.md` — Canon change log

## Anti-drift gates

Run locally before pushing:

```bash
python scripts/check_frontmatter.py     # YAML front-matter on every doc/packet
python scripts/check_docs_manifest.py   # docs/MANIFEST.md mirrors docs/
python scripts/grace_lint.py            # marker contracts in apps/api/app
```
