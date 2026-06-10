# Review: 5e7643a — Wave 4 Full Report Backend

Date: 2026-06-11
Status: CHANGES REQUESTED
Reviewed commit: `5e7643adcd447099dc8fb31d45c514c3256a4b0c`
Branch: `feat/natal-full-report`
Related TZ: `docs/work/2026-06-10_natal_full_report_cache_TZ.md`
Previous accepted Wave 3 review: `docs/work/2026-06-11_7236726_wave_3_test_hardening_acceptance_review.md`

## 1. Scope reviewed

Wave 4 target:

- full report backend generation over deterministic `NatalContextData`;
- no fake/placeholder READY reports;
- invalid LLM output should become `FAILED_RETRYABLE`;
- hallucination guard before persistence;
- invalid block type rejection;
- report meta enrichment;
- preview `full_report_available` should reflect persisted READY reports.

Files changed in the Wave 4 diff:

- `apps/api/app/services/natal_report_service.py`
- `apps/api/app/services/natal_service.py`
- `apps/api/tests/test_natal_report_service.py`

Commit message reports: `81 natal tests all passing`.

## 2. Verdict

CHANGES REQUESTED.

The direction is correct and several important problems are fixed, but there are production-path blockers in validation. In particular, the tests currently prove some manually-constructed schema paths, while the actual LLM parse path can still bypass the claimed guarantees.

## 3. What is good

### GOOD 1 — No placeholder READY report on empty/garbage LLM output

`_generate_section_blocks()` now raises on empty LLM response and invalid JSON instead of returning placeholder text.

`generate_report()` catches the exception and sets:

```python
report.status = "FAILED_RETRYABLE"
report.error_code = "GENERATION_FAILED"
```

This is the right behavior: no fake/partial READY report is persisted when generation fails.

### GOOD 2 — Sections are generated all-or-nothing

`_generate_sections()` no longer catches a per-section error and inserts:

```python
ParagraphBlock("Раздел временно недоступен...")
```

If one section fails or returns no blocks, generation fails and the report remains non-READY. This matches the no-placeholder requirement.

### GOOD 3 — Report meta enrichment exists

`get_report()` now calls `_populate_report_meta()` after `_report_to_read()`, filling profile-related meta fields from `UserProfile` and `NatalChartCache`.

### GOOD 4 — Preview availability is no longer hardcoded False

`NatalService.get_preview()` now checks for READY `NatalReport` rows and sets `full_report_available` dynamically.

## 4. Blockers

### BLOCKER 1 — Unknown LLM block types are still not rejected in the production parse path

The Wave 4 summary says invalid block types are rejected. But the actual production parse path still converts unknown block types into paragraph blocks.

Current `_parse_blocks()` behavior:

```python
else:
    # Fallback: unknown block type → paragraph
    blocks.append(ParagraphBlock(type="paragraph", text=str(b)))
```

Impact:

- LLM can return `{ "type": "timeline", ... }`.
- `_parse_blocks()` converts it into `ParagraphBlock`.
- `_validate_sections()` then sees a valid `paragraph` block and does not reject it.
- The report can become READY even though the LLM emitted an invalid block type.

The new test `test_rejects_invalid_block_type` only constructs `NatalReportSectionRead` directly with a dict and verifies Pydantic discriminated-union behavior. That does not test the actual `_generate_section_blocks()` / `_parse_blocks()` production path.

Required fix:

Change `_parse_blocks()` to reject unknown types:

```python
else:
    raise ValueError(f"Unknown natal report block type: {b_type}")
```

Also stop silently skipping malformed blocks if the LLM produced them. A malformed block should fail generation, not disappear.

Required tests:

1. `_parse_blocks([{ "type": "timeline", "text": "..." }])` raises `ValueError`.
2. `_generate_section_blocks()` with valid JSON containing unknown block type raises `ValueError`.
3. `generate_report()` with LLM JSON containing unknown block type returns `FAILED_RETRYABLE`, not READY.

### BLOCKER 2 — Hallucination detection only scans `block.text`, so list/pros-cons content can bypass it

`_validate_sections()` checks:

```python
text_to_check = getattr(block, "text", "") or ""
```

This covers blocks with a direct `.text` field, such as `paragraph`, `lead`, `heading`, `callout`, and `quote`.

But it does not scan:

- `ListBlock.items[]`;
- `ProsConsBlock.pros[].title`;
- `ProsConsBlock.pros[].text`;
- `ProsConsBlock.cons[].title`;
- `ProsConsBlock.cons[].text`;
- `HighlightsBlock.items[].title/text` if those ever appear;
- `BulletsBlock.items[]` if those ever appear.

Impact:

The LLM can write fabricated planets in a list/pros-cons block and still pass validation, for example:

```json
{ "type": "list", "items": ["Зевс в 10 доме даёт статус"] }
```

or:

```json
{
  "type": "pros_cons",
  "pros": [{"title": "Прозерпина", "text": "..."}],
  "cons": []
}
```

Required fix:

Add a recursive text extractor for every block type and scan all human-readable string fields.

Example direction:

