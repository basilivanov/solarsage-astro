# AI_HEADER
# module: M-CONTRACTS.access
# canon: docs/GRACE_CANON.md §6
# wave: W-1.1B
# purpose: User-level access state. Mirrors packages/contracts/access.ts
#          byte-for-byte at the JSON wire level (field names + optionality).

# START_MODULE_CONTRACT: M-CONTRACTS.access
# purpose: Define UserAccessState enum and AccessSummary payload.
# invariants:
#   - UserAccessState literal set is closed: trial | subscription | expired | none.
#     Changing it is a contract_version bump (canon §6).
#   - AccessSummary.access_until is an ISO-8601 string, never datetime.
# emits: nothing.
# consumes: schemas._base.CamelModel.
# END_MODULE_CONTRACT

# START_MODULE_MAP: M-CONTRACTS.access
# - UserAccessState: Literal alias for the user-level state machine.
# - AccessSummary: top-level summary returned by /api/access (future wave).
# END_MODULE_MAP

# START_BLOCK: ACCESS_TYPES
from __future__ import annotations

from typing import Literal

from ._base import CamelModel

UserAccessState = Literal["trial", "subscription", "expired", "none"]


class AccessSummary(CamelModel):
    user: UserAccessState
    referral_days_left: int
    subscription_active: bool
    access_until: str | None = None
# END_BLOCK: ACCESS_TYPES
