# Acceptance Review: 0a93abe — Wave 4 Full Report Backend Fixes

Date: 2026-06-11
Status: ACCEPTED
Reviewed commit: `0a93abebb6b629954917fa2c3f72c8174df3f1d0`
Branch: `feat/natal-full-report`
Previous Wave 4 review: `docs/work/2026-06-11_5e7643a_wave_4_full_report_backend_review.md`
Related TZ: `docs/work/2026-06-10_natal_full_report_cache_TZ.md`

## 1. Scope reviewed

This review checked commit `0a93abe` against the 4 blockers and 2 risks from the previous Wave 4 review:

1. Unknown LLM block types must fail, not become `ParagraphBlock`.
2. Hallucination guard must scan all human-readable text fields, not only `block.text`.
3. `full_report_available` must be tied to the current active natal context, not any old READY report.
4. Special points must be handled consistently with deterministic context.
5. Sign hallucination detection must either exist or not be claimed.
6. `_check_hallucinated_planets()` should become meaningfully context-aware.

Commit message reports: `64 Wave 4 tests + 6 Wave 3 tests all passing`.

## 2. Verdict

ACCEPTED.

The blockers from `5e7643a` are closed by code inspection and targeted tests. Wave 4 full-report backend can proceed to the next gate.

## 3. Blocker closure review

### BLOCKER 1 — Unknown block type fallback removed

Status: RESOLVED.

`_parse_blocks()` now raises hard on unknown block type:

```python
raise ValueError(f"Unknown natal report block type: {b_type}")
```

Malformed block data also raises `ValueError` instead of being silently skipped.

This means LLM output like:

```json
{"type": "timeline", "text": "..."}
```

no longer becomes a fake paragraph and cannot be persisted as READY.

Tests reviewed:

- `test_unknown_type_raises_value_error`
- `test_unknown_type_does_not_become_paragraph`
- `test_malformed_block_raises_value_error`
- `test_llm_unknown_block_type_produces_failed_retryable`

The last test covers the important production path through `generate_report()`, not only direct schema construction.

Acceptance result: OK.

### BLOCKER 2 — Hallucination guard scans all text fields

Status: RESOLVED.

New `_iter_block_texts(block)` walks human-readable fields across block variants:

- `ParagraphBlock.text`
- `LeadBlock.text`
- `HeadingBlock.text`
- `QuoteBlock.text`
- `ListBlock.items[]`
- `CalloutBlock.title/text`
- `ProsConsBlock.pros[].title/text`
- `ProsConsBlock.cons[].title/text`
- `HighlightsBlock.items[].title/text`
- `BulletsBlock.items[]`

`_validate_sections()` now runs `_check_hallucinated_planets()` and sign checks over every fragment from `_iter_block_texts()`.

Tests reviewed:

- `test_rejects_hallucinated_planet_in_list_items`
- `test_rejects_hallucinated_planet_in_pros_cons_title`
- `test_rejects_hallucinated_planet_in_pros_cons_text`
- `test_rejects_hallucinated_planet_in_callout_title`
- `test_rejects_hallucinated_planet_in_cons_text`
- `_iter_block_texts` helper tests for paragraph/lead/heading/list/callout/pros-cons/quote/divider.

Acceptance result: OK.

### BLOCKER 3 — `full_report_available` scoped to current context

Status: RESOLVED.

`NatalService.get_preview()` no longer checks for any READY report by user only. It now checks READY report by:

```python
NatalReport.user_id == user_id
NatalReport.natal_context_id == cache_entry.id
NatalReport.status == "READY"
NatalReport.prompt_version == PROMPT_VERSION
NatalReport.report_schema_version == REPORT_SCHEMA_VERSION
```

This prevents an old READY report from enabling full report access after birth data/profile hash changes.

Tests reviewed:

- `test_old_context_report_does_not_enable_availability`
- `test_current_context_report_enables_availability`

Acceptance result: OK.

### BLOCKER 4 — Special points policy made consistent

Status: RESOLVED.

The previous unconditional blacklist for Chiron/Selena/Lilith was split into:

- always-forbidden fabricated names: `Зевс`, `Прозерпина`, etc.;
- conditionally-allowed special-point names: `Хирон`, `Селена`, `Лилит` only if corresponding English sidecar names exist in `context.special_points`.

This matches the current design: special points may be present in deterministic context, and the LLM may reference them only when they were supplied as facts.

Tests reviewed:

- `test_special_points_allowed_when_in_context`
- `test_special_points_rejected_when_not_in_context`
- `test_lilith_rejected_when_not_in_context`
- `test_always_forbidden_planets_rejected_even_with_special_points`
- direct `_check_hallucinated_planets()` tests for Chiron/Lilith/Selena.

Acceptance result: OK.

## 4. Risk closure review

### RISK 1 — Sign hallucination detection claim is now implemented

Status: RESOLVED ENOUGH FOR WAVE 4.

`_validate_sections()` now rejects fabricated sign stems:

```python
forbidden_sign_stems = ["змееносц", "ophiuchus"]
```

This catches declined Russian forms such as `Змееносце`/`Змееносцем` by stem matching.

Test reviewed:

- `test_rejects_hallucinated_sign_ophiuchus`
- `test_allows_real_sign_names_in_russian`

Acceptance result: OK.

### RISK 2 — `_check_hallucinated_planets()` is now context-aware for special points

Status: PARTIALLY RESOLVED, NON-BLOCKING.

The function now uses `allowed_special_point_names` to allow or reject Chiron/Selena/Lilith depending on deterministic context.

`known_planet_names` is still mostly a future hook rather than an active general whitelist; the current implementation remains blacklist-based for fabricated planets. That is acceptable for Wave 4 because the blocker was about obvious hallucination patterns and special-point consistency, not a full entity-recognition whitelist.

## 5. Non-blocking notes

### NOTE 1 — English special-point mentions are not currently rejected

The current `_SPECIAL_POINT_PATTERNS` scan checks Russian output terms like `хирон`, `селена`, `лилит` against English sidecar names. If the LLM outputs English `Chiron` while Chiron is not in context, this may not be rejected.

Because the prompt explicitly requires Russian output and forbids anglicisms, this is not a Wave 4 blocker. A future hardening pass could add English text-pattern checks too.

### NOTE 2 — Report parser accepts 8 report block types, while schema also contains legacy `highlights`/`bullets`

The service prompt allows the 8 report block types:

```text
lead, paragraph, heading, list, callout, pros_cons, quote, divider
```

`_validate_sections()` includes `highlights` and `bullets` in valid block types because the wider schema contains them. `_parse_blocks()` does not currently parse LLM-produced `highlights`/`bullets`.

This is acceptable because Wave 4 report generation prompts the LLM to emit the 8 report block types only. If full-report LLM output should later support `highlights`/`bullets`, `_parse_blocks()` should be extended deliberately with tests.

### NOTE 3 — Test evidence is commit-local

Commit message reports `64 Wave 4 tests + 6 Wave 3 tests all passing`. CI artifacts were not independently fetched in this review.

## 6. Acceptance decision

Accepted.

Wave 4 full-report backend now satisfies the reviewed acceptance points:

- no placeholder READY reports on LLM failure;
- invalid JSON and invalid block type produce `FAILED_RETRYABLE`;
- production parse path rejects unknown block types;
- hallucination guard scans all text-bearing fields;
- special points are allowed only when present in deterministic context;
- `full_report_available` is tied to the current active natal context;
- sign hallucination claim has an implemented guard and tests.
