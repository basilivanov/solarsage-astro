# ############################################################################
# AI_HEADER: PERSONAL_FACT_PACK_SCHEMA — frozen internal B2B1 fact provenance contracts.
# ROLE: Validates opaque, deterministic personal/sphere fact records without storing user prose or natal values.
# ############################################################################

# START_MODULE_CONTRACT: M-PERSONAL-FACT-PACK-SCHEMA
# purpose: Define strict internal fact and fact-pack models consumed by later B2B guidance only.
# owns:
#   - apps/api/app/schemas/personal_fact_pack.py
# inputs: Machine fact ids, canonical references, confidences, and selected activation ids.
# outputs: Frozen PersonalFact and PersonalFactPack models.
# dependencies: math/re stdlib, pydantic, B2B content aliases, public horizon literal aliases.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - No user-facing statement body, raw evidence/debug, profile PII, or matched natal values are modelled.
#   - Facts have bounded rounded confidence and canonical selected-anchor provenance.
# failure_policy: raises Pydantic ValidationError on impossible internal states.
# END_MODULE_CONTRACT: M-PERSONAL-FACT-PACK-SCHEMA

# START_MODULE_MAP: M-PERSONAL-FACT-PACK-SCHEMA
# public_entrypoints:
#   - PersonalFact
#   - PersonalFactPack
# semantic_blocks:
#   - PERSONAL_FACT_PACK_TYPES: internal validation primitives.
#   - PERSONAL_FACT_PACK_MODELS: frozen fact and pack contracts.
# owned_tests:
#   - apps/api/tests/test_personal_fact_pack_service.py
# END_MODULE_MAP: M-PERSONAL-FACT-PACK-SCHEMA

# START_BLOCK: PERSONAL_FACT_PACK_TYPES
from __future__ import annotations

import math
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from app.schemas.horizon_content_canon import HorizonThemeKey, PersonalFactKind
from app.schemas.today_horizons import TodayV2HorizonId, TodayV2ProductSphereKey

HORIZON_ORDER: tuple[TodayV2HorizonId, ...] = ("long", "medium", "fast")
FACT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")
STATEMENT_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
NATAL_SOURCE_RE = re.compile(r"^natal:(?:planet|house):[a-z]+$|^natal:aspect:[a-z]+:[a-z]+$")
ActivationId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]


class PersonalFactPackModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


def _ensure_unique(values: tuple[str, ...], path: str) -> None:
    # START_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SCHEMA._ensure_unique
    # purpose: Reject duplicate opaque provenance identifiers without changing their declared order.
    # inputs: values - ordered ids; path - structural error location.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError for duplicates.
    # END_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SCHEMA._ensure_unique
    if any(not value.strip() for value in values) or len(values) != len(set(values)):
        raise ValueError(f"{path}: expected unique non-blank values")


def _ensure_round6(value: float, path: str) -> None:
    # START_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SCHEMA._ensure_round6
    # purpose: Validate finite normalized fact confidence serialized at six decimals.
    # inputs: value - confidence; path - structural error location.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError for non-finite/out-of-range/unrounded values.
    # END_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SCHEMA._ensure_round6
    if not math.isfinite(value) or value < 0 or value > 1 or round(value, 6) != value:
        raise ValueError(f"{path}: expected rounded normalized value")


# END_BLOCK: PERSONAL_FACT_PACK_TYPES


