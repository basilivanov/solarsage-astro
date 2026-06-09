# Review: W-HORARY-ANSWER-QUALITY-V1

Date: 2026-06-09
Reviewed repository state: `origin/main` as visible through GitHub connector
Source TZ: `docs/work/2026-06-09_horary_answer_quality_TZ.md`
Canon dependency: `docs/FAILURE_HANDLING_CANON.md`

## Verdict

Status: **REWORK / BLOCKED**

I do not see an implementation commit for `W-HORARY-ANSWER-QUALITY-V1` in `origin/main` through the GitHub connector. The latest matching commit found is the TZ commit itself:

- `b1d9f7a7e58df8dd38d8151001b57222b509af15` — `Add horary answer quality TZ`

The current code path still appears to preserve the exact issues that this packet was supposed to remove.

## Blockers

### B1. Generic fallback answer still exists

The current `LLMService.generate_horary_answer()` still returns a generic fallback answer when structured LLM generation fails.

This violates `docs/FAILURE_HANDLING_CANON.md` and the packet requirement:

- do not save generic answer blocks;
- mark question failed/error;
- refund credit if applicable;
- show a real error state.

Expected behavior:

- invalid/missing LLM output must not create a `HoraryAnswer` row;
- question status must become failed/error;
- credit refund behavior must execute where applicable.

### B2. Hardcoded timing still exists

The horary prompt still uses hardcoded default timing text equivalent to `2–3 недели` in the timing block template.

This violates the packet requirement: timing must be derived from explicit question timeframe or computed chart evidence, otherwise return a not-enough-evidence timing state.

Expected behavior:

- remove hardcoded default time range from prompt/template;
- introduce structured timing result;
- if no timing evidence exists, return `not_enough_evidence`.

### B3. Engine still returns tuple instead of structured evidence

The current engine still returns roughly:

- verdict;
- confidence;
- involved planets.

The packet requires a structured result containing:

- confidence label;
- confidence explanation;
- testimonies for;
- testimonies against;
- neutral factors;
- timing;
- calculation warnings.

Without this, the LLM still lacks enough evidence to explain the answer in a detailed, trustworthy way.

### B4. LLM still receives too little evidence

The answer generation call still appears to pass only question text, category, verdict, confidence, involved planets, ASC ruler, and significator.

It does not pass structured testimonies such as applying/separating aspect, orb, Moon testimony, house context, support/opposition factors, or timing evidence.

This is why answer quality remains shallow and generic.

### B5. Confidence still risks being treated as probability

The backend still stores numeric `confidence`, and the old verdict card model still uses numeric confidence. The packet requires public UI to show confidence as low/medium/high or strength of evidence, not event probability.

Expected behavior:

- API/blocks should include public confidence label and explanation;
- frontend must not show probability wording;
- numeric score should be internal/dev-only or clearly labelled as strength of indications.

## Required rework packet

Implement the actual code changes from `W-HORARY-ANSWER-QUALITY-V1`:

1. Replace `HoraryEngine.compute_verdict()` tuple return with a structured result or wrapper model.
2. Add evidence objects: for/against/neutral/timing/warnings.
3. Pass structured evidence to LLM.
4. Remove hardcoded timing default from prompt and UI assumptions.
5. Remove generic fallback answer creation.
6. On invalid LLM result: mark failed/error, refund if applicable, and do not save answer row.
7. Add backend tests for invalid JSON, LLM unavailable, no timing evidence, confidence labels.
8. Add frontend tests for confidence label, failed/error state, no probability wording, no default hardcoded timing.
9. Add grep guard for hardcoded timing and generic fallback text.

## Acceptance checklist

```text
[ ] Generic horary fallback answer removed.
[ ] Invalid LLM JSON does not save HoraryAnswer.
[ ] Invalid/unavailable generation marks question failed/error.
[ ] Credit refund remains correct.
[ ] Hardcoded `2–3 недели` default removed from horary prompt/template.
[ ] Timing supports derived / low-confidence / not_enough_evidence states.
[ ] Engine returns structured evidence, not only verdict/confidence/planets.
[ ] LLM receives structured computed evidence.
[ ] Public UI shows low/medium/high confidence, not probability.
[ ] Backend tests cover failure behavior.
[ ] Frontend tests cover failed/error rendering and confidence wording.
[ ] Grep guard blocks regression.
```

## Final conclusion

Do not accept this packet yet.

Either the implementation was not pushed to `origin/main`, or it was not discoverable through the GitHub connector. In the repository state visible to review, the main blockers remain.
