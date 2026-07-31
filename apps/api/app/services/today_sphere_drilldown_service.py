# ############################################################################
# AI_HEADER: MODULE_TODAY-SPHERE-DRILLDOWN — deterministic published sphere evidence.
# ROLE: Authorizes an owner snapshot and projects one canonical sphere from the
#   existing pure Today convergence wire projection.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-SPHERE-DRILLDOWN
# purpose: Serve deterministic sphere evidence for one published owner snapshot.
# owns:
#   - apps/api/app/services/today_sphere_drilldown_service.py
# inputs: owner UUID, snapshot UUID, canonical sphere key, and AsyncSession.
# outputs: TodaySphereDrilldownPayload with event order inherited from payload projection.
# dependencies: TodaySnapshotService, AccessService, public Today convergence projection,
#   TodaySphereDrilldownPayload.
# side_effects: owner snapshot/access SELECTs only; no sidecar, LLM, or calculation.
# emitted_logs: none.
# invariants:
#   - missing/foreign/unpublished snapshots are indistinguishable to callers;
#   - preview and locked access are rejected before deterministic evidence projection;
#   - event/time mapping is reused from project_snapshot_payload;
#   - narrative fields never enter the drilldown wire shape.
# failure_policy: typed service errors are translated by the HTTP route; malformed
#   persisted projection data fails closed as snapshot-not-found.
# END_MODULE_CONTRACT: M-TODAY-SPHERE-DRILLDOWN

# START_MODULE_MAP: M-TODAY-SPHERE-DRILLDOWN
# public_entrypoints:
#   - TodaySphereDrilldownService.get_drilldown
#   - InvalidSphereError
#   - SnapshotNotFoundError
#   - AccessRequiredError
#   - SphereNotInSnapshotError
# semantic_blocks:
#   - AUTHORIZATION: owner snapshot and full-access gates.
#   - DETERMINISTIC_PROJECTION: reuse public Today payload projection.
#   - SPHERE_SELECTION: filter ordered events and matching convergence group.
# owned_tests:
#   - apps/api/tests/test_today_sphere_drilldown_api.py
# END_MODULE_MAP: M-TODAY-SPHERE-DRILLDOWN

from __future__ import annotations

from typing import get_args
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.today_convergence import CanonicalSphere
from app.schemas.today_sphere_drilldown import (
    TodaySphereDrilldownConvergence,
    TodaySphereDrilldownPayload,
)
from app.services.access_service import AccessService
from app.services.today_convergence_projection import (
    TodayConvergenceProjectionError,
    project_snapshot_payload,
)
from app.services.today_snapshot_service import TodaySnapshotService


CANONICAL_SPHERES = frozenset(get_args(CanonicalSphere))


class InvalidSphereError(ValueError):
    """The requested sphere is outside the canonical twelve-sphere set."""


class SnapshotNotFoundError(ValueError):
    """The snapshot is missing, foreign, unpublished, or not projectable."""


class AccessRequiredError(ValueError):
    """The snapshot exists but evidence requires full access."""


class SphereNotInSnapshotError(ValueError):
    """The canonical sphere has no selected deterministic evidence."""


# START_BLOCK: DETERMINISTIC_PROJECTION
class TodaySphereDrilldownService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_drilldown(
        self,
        user_id: UUID,
        snapshot_id: UUID,
        sphere_key: str,
    ) -> TodaySphereDrilldownPayload:
        # START_FUNCTION_CONTRACT: F-M-TODAY-SPHERE-DRILLDOWN.get_drilldown
        # purpose: Authorize and project one deterministic sphere evidence chain.
        # inputs: owner UUID, snapshot UUID, and canonical sphere key.
        # returns: TodaySphereDrilldownPayload with ordered event evidence.
        # side_effects: reads owner snapshot and access ledger.
        # emitted_logs: none.
        # error_behavior: raises typed errors for 422/403/404 route outcomes.
        # END_FUNCTION_CONTRACT: F-M-TODAY-SPHERE-DRILLDOWN.get_drilldown
        if sphere_key not in CANONICAL_SPHERES:
            raise InvalidSphereError(sphere_key)

        snapshot = await TodaySnapshotService(self.db).load_owned(user_id, snapshot_id)
        if snapshot is None or snapshot.published_at is None:
            raise SnapshotNotFoundError("snapshot_not_found")

        access = await AccessService(self.db).can_access_day(user_id, snapshot.target_date)
        if access.state != "full":
            raise AccessRequiredError("full_access_required")

        try:
            payload = project_snapshot_payload(snapshot, None, access)
        except TodayConvergenceProjectionError as exc:
            raise SnapshotNotFoundError("snapshot_not_projectable") from exc

        events = [event for event in payload.events if event.sphere == sphere_key]
        if not events:
            raise SphereNotInSnapshotError("sphere_not_in_snapshot")

        convergence = next(
            (
                TodaySphereDrilldownConvergence(
                    id=group.id,
                    primary_sphere=group.primary_sphere,
                    secondary_sphere=group.secondary_sphere,
                    polarity=group.polarity,
                    evidence_level=group.evidence_level,
                    event_ids=group.event_ids,
                )
                for group in payload.convergences
                if sphere_key in {group.primary_sphere, group.secondary_sphere}
            ),
            None,
        )

        return TodaySphereDrilldownPayload(
            snapshot_id=payload.snapshot_id or str(snapshot.id),
            sphere=sphere_key,
            state=payload.state,
            day_tone=payload.day_tone,
            birth_time_mode=payload.birth_time.mode,
            events=events,
            convergence=convergence,
        )
# END_BLOCK: DETERMINISTIC_PROJECTION

