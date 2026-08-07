# ############################################################################
# AI_HEADER: MODULE_MIGRATION_0031_CHECKIN-OBSERVED-SPHERES — canonicalize stored check-in sphere keys.
# ROLE: Performs the one-time JSON data migration for EveningCheckin observed spheres.
# ############################################################################

# START_MODULE_CONTRACT: M-MIGRATION-0031-CHECKIN-OBSERVED-SPHERES
# purpose: Migrate persisted evening_checkins.observed_spheres to the twelve
#   canonical product sphere keys without guessing unknown data.
# owns:
#   - apps/api/alembic/versions/0031_checkin_observed_spheres.py
# inputs: Database at revision 0030_sphere_natal_narr.
# outputs: Canonicalized observed_spheres JSON arrays or a counted migration failure.
# dependencies: Alembic operations and SQLAlchemy Core.
# side_effects: Updates only evening_checkins.observed_spheres; downgrade is a
#   data-preserving no-op because the rename is intentionally irreversible.
# emitted_logs: none.
# invariants: null stays null; aliases are mapped and deduplicated in order;
#   unknown keys abort before any row is updated; an empty table is a no-op.
# failure_policy: raises RuntimeError with stable unknown-key occurrence counts.
# END_MODULE_CONTRACT: M-MIGRATION-0031-CHECKIN-OBSERVED-SPHERES

# START_MODULE_MAP: M-MIGRATION-0031-CHECKIN-OBSERVED-SPHERES
# public_entrypoints:
#   - upgrade
#   - downgrade
# semantic_blocks:
#   - CHECKIN_SPHERE_DATA: collect, validate, map, deduplicate, and update JSON rows.
#   - IRREVERSIBLE_ROLLBACK: preserve canonical data on downgrade.
# owned_tests:
#   - apps/api/tests/test_checkin_observed_spheres_migration.py
# END_MODULE_MAP: M-MIGRATION-0031-CHECKIN-OBSERVED-SPHERES

from __future__ import annotations

from collections import Counter
from typing import Any

from alembic import op
import sqlalchemy as sa


revision = "0031_checkin_observed_spheres"
down_revision = "0030_sphere_natal_narr"
branch_labels = None
depends_on = None

_CANONICAL_SPHERES = frozenset(
    {
        "work",
        "finance",
        "documents",
        "relationships",
        "sport",
        "communication",
        "health",
        "home_family",
        "travel",
        "creativity",
        "study",
        "friends_goals",
    }
)
_LEGACY_RENAMES = {"money": "finance", "shopping": "finance"}
_REMOVED_KEYS = frozenset({"decisions"})


def _unknown_label(value: object) -> str:
    if isinstance(value, str):
        return value
    return f"<{type(value).__name__}>"


def _canonicalize_value(value: object, unknown: Counter[str]) -> object:
    """Return one canonical list while recording every unknown occurrence."""
    if value is None:
        return None
    if not isinstance(value, list):
        unknown[f"<non-array:{type(value).__name__}>"] += 1
        return value

    result: list[str] = []
    seen: set[str] = set()
    for raw_key in value:
        if not isinstance(raw_key, str):
            unknown[_unknown_label(raw_key)] += 1
            continue
        if raw_key in _REMOVED_KEYS:
            continue
        canonical_key = _LEGACY_RENAMES.get(raw_key, raw_key)
        if canonical_key not in _CANONICAL_SPHERES:
            unknown[raw_key] += 1
            continue
        if canonical_key not in seen:
            seen.add(canonical_key)
            result.append(canonical_key)
    return result


def _format_unknown_counts(unknown: Counter[str]) -> str:
    return ", ".join(
        f"{key}={unknown[key]}" for key in sorted(unknown)
    )


# START_BLOCK: CHECKIN_SPHERE_DATA
def upgrade() -> None:
    # START_FUNCTION_CONTRACT: F-M-MIGRATION-0031-CHECKIN-OBSERVED-SPHERES.upgrade
    # purpose: Canonicalize all persisted observed sphere arrays in one transaction.
    # inputs: Database at 0030_sphere_natal_narr.
    # returns: None; raises with occurrence counts for unknown values.
    # side_effects: Updates evening_checkins.observed_spheres only after a full preflight.
    # emitted_logs: none.
    # error_behavior: RuntimeError aborts the migration before any update when
    #   an unknown key or malformed JSON shape is found.
    # END_FUNCTION_CONTRACT: F-M-MIGRATION-0031-CHECKIN-OBSERVED-SPHERES.upgrade
    bind = op.get_bind()
    checkins = sa.table(
        "evening_checkins",
        sa.column("id"),
        sa.column("observed_spheres", sa.JSON()),
    )

    updates: list[tuple[Any, object]] = []
    unknown: Counter[str] = Counter()
    rows = bind.execute(
        sa.select(checkins.c.id, checkins.c.observed_spheres)
    )
    for row in rows:
        original = row.observed_spheres
        canonical = _canonicalize_value(original, unknown)
        if not unknown and canonical != original:
            updates.append((row.id, canonical))
        elif unknown:
            # Keep collecting all rows so the failure report is actionable;
            # no update is issued until the complete preflight succeeds.
            continue

    if unknown:
        raise RuntimeError(
            "checkin observed_spheres migration aborted; "
            f"unknown values: {_format_unknown_counts(unknown)}"
        )

    for row_id, canonical in updates:
        bind.execute(
            sa.update(checkins)
            .where(checkins.c.id == row_id)
            .values(observed_spheres=canonical)
        )
# END_BLOCK: CHECKIN_SPHERE_DATA


# START_BLOCK: IRREVERSIBLE_ROLLBACK
def downgrade() -> None:
    # START_FUNCTION_CONTRACT: F-M-MIGRATION-0031-CHECKIN-OBSERVED-SPHERES.downgrade
    # purpose: Leave canonical check-in data intact when the schema revision is rolled back.
    # inputs: Database at 0031_checkin_observed_spheres.
    # returns: None.
    # side_effects: none; old aliases cannot be reconstructed without guessing.
    # emitted_logs: none.
    # error_behavior: no-op.
    # END_FUNCTION_CONTRACT: F-M-MIGRATION-0031-CHECKIN-OBSERVED-SPHERES.downgrade
    return None
# END_BLOCK: IRREVERSIBLE_ROLLBACK
