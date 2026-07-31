# P2-C3 TZ — canonical pipeline orchestration and fixed-probe parity

Date: 2026-07-31
Status: implementation packet
Depends on: packets 18–24, commit `c35cd182`.

## 1. Goal

Add the one pure production entrypoint that composes the already accepted
W2 stages:

```text
RawPhysicalFact[]
  -> canonical ledger
  -> direct groups
  -> frozen tone policy
  -> deterministic presentation selection
```

The packet does not adapt legacy `TodayService`, call the sidecar, create a
wire payload, persist a snapshot, or change W1. It proves the production
composition against a committed fixed probe and closes mutation fixtures 1–6
as one end-to-end deterministic gate.

## 2. Exact write scope

Only these paths may be created/changed:

1. new `apps/api/app/services/today_convergence_pipeline.py`;
2. new `apps/api/tests/test_today_convergence_pipeline.py`;
3. new
   `apps/api/tests/fixtures/today_convergence_pipeline_probe.v1.json`;
4. `grace/verification-matrix.md`;
5. `grace/knowledge-graph.xml`;
6. this reviewer-owned packet — do not edit it.

If another file is needed, stop and report. Coder does not commit or push.

## 3. Public records and entrypoint

Add frozen records without compatibility aliases:

- `CanonicalPipelineBuilt`
  - `formula_version`;
  - `state: convergence_today|quiet_day`;
  - final `CanonicalLedger`;
  - final `CanonicalGroupingResult`;
  - final `CanonicalToneResult`;
  - final `CanonicalSelectionResult`.
- `CanonicalPipelineUnavailable`
  - `formula_version: str | None`;
  - `state="unavailable"`;
  - `failure_stage: canon|ledger|grouping|tone|selection|tone_rebind`;
  - stable `failure_reason` from the typed boundary error;
  - the successfully completed immutable `ledger/grouping/tone` records, or
    `None` when that stage was not reached.
- `CanonicalPipelineResult` — the explicit union of the two records.

Entrypoint:

```python
run_canonical_today_pipeline(
    raw_facts: Sequence[RawPhysicalFact],
    target_date: date,
    timezone_name: str,
    delta_trigger_semantic_keys: Sequence[str] | None = None,
    canon: TodayConvergenceCanon | None = None,
) -> CanonicalPipelineResult
```

The result owns no wire/Pydantic aliases and emits no logs. Empty but valid
input is a built `quiet_day`, not a technical failure; later period-context
projection makes that screen non-empty.

## 4. Normative orchestration

1. Resolve the strict frozen canon. A typed canon failure returns unavailable
   at `failure_stage=canon`.
2. Build the ledger with exact semantic DayDelta keys. A top-level ledger API
   error returns unavailable at `ledger`; row-level invalid facts remain the
   existing ledger exclusions and do not make the whole day unavailable.
3. Build direct groups. Typed grouping invariant failures return unavailable
   at `grouping`.
4. Compute provisional tone with `selected_unit_ids=()`. Selected IDs are
   audit-only by the accepted C1 contract; day/group tone cannot depend on
   them.
5. Select presentation from ledger/grouping/provisional tone. Typed selector
   failures (including `hero_without_public_polarity`) return unavailable at
   `selection`.
6. Recompute tone with exactly `selection.selected_unit_ids` so the persisted
   tone audit describes the public evidence set.
7. Assert provisional and final `tone_policy_version`, `day_tone`,
   `group_tones`, tone scores, trigger keys and context facts are identical;
   only selected-audit fields may differ. Any dependency is unavailable with
   exact reason token `today_convergence_pipeline:tone_selection_dependency`
   at `tone_rebind`.
8. Return built result with `state == selection.state`, final tone, and the
   exact frozen canon `formula_version`.

Catch only the known typed errors from canon/ledger/groups/tone/selection at
their own stage. Do not catch arbitrary `Exception`, do not silently turn
programming defects into successful quiet days, and do not create fallback
copy.

## 5. Fixed reference probe

Commit one small, human-readable JSON fixture. It must contain normalized raw
facts plus a literal expected projection for at least:

1. a public hero with an extra non-evidence group member and background noise;
2. a quiet mixed-tone day from independent supportive+tense fresh units;
3. a single rare main event plus ordinary impulses with the three-sphere cap;
4. exact/bucket/unknown robust inputs and one time-sensitive non-exact
   exclusion;
5. an edge-orb/noise exclusion and producer duplicate.

The expected projection includes exact canonical event/group IDs,
`formula_version`, state, day tone, selected evidence IDs, selected spheres,
main/impulse IDs, and relevant ledger/group/tone/selection counters. Test code
may parse ISO date/datetime fixture values, but production code must not import
the fixture or any `analysis/` module.

Compare a canonical JSON projection with the literal expected object. Also
assert the canonical serialization SHA-256 stored in the fixture, so reference
drift is explicit in review rather than regenerated silently.

## 6. Required acceptance tests

Prove all of the following:

1. built result composes the exact same ledger/group/tone/selection records as
   direct stage calls;
2. final tone audit `selected_unit_ids` equals selector
   `selected_unit_ids`, while state/day tone do not change during rebind;
3. invalid timezone and a fabricated steady-only hero become typed
   unavailable at the exact stage/reason; ordinary excluded rows do not;
4. input/provenance permutation is byte-equal;
5. empty input is built quiet/steady with no selected events;
6. delta trigger accepts exact semantic keys and upgrades only the matching
   unit; bare planet names do not upgrade anything;
7. exact, robust bucket and robust unknown remain valid; time-sensitive
   bucket/unknown rows remain audit-only;
8. fixed JSON probe is literal byte/semantic parity and its digest matches;
9. mutation fixtures 1–6 run through this public entrypoint:
   - two ordinary lunar aspects of one target are not hero;
   - same physical fact from two producers is one unit;
   - edge-orb fact is excluded noise;
   - two independent units make hero only with a rare/structural anchor;
   - A->B->C does not create a transitive group;
   - a single rare anchor is quiet + `main_event`;
10. background does not create groups/tone and a fast factor alone does not
    create hero/day tone;
11. records are frozen and expose no legacy aliases.

## 7. GRACE and verification

Register `M-TODAY-CONVERGENCE-PIPELINE`, its edges to canon/ledger/groups/tone/
selection, and a `UC-TODAY-CONVERGENCE-W2-PIPELINE` row containing the fixed
probe and mutation gate.

Run:

```bash
cd apps/api
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_convergence_canon.py \
  tests/test_today_convergence_units.py \
  tests/test_today_convergence_ledger.py \
  tests/test_today_convergence_groups.py \
  tests/test_today_convergence_tone.py \
  tests/test_today_convergence_selection.py \
  tests/test_today_convergence_pipeline.py -q
cd ../..
/opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check \
  apps/api/app/services/today_convergence_pipeline.py \
  apps/api/tests/test_today_convergence_pipeline.py
python3 scripts/grace_lint.py apps/api/app --quiet
bash scripts/grace/check-markers.sh
git diff --check
```

Report exact counts, the fixed-probe SHA, mutation 1–6 outcomes, unavailable
stage/reason examples, and exact changed paths.

## 8. Out of scope

- conversion from `AstroSignal`/`ActivationLayer`/legacy factor ledger into
  `RawPhysicalFact` (next packet);
- sidecar/HTTP/DB/user profile calls;
- wire/event-time/period-context/access/preview projection;
- snapshot persistence and structured runtime logs;
- LLM, pregen, frontend or full ephemeris corpus replay;
- any W1 canon/threshold/frequency change.
