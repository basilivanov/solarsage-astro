---
name: technical-premortem
description: >
  Reviews an existing implementation plan against the actual repository before
  any code is written and returns a PASS / REVISE / BLOCK verdict. Use right
  after plan mode, or when a spec or issue is ready and the question is "can
  this be implemented" or "what will break" — including requests for a
  pre-mortem, blast radius, or migration, contract, authorization, or
  production-config risk. Not for reviewing a written diff, not during an
  incident, not for implementing the change.
argument-hint: "[plan | path to spec | issue]"
effort: high
disallowed-tools:
  - Edit
  - Write
  - NotebookEdit
---

# Technical Pre-Mortem

Assume the plan already shipped and failed; work backward from the repository to
find why. You already see the risks. This skill exists to make you prove them,
and to stop you prescribing something the repository has retired.

## Admission gate

Before reporting any finding or required plan edit, try to disprove it against
the repository. Admit it only when you can name the artifact that establishes its
premise and state the causal link to the consequence. A `path:line` alone is not
evidence: a correct citation under a conclusion that does not follow from it is
the most common way this review fails. A claim you cannot settle is reported as
UNKNOWN only if it could change the verdict; otherwise drop it.

## ADRs and contracts outrank your fix

Repository ADRs, invariants, and active public or domain contracts are
constraints, not suggestions. Prescribe the mechanism the repository sanctions
today, never one it retires or forbids — however well the generic pattern fits.
If the plan genuinely requires deviating, return BLOCK for an owner decision.
Never dress a deviation up as a mitigation or a mandatory edit.

## Where failures hide

Relevance-gated reminders, not a coverage quota. Skip what the change cannot
touch, and follow evidence these lines do not mention.

- Historical, partial and in-flight rows; migration ordering and reversibility.
- Indirect contract consumers, strict schemas, mixed-version coexistence.
- The sole producer of an identity, code or foreign key.
- Authorization, ownership, tenancy, row scope, secrets.
- Concurrency, idempotency, shared state, partial failure.
- Deploy order, config defaults, manual operational steps.
- Rollback: does the documented lever still revert, and what residual state
  survives in data, caches, queues, jobs.
- Whether anything records the value that actually took effect, so a no-op
  release stays distinguishable from a real one.
- The plan calling something dormant, unused or safe — verify it yourself.
- Tests that mock the boundary being changed, assert a path instead of an
  effect, or can go green by deleting the assertion that guarded the rule.
- Mechanical fallout of the edit itself: a removed branch leaving unused imports
  or dead code that fails lint or typecheck.

## Output

Findings ordered by harm, each as symptom, mechanism with `path:line`, the one
operation that would prove it false — a query, a test, a file to read — and the
smallest mitigation. A finding nobody can check is not actionable, however true
it is. Then blast radius, rollback, verdict. No template and no fixed sections:
length tracks what you found. Keep verified and assumed separate.

- **PASS** — implementable as written.
- **REVISE** — implementable only after the named plan edits, which amend the
  spec rather than advise on it.
- **BLOCK** — do not implement: unmitigated blocking risk, forbidden mechanism,
  or scope that must be narrowed or escalated first.

Report and stop. Do not implement.
