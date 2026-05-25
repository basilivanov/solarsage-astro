# Roles — Strict GRACE execution

Source: `docs/GRACE_CANON.md` §10 (Multi-agent execution model).

This file is the **single source of truth** for who does what during execution.
It is short on purpose. If a situation is not covered here, fall back to the canon.

---

## Roles

### Controller (you, the human owner)

- Owns the artifact pack: `requirements.xml`, `technology.xml`, `development-plan.xml`,
  `knowledge-graph.xml`, `verification-matrix.md`.
- Owns the boundary contract decisions (see W-1.1B).
- Issues **controller packets** (one per wave) using the template in canon §10.7.
- Resolves drift escalations from worker (§10.3).
- Decides scope freezes; never expands a wave silently.
- Never writes feature code in the same step as authoring a packet.

### Worker (implementing agent or contributor)

- Executes the active controller packet **literally**.
- May only write inside `Allowed Write Scope`.
- Must touch nothing in `Frozen / Out Of Scope`.
- Must respect `Must Preserve` invariants.
- On any ambiguity, missing fact, or temptation to expand scope: **STOP and escalate**
  to controller with a one-paragraph question. Do not guess.
- Returns evidence in the format requested by the packet (logs, diff, test output).

### Reviewer (controller or designated second pair of eyes)

- Verifies that the worker's diff stays inside `Allowed Write Scope`.
- Verifies every `Verification` step in the packet was actually run and passed.
- Verifies every `Expected Evidence` item is attached.
- Cross-checks against the wave's `exit-criteria` in `development-plan.xml`
  and the touched UC rows in `verification-matrix.md`.
- Either closes the wave gate or rejects with a specific reason. Never "looks good".

---

## Current assignment

| Role       | Owner               |
|------------|---------------------|
| Controller | <fill in: human>    |
| Worker     | <fill in: agent or human> |
| Reviewer   | <fill in: human, can be same as controller for solo dev> |

Solo-developer mode is allowed: one human plays all three roles, but the
**phase separation must still hold** — author the packet, then close the editor,
then re-open as worker. Mixing authoring and execution in one session is the
single most common cause of drift in solo GRACE projects.

---

## Packet lifecycle

1. Controller drafts packet under `grace/packets/<wave-id>.md`.
2. Controller marks it `status: ready`.
3. Worker reads only the packet (not the rest of the artifact pack) and executes.
4. Worker attaches evidence to the same file under `## Evidence`.
5. Reviewer either flips `status: closed` and links the merge commit, or sets
   `status: rejected` with a reason and the worker iterates.
6. Controller drafts the next packet only after the previous one is `closed`.

No packet may be open at the same time as another packet for the same module.
Two packets for **different** modules with no shared `Allowed Write Scope` may
run in parallel — see canon §10.4.