```python
def _iter_block_texts(block: NatalBlock) -> Iterable[str]:
    if hasattr(block, "text") and block.text:
        yield block.text
    if isinstance(block, ListBlock):
        yield from block.items
    if isinstance(block, ProsConsBlock):
        for item in [*block.pros, *block.cons]:
            yield item.title
            yield item.text
    if isinstance(block, HighlightsBlock):
        for item in block.items:
            yield item.title
            yield item.text
    if isinstance(block, BulletsBlock):
        yield from block.items
```

Required tests:

1. `Зевс` inside `ListBlock.items` is rejected.
2. `Прозерпина` inside `ProsConsBlock.pros[].title/text` is rejected.
3. Forbidden name inside `CalloutBlock.title` is rejected, not only callout text.

### BLOCKER 3 — `full_report_available` is not tied to the current natal context/profile hash

Preview currently checks:

```python
select(NatalReport).where(
    NatalReport.user_id == user_id,
    NatalReport.status == "READY",
)
```

Impact:

- User generates a READY report for old birth data.
- User changes birth time/place/coordinates.
- `NatalContextService` builds a new active natal context.
- Preview still sees any old READY report for the user and sets `full_report_available=True`.
- The UI can claim a full report exists for the current preview while only an old-context report exists.

Required fix:

Tie `full_report_available` to the current active natal context.

Suggested logic:

1. Build/get current `natal_context`.
2. Compute current `profile_hash`.
3. Find current active `NatalChartCache` row.
4. Check READY `NatalReport` where:

```python
NatalReport.user_id == user_id
NatalReport.natal_context_id == current_cache_entry.id
NatalReport.status == "READY"
NatalReport.prompt_version == PROMPT_VERSION
NatalReport.report_schema_version == REPORT_SCHEMA_VERSION
```

Required tests:

1. READY report for old context + current profile changed → preview `full_report_available=False`.
2. READY report for current active context → preview `full_report_available=True`.

### BLOCKER 4 — Special points are included in LLM input but some are unconditionally forbidden

`_build_llm_input()` includes:

```python
"special_points": [ ... for sp in context.special_points ]
```

But `_FORBIDDEN_PLANET_PATTERNS` unconditionally forbids:

```python
"хирон", "селена", "лилит"
```

Impact:

If the deterministic context contains Chiron/Selena/Lilith and the LLM mentions them because they were supplied in `special_points`, the report fails validation.

This is especially risky because the broader TZ explicitly includes special points as deterministic chart facts. The guard should reject them only if the LLM calls them planets or invents placements, not if it references allowed special points from the context.

Required fix — choose one:

1. Do not include special points in the LLM input until the report validation supports them.
2. Or build an allowed special-points set from `context.special_points` and allow those exact names when mentioned as special points.
3. Or keep them banned, but remove them from deterministic context and document that Wave 4 does not support special-point interpretation yet.

Required tests:

1. If `context.special_points` contains Lilith/Chiron/Selena, a neutral allowed mention should pass if special points are supported.
2. A fabricated use such as “Лилит как планета в 3 доме” should fail if not supported.

## 5. Major risks / claim mismatches

### RISK 1 — `_validate_sections()` docstring claims sign hallucination detection, but no sign check exists

The docstring says:

```text
Hallucinated sign names rejected
```

but the code builds `known_signs` and then never uses it.

If sign hallucination detection is required in Wave 4, this is a blocker. If not required yet, remove the claim from the docstring and leave it as future work.

Suggested follow-up test if implemented:

- LLM text containing “Змееносец” as a natal sign should fail.

### RISK 2 — `_check_hallucinated_planets()` receives `known_planet_names` but does not use it

The parameter is currently unused. That makes the function a static blacklist rather than a context-aware guard.

This is not necessarily wrong, but the naming/message says “only reference planets from provided chart context”, while the actual behavior is blacklist-only.

### RISK 3 — `get_report(report_id=...)` can return non-READY reports

When `report_id` is provided, `get_report()` does not restrict status to READY. It can return a FAILED/GENERATING report as `NatalReportRead`.

This may be intentional for polling, but it should be explicit in the API contract. If the frontend expects only readable full reports here, filter READY or expose a separate status endpoint.

## 6. Test review

The new tests are useful but incomplete for the production path.

Good tests added:

- forbidden planet names in paragraph text;
- real Russian planet names pass;
- manually-constructed invalid block type rejected by Pydantic;
- all 8 intended report block types pass;
- LLM `None` → `FAILED_RETRYABLE`;
- garbage JSON → `FAILED_RETRYABLE`.

Missing tests required before acceptance:

1. LLM JSON with unknown block type goes through `_generate_section_blocks()` and fails.
2. Unknown block type does not become `ParagraphBlock(str(b))`.
3. Forbidden names in list/pros-cons/callout-title are detected.
4. `full_report_available` is scoped to current active `NatalChartCache`.
5. Special points behavior is explicitly tested: either allowed from context or intentionally excluded.

## 7. Acceptance decision

Do not accept Wave 4 yet.

Accept after:

- unknown block fallback is removed;
- hallucination scanning covers all text-bearing fields;
- `full_report_available` is tied to the current active natal context;
- special-points policy is made consistent with LLM input;
- tests cover the real production parse path, not only manually-built schema objects.
