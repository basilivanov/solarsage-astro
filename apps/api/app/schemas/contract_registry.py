# ############################################################################
# AI_HEADER: MODULE_CONTRACT_REGISTRY — explicit public OpenAPI schema roots.
# ROLE: Owns the deterministic list of API public root schemas used by contract generation.
# ############################################################################

# START_MODULE_CONTRACT: M-CONTRACT-REGISTRY
# purpose: Provide an explicit class-object registry for the API-to-frontend
#   contract surface and validate that only API-owned CamelModel roots are
#   exposed to the OpenAPI exporter.
# owns:
#   - apps/api/app/schemas/contract_registry.py
# inputs: API schema classes from feature modules.
# outputs: PUBLIC_CONTRACT_ROOTS and validate_public_contract_roots().
# dependencies: app.schemas feature modules, app.schemas._base.CamelModel.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Registry order is alphabetical by class name and stable.
#   - Shared implementation/base classes are never public roots.
#   - Validation errors include only index/name/reason, never schema payloads.
# failure_policy: deterministic TypeError/ValueError for invalid registries.
# END_MODULE_CONTRACT: M-CONTRACT-REGISTRY

# START_MODULE_MAP: M-CONTRACT-REGISTRY
# public_entrypoints:
#   - PUBLIC_CONTRACT_ROOTS
#   - validate_public_contract_roots
# semantic_blocks:
#   - PUBLIC_ROOT_IMPORTS: direct imports of feature-owned schema classes.
#   - PUBLIC_ROOTS: closed tuple of public OpenAPI root classes.
#   - REGISTRY_VALIDATION: deterministic registry guard helper.
# owned_tests:
#   - apps/api/tests/test_contract_registry.py
# END_MODULE_MAP: M-CONTRACT-REGISTRY

from __future__ import annotations

import inspect

from ._base import CamelModel
from .access import AccessSummary
from .activation import ActivationLayer
from .auth import AuthError, AuthSession, TelegramAuthRequest
from .calendar import CalendarPayload
from .checkin import CheckinCreate, CheckinMetrics, CheckinResponse, YesterdayCheckinResponse
from .profile import BirthData, LocationData, ProfileRead, ProfileWrite
from .horary import (
    HoraryAnswerRead,
    HoraryQuestionCreate,
    HoraryQuestionRead,
    HoraryQuotaRead,
)
from .natal import NatalPayload
from .scoring_v2 import ScoringV2Result
from .today import ConvergenceEvidence, TodayPayload


# START_BLOCK: PUBLIC_ROOTS
PUBLIC_CONTRACT_ROOTS: tuple[type[CamelModel], ...] = (
    AccessSummary,
    ActivationLayer,
    AuthError,
    AuthSession,
    BirthData,
    CalendarPayload,
    CheckinCreate,
    CheckinMetrics,
    CheckinResponse,
    ConvergenceEvidence,
    HoraryAnswerRead,
    HoraryQuestionCreate,
    HoraryQuestionRead,
    HoraryQuotaRead,
    LocationData,
    NatalPayload,
    ProfileRead,
    ProfileWrite,
    ScoringV2Result,
    TelegramAuthRequest,
    TodayPayload,
    YesterdayCheckinResponse,
)
# END_BLOCK: PUBLIC_ROOTS


# START_BLOCK: REGISTRY_VALIDATION
def _registry_error(index: int, name: str, reason: str, error_type: type[Exception]) -> Exception:
    # START_FUNCTION_CONTRACT: F-M-CONTRACT-REGISTRY._registry_error
    # purpose: Build a deterministic registry validation exception.
    # inputs: index/name/reason metadata and the concrete exception type.
    # returns: Exception instance with no schema payload data.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACT-REGISTRY._registry_error
    return error_type(f"index={index} name={name} reason={reason}")


def _schema_title(root: type[CamelModel], index: int, name: str) -> str:
    # START_FUNCTION_CONTRACT: F-M-CONTRACT-REGISTRY._schema_title
    # purpose: Resolve a root model JSON schema title for duplicate-title guarding.
    # inputs: root model plus deterministic error metadata.
    # returns: Non-empty JSON schema title.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: Raises ValueError with index/name/reason on missing title.
    # END_FUNCTION_CONTRACT: F-M-CONTRACT-REGISTRY._schema_title
    try:
        title = root.model_json_schema().get("title")
    except Exception as exc:  # pragma: no cover - defensive guard, should not happen for CamelModel
        raise _registry_error(index, name, "schema-title-unavailable", ValueError) from exc
    if not isinstance(title, str) or not title:
        raise _registry_error(index, name, "schema-title-missing", ValueError)
    return title


def validate_public_contract_roots(
    roots: tuple[type[CamelModel], ...] = PUBLIC_CONTRACT_ROOTS,
) -> tuple[type[CamelModel], ...]:
    # START_FUNCTION_CONTRACT: F-M-CONTRACT-REGISTRY.validate_public_contract_roots
    # purpose: Validate the public contract root registry before OpenAPI export.
    # inputs: roots — tuple of candidate Pydantic API root classes.
    # returns: The same tuple object when validation succeeds.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: Raises deterministic TypeError/ValueError with index/name/reason only.
    # END_FUNCTION_CONTRACT: F-M-CONTRACT-REGISTRY.validate_public_contract_roots
    if not isinstance(roots, tuple):
        raise _registry_error(-1, type(roots).__name__, "not-tuple", TypeError)
    if not roots:
        raise _registry_error(-1, "<empty>", "empty", ValueError)

    names: list[str] = []
    seen_objects: dict[int, int] = {}
    seen_names: dict[str, int] = {}
    seen_titles: dict[str, int] = {}

    for index, root in enumerate(roots):
        if not inspect.isclass(root):
            raise _registry_error(index, type(root).__name__, "non-class", TypeError)

        name = root.__name__
        names.append(name)

        object_id = id(root)
        if object_id in seen_objects:
            raise _registry_error(index, name, f"duplicate-object:{seen_objects[object_id]}", ValueError)
        seen_objects[object_id] = index

        if name in seen_names:
            raise _registry_error(index, name, f"duplicate-name:{seen_names[name]}", ValueError)
        seen_names[name] = index

        if root is CamelModel:
            raise _registry_error(index, name, "camelmodel-base", TypeError)
        if root.__module__.split(".", 1)[0] == "solarsage_contracts":
            raise _registry_error(index, name, "shared-module-root", TypeError)
        if name.endswith("Contract"):
            raise _registry_error(index, name, "shared-contract-suffix", TypeError)
        if not issubclass(root, CamelModel):
            raise _registry_error(index, name, "non-camelmodel-subclass", TypeError)

        title = _schema_title(root, index, name)
        if title in seen_titles:
            raise _registry_error(index, name, f"duplicate-schema-title:{seen_titles[title]}", ValueError)
        seen_titles[title] = index

    if names != sorted(names):
        raise _registry_error(-1, ",".join(names), "unsorted", ValueError)

    return roots
# END_BLOCK: REGISTRY_VALIDATION


__all__ = ["PUBLIC_CONTRACT_ROOTS", "validate_public_contract_roots"]
