// ############################################################################
// AI_HEADER: MODULE_TODAY_FOCUS_RELATION
// ROLE: Presentation helper computing event relation (convergence_event | independent_event) from provenance partition.
// DEPENDENCIES: @/lib/contracts/today
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-FOCUS-RELATION
// purpose: Partition TodayFocusEvent sourceActivationIds against focus.convergence sourceActivationIds.
// owns:
//   - lib/presentation/today-focus-relation.ts
// inputs: event (TodayFocusEvent), focusState (string), convergenceSourceActivationIds (readonly string[] | null | undefined)
// outputs: "convergence_event" | "independent_event"
// dependencies: @/lib/contracts/today
// side_effects: none (pure calculation)
// emitted_logs: none
// failure_policy: returns "independent_event" on missing or non-matching IDs
// END_MODULE_CONTRACT: M-TODAY-FOCUS-RELATION

// START_MODULE_MAP: M-TODAY-FOCUS-RELATION
// public_entrypoints:
//   - getEventRelation
// semantic_blocks:
//   - RELATION_PARTITION: pure set intersection for event relation
// owned_tests:
//   - __tests__/components/TodayFocus.test.tsx
// END_MODULE_MAP: M-TODAY-FOCUS-RELATION

import type { TodayFocusEvent } from "@/lib/contracts/today"

export type EventRelation = "convergence_event" | "independent_event"

// START_BLOCK: RELATION_PARTITION
export function getEventRelation(
  event: TodayFocusEvent,
  focusState: string,
  convergenceSourceActivationIds?: readonly string[] | null,
): EventRelation {
  // START_FUNCTION_CONTRACT: F-M-TODAY-FOCUS-RELATION.getEventRelation
  // purpose: Compute relation attribute ("convergence_event" | "independent_event") from provenance partition (§3.5 amendment, §5.1 doc 28).
  // inputs: event (TodayFocusEvent), focusState (string), convergenceSourceActivationIds (readonly string[] | null | undefined)
  // returns: EventRelation ("convergence_event" | "independent_event")
  // side_effects: none
  // emitted_logs: none
  // error_behavior: returns "independent_event" for single_impulses or non-matching IDs
  // END_FUNCTION_CONTRACT: F-M-TODAY-FOCUS-RELATION.getEventRelation
  if (focusState !== "convergence_today" || !convergenceSourceActivationIds || convergenceSourceActivationIds.length === 0) {
    return "independent_event"
  }

  const convSet = new Set(convergenceSourceActivationIds)
  const eventActIds = event.sourceActivationIds || []

  const hasIntersection = eventActIds.some((actId) => convSet.has(actId))
  return hasIntersection ? "convergence_event" : "independent_event"
}
// END_BLOCK: RELATION_PARTITION