# START_BLOCK: PERSONAL_FACT_PACK_MODELS
class PersonalFact(PersonalFactPackModel):
    id: str
    kind: PersonalFactKind
    statement_key: str
    confidence: float
    horizon_ids: tuple[TodayV2HorizonId, ...]
    theme_keys: tuple[HorizonThemeKey, ...]
    activation_ids: tuple[ActivationId, ...]
    natal_source_ids: tuple[str, ...]
    profile_source_ids: tuple[str, ...]
    sphere_keys: tuple[TodayV2ProductSphereKey, ...]

    @model_validator(mode="after")
    def validate_fact(self) -> "PersonalFact":
        # START_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SCHEMA.PersonalFact.validate_fact
        # purpose: Enforce opaque fact identity, canonical reference lists, and kind-specific provenance requirements.
        # inputs: self - parsed internal fact.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError for impossible fact state.
        # END_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SCHEMA.PersonalFact.validate_fact
        if not FACT_ID_RE.fullmatch(self.id) or not STATEMENT_KEY_RE.fullmatch(self.statement_key):
            raise ValueError("PersonalFact: invalid opaque id or statement key")
        _ensure_round6(self.confidence, "PersonalFact.confidence")
        if not self.horizon_ids or self.horizon_ids != tuple(
            horizon for horizon in HORIZON_ORDER if horizon in self.horizon_ids
        ):
            raise ValueError("PersonalFact.horizon_ids: expected non-empty canonical subsequence")
        for path, values in (
            ("PersonalFact.theme_keys", self.theme_keys),
            ("PersonalFact.activation_ids", self.activation_ids),
            ("PersonalFact.natal_source_ids", self.natal_source_ids),
            ("PersonalFact.profile_source_ids", self.profile_source_ids),
            ("PersonalFact.sphere_keys", self.sphere_keys),
        ):
            _ensure_unique(values, path)
        if not any((self.activation_ids, self.natal_source_ids, self.profile_source_ids, self.sphere_keys)):
            raise ValueError("PersonalFact: expected provenance")
        if self.kind in {"strength", "risk"} and not all(
            (self.natal_source_ids, self.activation_ids, self.theme_keys, self.sphere_keys)
        ):
            raise ValueError("PersonalFact: strength/risk requires natal, activation, theme, and sphere provenance")
        if self.kind in {"strength", "risk"}:
            if not self.id.startswith(f"pf:v1:{self.kind}:") or not self.statement_key.startswith(f"{self.kind}."):
                raise ValueError("PersonalFact: strength/risk id and statement kind mismatch")
            if len(self.horizon_ids) != len(self.activation_ids) or not all(
                NATAL_SOURCE_RE.fullmatch(source) for source in self.natal_source_ids
            ):
                raise ValueError("PersonalFact: invalid strength/risk provenance alignment")
        if self.kind == "sphere" and not (
            len(self.horizon_ids) == len(self.activation_ids) == len(self.sphere_keys) == 1
            and not self.natal_source_ids
            and not self.profile_source_ids
            and self.theme_keys
        ):
            raise ValueError("PersonalFact: sphere fact requires exactly one local source")
        if self.kind == "sphere":
            horizon = self.horizon_ids[0]
            sphere = self.sphere_keys[0]
            if self.id != f"pf:v1:sphere:{horizon}:{sphere}" or self.statement_key != f"sphere.active.{sphere}":
                raise ValueError("PersonalFact: sphere id or statement mismatch")
        if self.kind == "profile" and not self.profile_source_ids:
            raise ValueError("PersonalFact: profile requires profile source")
        if self.kind == "natal" and not self.natal_source_ids:
            raise ValueError("PersonalFact: natal requires natal source")
        return self


class PersonalFactPack(PersonalFactPackModel):
    schema_version: Literal["personal-fact-pack.v1"]
    selected_activation_ids: tuple[ActivationId, ActivationId, ActivationId]
    facts: tuple[PersonalFact, ...]

    @model_validator(mode="after")
    def validate_pack(self) -> "PersonalFactPack":
        # START_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SCHEMA.PersonalFactPack.validate_pack
        # purpose: Bind every fact to ordered long/medium/fast selected anchors and stable fact ordering.
        # inputs: self - parsed fact pack.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError for invalid version, ids, fact order, or non-selected provenance.
        # END_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SCHEMA.PersonalFactPack.validate_pack
        if self.schema_version != "personal-fact-pack.v1":
            raise ValueError("PersonalFactPack.schema_version: expected v1")
        _ensure_unique(self.selected_activation_ids, "PersonalFactPack.selected_activation_ids")
        if not self.facts:
            raise ValueError("PersonalFactPack.facts: expected complete selected sphere facts")
        fact_ids = tuple(fact.id for fact in self.facts)
        _ensure_unique(fact_ids, "PersonalFactPack.facts")
        if any(not set(fact.activation_ids) <= set(self.selected_activation_ids) for fact in self.facts):
            raise ValueError("PersonalFactPack: activation provenance outside selected anchors")
        saw_non_sphere = False
        last_sphere_horizon = -1
        seen_sphere_facts: set[tuple[str, str]] = set()
        selected_by_horizon = dict(zip(HORIZON_ORDER, self.selected_activation_ids, strict=True))
        for fact in self.facts:
            if fact.kind == "sphere" and saw_non_sphere:
                raise ValueError("PersonalFactPack.facts: sphere facts must precede personal facts")
            if fact.kind != "sphere":
                saw_non_sphere = True
            if fact.kind == "sphere":
                horizon = fact.horizon_ids[0]
                sphere_key = (horizon, fact.sphere_keys[0])
                horizon_index = HORIZON_ORDER.index(horizon)
                if horizon_index < last_sphere_horizon or sphere_key in seen_sphere_facts:
                    raise ValueError("PersonalFactPack.facts: invalid sphere fact order or duplicate")
                if fact.activation_ids[0] != selected_by_horizon[horizon]:
                    raise ValueError("PersonalFactPack.facts: sphere activation horizon mismatch")
                last_sphere_horizon = horizon_index
                seen_sphere_facts.add(sphere_key)
            elif fact.kind in {"strength", "risk"}:
                expected_ids = tuple(selected_by_horizon[horizon] for horizon in fact.horizon_ids)
                if fact.activation_ids != expected_ids:
                    raise ValueError("PersonalFactPack.facts: personal activation horizon mismatch")
        if {horizon for horizon, _ in seen_sphere_facts} != set(HORIZON_ORDER):
            raise ValueError("PersonalFactPack.facts: expected sphere facts for every selected horizon")
        return self


# END_BLOCK: PERSONAL_FACT_PACK_MODELS


__all__ = ["PersonalFact", "PersonalFactPack"]
