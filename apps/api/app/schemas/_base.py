# AI_HEADER
# module: M-CONTRACTS._base
# canon: docs/GRACE_CANON.md §6 (Backend → Frontend Contract boundary)
# wave: W-1.1B (Option B — Pydantic is source of truth)
# purpose: Common Pydantic v2 base for every public API schema. Enforces
#          camelCase wire-format and strict validation (extra=forbid) so the
#          generated openapi.json round-trips losslessly into TypeScript.

# START_MODULE_CONTRACT: M-CONTRACTS._base
# purpose: Provide CamelModel — the single ConfigDict every schema in
#          apps/api/app/schemas/* inherits from.
# invariants:
#   - extra=forbid: unknown keys at the wire boundary are a hard error,
#     so divergence between Pydantic and the generated TS surfaces as a
#     validation failure in tests, not as a silent passthrough.
#   - alias_generator=to_camel + populate_by_name=True: Python attributes
#     stay snake_case; the JSON wire stays camelCase; both names accepted
#     on input.
#   - by-alias serialization is the default everywhere we emit responses
#     (callers use .model_dump(by_alias=True) or response_model handling).
# emits: nothing (pure config).
# consumes: pydantic.BaseModel, pydantic.alias_generators.to_camel.
# END_MODULE_CONTRACT

# START_MODULE_MAP: M-CONTRACTS._base
# - CamelModel: BaseModel subclass with shared ConfigDict for all schemas.
# END_MODULE_MAP

# START_BLOCK: CAMEL_MODEL_BASE
from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base for every public API schema.

    See module contract above for the full set of invariants. Subclasses
    MUST NOT override `model_config` — extend it via `model_config = {**CamelModel.model_config, ...}`
    if a field-level escape hatch is ever required (currently: never).
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        alias_generator=to_camel,
        str_strip_whitespace=False,
        frozen=False,
    )
# END_BLOCK: CAMEL_MODEL_BASE
