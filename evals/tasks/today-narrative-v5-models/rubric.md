# Today narrative v5 — deterministic rubric

This rubric is immutable with the task. It is applied to both response arms;
arm B is normalized from arrays to the keyed production shape before scoring.

## Automatic metrics

Each response contributes these values:

- `strict_support`: arm A is `1`; arm B is `0` only for the explicit
  `strict_unsupported` class.
- `json_valid`: JSON parses without markdown fences and matches the input
  block/template shape after normalization.
- `truncated_rate`: share of responses whose measured `completion_tokens`
  reached that model's `max_tokens` cap; this is reported independently from
  `json_valid`, and capped responses do not receive content scores.
- `fill_rate`: non-null, non-empty claims divided by required claims.
- `claim_binding`: every non-null claim has non-empty `sourceEventIds` fully
  contained in the block's selected evidence IDs, and block keys are exact.
- `sanitizer_pass`: every non-null claim passes the production sanitizer's
  forbidden-token and sphere/facet/polarity grounding checks.
- `length_ok`: summary ≤220, meaning ≤260, action ≤180 characters.
- `stamp_hits`: count of v5 forbidden-stamp occurrences.
- `datetime_leak`: count of clock/date/window patterns in claims.
- `name_rule`: first name occurs no more than once in the complete response.
- `lexicon_cover`: each non-null facet claim contains at least one safe
  lexicon term for that facet; facet-null claims are not penalized.

The scorer also reports p50/p95 latency, usage-based cost, cost per 1,000
narratives, monthly pre-generation estimate (500 users/day × 30), and
repeatability as token Jaccard across the two repeats for matching blocks. The
HTML report additionally projects measured mean cost to 3000 calls/month for
100 DAU and splits completion usage into reasoning and visible tokens when
the provider supplies `completion_tokens_details.reasoning_tokens`.

## Composite score

`auto_score` is zero when `json_valid` is zero. Otherwise:

```text
sanitizer_pass * 30
+ fill_rate       * 15
+ claim_binding   * 10
+ length_ok       * 10
+ lexicon_cover   * 10
+ stamp_clean     * 10
+ datetime_clean  * 10
+ name_rule       *  5
```

`stamp_clean`, `datetime_clean`, and `name_rule` are one minus their bounded
violation rate. `json_valid`, `claim_binding`, and all ratios are measured per
response and then averaged by model/arm.

## Human blind review

Review the baseline nano and the top two models by arm-A `auto_score`, with
about ten shuffled blocks per candidate. Store only masked text in committed
review artifacts. Score beauty and grounding accuracy from 1 to 5, then add
notes and a migration verdict separately from this automatic rubric.

The recommended production candidate is the cheapest model whose arm-A
`auto_score` is at least the nano score and whose arm-A `sanitizer_pass` is at
least the nano score. The strict-schema verdict must separately consider
`strict_support`, arm-B `json_valid`, and quality degradation versus arm A.

## Sanity control

The baseline nano fixture must retain at least one known cross-facet failure in
the selftest. If that control stops failing, the harness is invalid and a paid
run must not be accepted.
