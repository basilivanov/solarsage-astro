# AI_HEADER
# module: M-CONTRACTS.horary
# wave: W-HORARY
# purpose: Horary schema definitions

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
    """Крупная карточка вердикта: да/нет/возможно + confidence."""

    type: Literal["verdict_card"] = "verdict_card"
    verdict: Literal["yes", "no", "maybe"]
    confidence: float  # 0.0–1.0
    label: str | None = None  # Короткий текст рядом с вердиктом

    @field_validator("confidence")
    @classmethod
    def _validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v


class TimingBlock(CamelModel):
    """Блок со сроками реализации."""

    type: Literal["timing"] = "timing"
    time_range: str
    text: str | None = None


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
    blocks: list[HoraryBlock]
    planets: list[str]
    generated_at: str


class HoraryQuestionRead(CamelModel):
    id: str
    text: str
    category: str | None
    status: Literal["pending", "processing", "answered", "failed", "refunded", "expired"]
    spent_credit_source: Literal["subscription_weekly_free", "referral_bonus", "gift", "paid", "adjustment"] | None = None
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
