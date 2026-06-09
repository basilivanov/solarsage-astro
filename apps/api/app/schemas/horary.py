# ############################################################################
# AI_HEADER: MODULE_HORARY_SCHEMAS
# ROLE: Pydantic v2 schemas for horary request/response payload structures.
# DEPENDENCIES: pydantic, app.schemas._base.CamelModel
# GRACE_ANCHORS: [BLOCKS, PAYLOADS]
# ############################################################################

# START_MODULE_CONTRACT: M-CONTRACTS.horary
# purpose: Pydantic wire payload definitions for GET /api/horary/quota, GET/POST questions.
# owns:
#   - apps/api/app/schemas/horary.py
# inputs:
#   - none
# outputs:
#   - HoraryQuestionCreate, HoraryQuestionRead, HoraryQuotaRead
# invariants:
#   - all schemas inherit from CamelModel for camelCase JSON translation.
#   - Text length constraints (5-500 chars) are enforced on input questions.
# END_MODULE_CONTRACT: M-CONTRACTS.horary

# START_MODULE_MAP: M-CONTRACTS.horary
# public_entrypoints:
#   - HoraryQuestionCreate
#   - HoraryQuestionRead
#   - HoraryQuotaRead
# END_MODULE_MAP: M-CONTRACTS.horary

from __future__ import annotations

from typing import Annotated, Literal
from pydantic import Field, field_validator
from ._base import CamelModel


class ParagraphBlock(CamelModel):
    type: Literal["paragraph"] = "paragraph"
    text: str


class LeadBlock(CamelModel):
    type: Literal["lead"] = "lead"
    text: str


class HeadingBlock(CamelModel):
    type: Literal["heading"] = "heading"
    level: Literal[2, 3]
    text: str


class ListBlock(CamelModel):
    type: Literal["list"] = "list"
    style: Literal["bullet", "check"] | None = None
    items: list[str]


class CalloutBlock(CamelModel):
    type: Literal["callout"] = "callout"
    tone: Literal["neutral", "strength", "risk", "insight"] | None = None
    title: str | None = None
    text: str


class ProsConsBlock(CamelModel):
    type: Literal["pros_cons"] = "pros_cons"
    pros_label: str | None = None
    cons_label: str | None = None
    pros: list[str] | None = None
    cons: list[str] | None = None


class DividerBlock(CamelModel):
    type: Literal["divider"] = "divider"


class QuoteBlock(CamelModel):
    type: Literal["quote"] = "quote"
    text: str
    source: str | None = None


# ---- Хорарные блоки (НОВЫЕ) ----


class VerdictCardBlock(CamelModel):
    """Крупная карточка вердикта: да/нет/возможно + label уверенности.

    Per W-HORARY-ANSWER-QUALITY-V1 §3.1–3.2 confidence here is shown as
    a human label (low/medium/high), NOT as a probability percentage.
    """

    type: Literal["verdict_card"] = "verdict_card"
    verdict: Literal["yes", "no", "maybe"]
    confidence: float  # 0.0–1.0 (internal/debug; UI shows the label)
    label: str | None = None  # Короткий текст рядом с вердиктом
    confidence_label: Literal["low", "medium", "high"]
    confidence_explanation: str

    @field_validator("confidence")
    @classmethod
    def _validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v


class TestimonyItem(CamelModel):
    title: str
    explanation: str
    weight: float
    planets: list[str] = Field(default_factory=list)
    aspect_type: str | None = None
    orb: float | None = None


class TestimoniesBlock(CamelModel):
    """Свидетельства «за», «против» и нейтральные факторы."""

    type: Literal["testimonies"] = "testimonies"
    pros_label: str = "Свидетельства «за»"
    cons_label: str = "Свидетельства «против»"
    neutral_label: str = "Нейтральные факторы"
    pros: list[TestimonyItem] = Field(default_factory=list)
    cons: list[TestimonyItem] = Field(default_factory=list)
    neutral: list[TestimonyItem] = Field(default_factory=list)


class TimingBlock(CamelModel):
    """Блок со сроками реализации.

    status="known"            — есть выраженный срок, time_range обязателен.
    status="unclear"          — карта не даёт точного срока, time_range
                                опционален (типовая оценка по категории).
    status="not_enough_evidence" — срок не выражен и не выводится, time_range=None.
    """

    type: Literal["timing"] = "timing"
    status: Literal["known", "unclear", "not_enough_evidence"]
    time_range: str | None = None
    text: str


HoraryBlock = Annotated[
    ParagraphBlock
    | LeadBlock
    | HeadingBlock
    | ListBlock
    | CalloutBlock
    | ProsConsBlock
    | DividerBlock
    | QuoteBlock
    | VerdictCardBlock
    | TestimoniesBlock
    | TimingBlock,
    Field(discriminator="type"),
]


# ---- Request/Response схемы ----


class HoraryQuestionCreate(CamelModel):
    text: str = Field(..., min_length=5, max_length=500)
    category: Literal["love", "career", "money", "health", "travel", "other"] | None = None
    client_timezone: str = Field(..., max_length=100)
    client_local_time: str | None = None
    question_lat: float | None = None
    question_lon: float | None = None
    question_location_name: str | None = None
    idempotency_key: str = Field(..., min_length=1, max_length=255)


class HoraryAnswerRead(CamelModel):
    verdict: Literal["yes", "no", "maybe"]
    confidence: float
    confidence_label: Literal["low", "medium", "high"] = "medium"
    confidence_explanation: str = ""
    blocks: list[HoraryBlock]
    planets: list[str]
    generated_at: str


class HoraryQuestionRead(CamelModel):
    id: str
    text: str
    category: str | None
    status: Literal["pending", "processing", "answered", "failed", "refunded", "expired"]
    spent_credit_source: Literal["subscription_weekly_free", "referral_bonus", "gift", "paid", "adjustment"] | None = None
    credit_refunded: bool = False
    client_timezone: str
    client_local_time: str | None
    question_location_name: str | None = None
    created_at: str
    answer: HoraryAnswerRead | None = None


class HoraryQuotaRead(CamelModel):
    weekly_free_available: bool
    weekly_free_expires_at: str | None = None
    next_weekly_free_at: str | None = None
    bonus_credits: int
    paid_credits: int
    can_purchase: bool = True
