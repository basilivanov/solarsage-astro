# ############################################################################
# AI_HEADER: MODULE_TODAY_SELECTION_CONTEXT — pure request-scoped V1/V2 selection.
# ROLE: Resolves an immutable selection value for explicit propagation by callers.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-SELECTION-CONTEXT
# purpose: Resolve the Today scoring family from global enablement and an
#          already-authorized local preview decision without ambient state.
# owns:
#   - apps/api/app/services/today_selection_context.py
# inputs: global_v2_enabled and preview_authorized boolean decisions.
# outputs: immutable TodaySelectionContext with a closed selection source.
# dependencies: Python dataclasses and enum standard library modules.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Context values have exactly force_v2 and source fields.
#   - Preview authorization takes source precedence over global flags.
#   - Selection values exist only where callers explicitly pass them.
# failure_policy: n/a (total pure resolver over boolean inputs).
# END_MODULE_CONTRACT: M-TODAY-SELECTION-CONTEXT

# START_MODULE_MAP: M-TODAY-SELECTION-CONTEXT
# public_entrypoints:
#   - TodaySelectionSource
#   - TodaySelectionContext
#   - resolve_today_selection_context
# semantic_blocks:
#   - SELECTION_VALUE: closed source enum and immutable request value.
#   - SELECTION_RESOLVER: pure truth-table resolver.
# owned_tests:
#   - apps/api/tests/test_today_selection_context.py
# END_MODULE_MAP: M-TODAY-SELECTION-CONTEXT

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


# START_BLOCK: SELECTION_VALUE
class TodaySelectionSource(StrEnum):
    """Closed provenance values for a Today scoring-family selection."""

    GLOBAL_FLAGS = "global_flags"
    LOCAL_DEV_PREVIEW = "local_dev_preview"


@dataclass(frozen=True, slots=True)
class TodaySelectionContext:
    """Immutable request value passed explicitly across selection boundaries."""

    force_v2: bool
    source: TodaySelectionSource
# END_BLOCK: SELECTION_VALUE


# START_BLOCK: SELECTION_RESOLVER
def resolve_today_selection_context(
    *,
    global_v2_enabled: bool,
    preview_authorized: bool,
) -> TodaySelectionContext:
    # START_FUNCTION_CONTRACT: F-M-TODAY-SELECTION-CONTEXT.resolve_today_selection_context
    # purpose: Resolve request-scoped V2 selection and its closed provenance.
    # inputs: global_v2_enabled — global family decision; preview_authorized —
    #         prior authorization decision for a local development preview.
    # returns: frozen, slotted TodaySelectionContext following the four-row truth table.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-TODAY-SELECTION-CONTEXT.resolve_today_selection_context
    """Resolve selection without reading or mutating process-global state."""
    if preview_authorized:
        return TodaySelectionContext(
            force_v2=True,
            source=TodaySelectionSource.LOCAL_DEV_PREVIEW,
        )
    return TodaySelectionContext(
        force_v2=bool(global_v2_enabled),
        source=TodaySelectionSource.GLOBAL_FLAGS,
    )
# END_BLOCK: SELECTION_RESOLVER
