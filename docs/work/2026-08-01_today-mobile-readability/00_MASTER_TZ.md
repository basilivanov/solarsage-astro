# Today mobile readability — master packet

## Goal

Make the 2 August Today and calendar usable inside Telegram on iPhone: no content under the Mini App chrome, event-first impulse drilldown, useful deterministic content when LLM narrative is unavailable, and readable calendar signals.

## Waves

- 01: Telegram content safe-area propagation and top-control layout.
- 02: event-first impulse drilldown and non-blocking narrative fallback.
- 03: calendar day-tone contract and compact icons.

## Acceptance

- Date headers, calendar arrows, and modal headers stay below Telegram's content safe area and iOS safe area fallback.
- A drilldown names the exact event, dates every cross-midnight peak/window, and places event meaning before sphere context.
- Deterministic facts remain visible for `contentState=unavailable`; the unavailable LLM state does not present as a blocking error.
- Calendar cells expose an accessible, non-color-only signal for published day tone and lunar milestones.
- Existing public `data-testid` and Today state contracts remain compatible.

No visual baselines are updated in this wave.
