# Canon: Failure handling policy

Date: 2026-06-09
Status: active project canon

## Core rule

A user-facing result must be based on trustworthy computed data.

When a required computation, generation step, contract validation, or external dependency fails, the product must show a clear error or incomplete-result state.

Do not replace a failed result with generic generated content that looks like a successful result.

## Forbidden

- Generic content presented as a successful result.
- Demo or mock payloads presented as production data.
- Hidden fallback that makes a failed path look successful.
- Technical confidence shown as statistical probability.
- Saving a successful result when required structured output was not produced.

## Allowed

- Retry with explicit limits.
- Error state.
- Partial result state, only when it is based on real computed data and is clearly marked as partial.
- Rollback or refund where the product contract requires it.
- Test fixtures in test/dev mode only.

## Review rule

Any hidden generic fallback in user-facing output is a blocker.

A reviewer must reject a packet if failure handling can mislead the user into thinking a failed result succeeded.

## Agent rule

Every packet must check failure behavior for:

- computation failure;
- invalid structured generation;
- external service unavailable;
- contract validation failure;
- missing required profile/input data.

If the user can mistake failure output for a successful result, the implementation is not acceptable.
