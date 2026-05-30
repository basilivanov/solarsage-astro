# ############################################################################
# AI_HEADER: MODULE_NATAL_SERVICE
# ROLE: Natal reading service — generates structured natal reading payload.
# DEPENDENCIES: sqlalchemy, app.schemas.natal
# GRACE_ANCHORS: [NATAL_READING_GENERATION]
# WAVE: W-7.1, W-7.2
# ############################################################################

# START_MODULE_CONTRACT: M-NATAL-SERVICE
# purpose: Generate natal reading payload with sections and blocks.
#   W-7.1: Returns structured sections × blocks.
#   W-7.2: Simplified MVP version (hardcoded content).
# owns:
#   - apps/api/app/services/natal_service.py
# inputs:
#   - user_id: UUID
# outputs:
#   - NatalPayload: structured natal reading
# dependencies:
#   - M-CONTRACTS.natal
# side_effects:
#   - none (read-only)
# invariants:
#   - sections are ordered by order field
#   - blocks within sections are ordered by order field
# failure_policy:
#   - returns hardcoded content for MVP
# non_goals:
#   - no LLM integration (future wave)
#   - no database persistence (future wave)
# END_MODULE_CONTRACT: M-NATAL-SERVICE

from datetime import datetime, timezone
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.natal import (
    BulletsBlock,
    HighlightsBlock,
    HighlightItem,
    NatalMeta,
    NatalPayload,
    NatalSection,
    ParagraphBlock,
    Person,
    PersonBirth,
    QuoteBlock,
)


class NatalService:
    """Natal reading service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_natal_reading(self, user_id: uuid.UUID) -> NatalPayload:
        """
        Get natal reading for user.

        W-7.1: Returns structured sections × blocks.
        W-7.2: Simplified MVP version (hardcoded content).

        Args:
            user_id: User UUID

        Returns:
            NatalPayload with meta and sections
        """
        # TODO: Replace with real LLM-generated content
        # For MVP, return hardcoded structure

        sections = [
            NatalSection(
                id="sun",
                title="Солнце",
                icon_name="sun",
                blocks=[
                    ParagraphBlock(
                        type="paragraph",
                        text="Ваше Солнце находится в знаке Овна, что наделяет вас энергией первопроходца. Вы прирожденный лидер, который не боится брать инициативу в свои руки.",
                    ),
                    HighlightsBlock(
                        type="highlights",
                        items=[
                            HighlightItem(
                                id="sun_strength",
                                title="Сильные стороны",
                                text="Смелость, решительность, энергичность",
                                tone="positive",
                            ),
                            HighlightItem(
                                id="sun_challenge",
                                title="Вызовы",
                                text="Импульсивность, нетерпеливость",
                                tone="neutral",
                            ),
                        ],
                    ),
                ],
            ),
            NatalSection(
                id="moon",
                title="Луна",
                icon_name="moon",
                blocks=[
                    ParagraphBlock(
                        type="paragraph",
                        text="Ваша Луна находится в знаке Рака, что делает вас глубоко эмоциональным и чувствительным человеком. Вы интуитивно понимаете эмоции других людей.",
                    ),
                    BulletsBlock(
                        type="bullets",
                        items=[
                            "Сильная связь с семьей и домом",
                            "Развитая интуиция и эмпатия",
                            "Потребность в эмоциональной безопасности",
                            "Склонность к заботе о других",
                        ],
                    ),
                    QuoteBlock(
                        type="quote",
                        text="Луна в Раке — это дар глубокого понимания человеческой природы.",
                        source="Классическая астрология",
                    ),
                ],
            ),
            NatalSection(
                id="ascendant",
                title="Асцендент",
                icon_name="arrow-up",
                blocks=[
                    ParagraphBlock(
                        type="paragraph",
                        text="Ваш Асцендент находится в знаке Льва, что придает вам харизму и естественное обаяние. Вы производите яркое впечатление на окружающих.",
                    ),
                    HighlightsBlock(
                        type="highlights",
                        items=[
                            HighlightItem(
                                id="asc_appearance",
                                title="Внешнее впечатление",
                                text="Уверенность, достоинство, магнетизм",
                                tone="positive",
                            ),
                        ],
                    ),
                ],
            ),
        ]

        meta = NatalMeta(
            schema_version="natal/v1",
            contract_version=1,
            title="Натальная карта",
            subtitle="Ваш астрологический портрет",
            generated_at=datetime.now(timezone.utc).isoformat(),
            calculation_version=1,
            interpretation_version=1,
            person=Person(
                name="Пользователь",
                birth=PersonBirth(
                    date="1990-01-01",
                    time="12:00",
                    place="Москва",
                ),
            ),
        )

        return NatalPayload(meta=meta, sections=sections)
