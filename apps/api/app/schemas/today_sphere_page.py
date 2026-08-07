# ############################################################################
# AI_HEADER: MODULE_SCHEMAS_TODAY-SPHERE-PAGE — static sphere page wire contract.
# ROLE: Defines the deterministic period layer and claim-bound natal narrative
#   projection returned by GET /api/spheres/{key}.
# ############################################################################

# START_MODULE_CONTRACT: M-SCHEMAS-TODAY-SPHERE-PAGE
# purpose: Define the strict public payload for one canonical static sphere page.
# owns:
#   - apps/api/app/schemas/today_sphere_page.py
# inputs: validated natal paragraphs, birth-time capability, and period items.
# outputs: camelCase TodaySpherePagePayload and nested public models.
# dependencies: CamelModel and Today convergence canonical enums.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - natal paragraphs are either ready with non-empty bound source ids or
#     unavailable with null paragraphs;
#   - period items carry only the four approved long-period techniques;
#   - the payload exposes housesAvailable so bucket/unknown birth time stays
#     honest at the wire boundary;
#   - periodUnavailable is explicit and never represented as a fake empty hash.
# failure_policy: Pydantic rejects malformed enums, dates, claims, and extras.
# END_MODULE_CONTRACT: M-SCHEMAS-TODAY-SPHERE-PAGE

# START_MODULE_MAP: M-SCHEMAS-TODAY-SPHERE-PAGE
# public_entrypoints:
#   - TodaySphereNatalParagraph
#   - TodaySphereNatalContent
#   - TodaySphereNatal
#   - TodaySpherePeriodItem
#   - TodaySpherePagePayload
# semantic_blocks:
#   - NATAL_WIRE: claim-bound natal narrative models.
#   - PERIOD_WIRE: deterministic long-period item model.
#   - PAGE_ROOT: static sphere page root payload.
# owned_tests:
#   - apps/api/tests/test_today_sphere_page_service.py
#   - apps/api/tests/test_today_sphere_page_api.py
# END_MODULE_MAP: M-SCHEMAS-TODAY-SPHERE-PAGE

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from app.schemas._base import CamelModel
from app.schemas.today_convergence import BirthMode, CanonicalSphere


SpherePeriodTechnique = Literal[
    "annual_profection",
    "firdar_major",
    "firdar_minor",
    "solar_return",
]


# START_BLOCK: NATAL_WIRE
class TodaySphereNatalParagraph(CamelModel):
    text: str = Field(..., min_length=1)
    source_fact_ids: list[str] = Field(..., min_length=1)


class TodaySphereNatalContent(CamelModel):
    paragraphs: list[TodaySphereNatalParagraph] = Field(
        ..., min_length=1, max_length=4
    )


class TodaySphereNatal(CamelModel):
    state: Literal["ready", "unavailable"]
    paragraphs: list[TodaySphereNatalParagraph] | None = None

    @model_validator(mode="after")
    def validate_state(self) -> TodaySphereNatal:
        if self.state == "ready" and not self.paragraphs:
            raise ValueError("ready natal content requires paragraphs")
        if self.state == "unavailable" and self.paragraphs is not None:
            raise ValueError("unavailable natal content must not carry paragraphs")
        return self
# END_BLOCK: NATAL_WIRE


# START_BLOCK: PERIOD_WIRE
class TodaySpherePeriodItem(CamelModel):
    id: str = Field(..., min_length=1, max_length=64)
    technique: SpherePeriodTechnique
    title: str = Field(..., min_length=1, max_length=160)
    note: str | None = Field(default=None, max_length=600)
    active_from: date
    active_until: date

    @model_validator(mode="after")
    def validate_window(self) -> TodaySpherePeriodItem:
        if self.active_until < self.active_from:
            raise ValueError("period window is inverted")
        if "сегодня" in self.title.casefold() or "завтра" in self.title.casefold():
            raise ValueError("relative day words are forbidden in period titles")
        return self
# END_BLOCK: PERIOD_WIRE


# START_BLOCK: PAGE_ROOT
class TodaySpherePagePayload(CamelModel):
    sphere: CanonicalSphere
    birth_time_mode: BirthMode
    houses_available: bool
    natal: TodaySphereNatal
    period: list[TodaySpherePeriodItem] = Field(..., max_length=5)
    period_identity: str
    period_unavailable: bool = False
    period_synthesis: str | None = Field(default=None, max_length=600)

    @model_validator(mode="after")
    def validate_period_state(self) -> TodaySpherePagePayload:
        if self.period_unavailable and (self.period or self.period_identity):
            raise ValueError("unavailable period must be empty")
        if self.period_unavailable and self.period_synthesis is not None:
            raise ValueError("unavailable period must not carry synthesis")
        if self.birth_time_mode != "exact" and self.houses_available:
            raise ValueError("non-exact birth time cannot expose houses")
        if self.birth_time_mode == "exact" and not self.houses_available:
            raise ValueError("exact birth time must expose house capability")
        return self
# END_BLOCK: PAGE_ROOT


__all__ = [
    "SpherePeriodTechnique",
    "TodaySphereNatalParagraph",
    "TodaySphereNatalContent",
    "TodaySphereNatal",
    "TodaySpherePeriodItem",
    "TodaySpherePagePayload",
]
