# ############################################################################
# AI_HEADER: MODULE_TODAY_PREVIEW_ACCESS — request-scoped local preview access.
# ROLE: Derives full-content access only from an authorized Today selection value.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-PREVIEW-ACCESS
# purpose: Derive Today content access from the real access result and the
#          already-authorized immutable request selection context.
# owns:
#   - apps/api/app/services/today_preview_access.py
# inputs: ContentAccessState and TodaySelectionContext values.
# outputs: Original access instance or a new full access value with null metadata.
# dependencies: Access schema and Today selection context only.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Only force_v2=true with LOCAL_DEV_PREVIEW receives full access.
#   - Ordinary, global, and malformed contexts preserve the same access instance.
#   - Inputs, settings, access ledgers, headers, and ambient state never mutate.
# failure_policy: Total pure resolver; unrecognized combinations preserve access.
# END_MODULE_CONTRACT: M-TODAY-PREVIEW-ACCESS

# START_MODULE_MAP: M-TODAY-PREVIEW-ACCESS
# public_entrypoints:
#   - resolve_today_access_for_selection
# semantic_blocks:
#   - ACCESS_RESOLVER: closed request-scoped access derivation.
# owned_tests:
#   - apps/api/tests/test_today_preview_access.py
# END_MODULE_MAP: M-TODAY-PREVIEW-ACCESS

from __future__ import annotations

from app.schemas.access import ContentAccessState
from app.services.today_selection_context import (
    TodaySelectionContext,
    TodaySelectionSource,
)


# START_BLOCK: ACCESS_RESOLVER
def resolve_today_access_for_selection(
    *,
    access_state: ContentAccessState,
    selection_context: TodaySelectionContext,
) -> ContentAccessState:
    # START_FUNCTION_CONTRACT: F-M-TODAY-PREVIEW-ACCESS.resolve_today_access_for_selection
    # purpose: Grant request-local full content to the exact authorized preview selection.
    # inputs: access_state — real AccessService result; selection_context — authorized selection.
    # returns: New full/null access for local preview, otherwise the original access instance.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none; non-matching and malformed contexts fail closed.
    # END_FUNCTION_CONTRACT: F-M-TODAY-PREVIEW-ACCESS.resolve_today_access_for_selection
    """Resolve access without inspecting or mutating ambient request state."""
    is_local_preview = (
        selection_context.force_v2 is True
        and selection_context.source is TodaySelectionSource.LOCAL_DEV_PREVIEW
    )
    if not is_local_preview:
        return access_state

    return ContentAccessState(
        state="full",
        reason=None,
        referral_days_left=None,
        subscription_active=None,
        access_until=None,
    )
# END_BLOCK: ACCESS_RESOLVER
