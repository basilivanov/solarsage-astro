# Patch to grace/development-plan.xml

This is a controller-authored amendment to be applied as a **separate prior PR**
before W-1.1B's worker PR, per drift-protection rule
"If implementation requires changing requirements.xml or technology.xml, the
change is a separate prior PR." The plan is a sibling of those files; same
rule applies.

## What changes

Insert a new wave **W-1.1B "Contract boundary"** between the existing
`W-1.1` and `W-1.2`. No existing wave id is renamed; renumbering would cascade
into PR titles and matrix references.

## Rationale

`W-1.3` already requires "Response validates against packages/contracts/today.ts
via JSON Schema test", but the plan never declares which side authors that
JSON Schema. Discovering this during W-1.2 (auth/profile schemas) would force
a retroactive contract decision and rewrite of the just-merged Pydantic
models. Pulling the decision earlier costs one wave; deferring it costs a
revert of W-1.2.

## XML to insert (place between `</wave>` of W-1.1 and `<wave id="W-1.2">`)

```xml
<wave id="W-1.1B">
  <title>Contract boundary: pick source of truth between Pydantic, zod, and packages/contracts</title>
  <modules>M-CONTRACTS</modules>
  <write-scope>packages/contracts/* · scripts/contracts/* · package.json (scripts only) · .github/workflows/contracts.yml · apps/api/app/contracts/* OR apps/api/app/schemas/_base.py (per chosen option) · lib/contracts/* (only if Option B reduces it to forms)</write-scope>
  <freeze-scope>all feature routes · all UI components · apps/solarsage/* · requirements.xml · technology.xml · knowledge-graph.xml</freeze-scope>
  <entry-criteria>W-1.1 closed · controller has recorded a Decision (A/B/C) in grace/packets/W-1.1B.md.</entry-criteria>
  <exit-criteria>
    <criterion>Exactly one source of truth is documented in packages/contracts/README.md.</criterion>
    <criterion>`pnpm contracts:check` (or equivalent) regenerates artifacts deterministically and CI fails on drift.</criterion>
    <criterion>Frontend smoke on NEXT_PUBLIC_USE_FIXTURES=true renders /day/today byte-identical to pre-wave.</criterion>
    <criterion>No existing field name or meta.contract_version value changed.</criterion>
  </exit-criteria>
  <deliverables>generator script · committed generated artifacts · CI step · README stating chosen option · parity test scaffold</deliverables>
</wave>
```

## Update to phase-deps section

No change. W-1.1B remains internal to PHASE-1-MOCKED-PIPELINE.

## Update to verification-matrix.md

Under "Cross-cutting verifications → Contract drift", append:

> Authoring direction is set by W-1.1B. The "regenerates and diffs" step
> in `tests/contract_parity_test.py` runs the generator declared by the
> chosen option (A/B/C); the test fails if regeneration produces a non-empty
> diff against committed artifacts.
