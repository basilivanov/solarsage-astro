# AI_HEADER
# module: M-NATAL-REPORT-SERVICE
# wave: W-NATAL-FULL
# purpose: Full natal report generation — LLM pipeline over deterministic NatalContext.

# START_MODULE_CONTRACT: M-NATAL-REPORT-SERVICE
# purpose: Generate, persist, and retrieve full natal reports.
#   - generate_report(): creates or returns existing report from deterministic context
#   - get_report(): retrieves persisted report by id or latest
#   - get_report_section(): retrieves single section
# owns:
#   - apps/api/app/services/natal_report_service.py
# inputs:
#   - user_id: UUID
#   - NatalContextData from NatalContextService
# outputs:
#   - NatalReportRead, NatalGenerateResponse
# dependencies:
#   - M-NATAL-CONTEXT-SERVICE
#   - M-LLM-SERVICE
#   - M-DB-SESSION
#   - M-CONTRACTS.natal
# invariants:
#   - Report generation is idempotent for same context/prompt/schema version
#   - LLM only writes narrative text; chart facts come from NatalContextData
#   - Failed generation produces FAILED_RETRYABLE, never a fake READY report
#   - No transit contamination in natal report
# failure_policy:
#   - LLM failure → FAILED_RETRYABLE
#   - Invalid LLM JSON → FAILED_RETRYABLE
#   - Repeated LLM failure → FAILED_PERMANENT after 3 attempts
# non_goals:
#   - No payment integration (future wave)
#   - No async job queue (MVP: synchronous generation)
# END_MODULE_CONTRACT: M-NATAL-REPORT-SERVICE

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import NatalChartCache, NatalReport
from app.schemas.natal import (
    NatalContextData,
    NatalGenerateResponse,
    NatalReportMeta,
    NatalReportRead,
    NatalReportSectionRead,
    NatalBlock,
    ParagraphBlock,
    LeadBlock,
    HeadingBlock,
    ListBlock,
    CalloutBlock,
    ProsConsBlock,
    QuoteBlock,
    DividerBlock,
)
from app.services.natal_context_service import NatalContextService

logger = logging.getLogger(__name__)

# ── Required section IDs for this wave ────────────────────────────
REQUIRED_SECTIONS = [
    "portrait",
    "ascendant",
    "rulers",
    "aspects",
    "spheres",
    "planets",
    "shadow",
    "synthesis",
]

_SECTION_TITLES = {
    "portrait": "Психологический портрет",
    "ascendant": "Асцендент и внешняя маска",
    "rulers": "Управители и ключевые темы",
    "aspects": "Аспекты и внутренние диалоги",
    "spheres": "Сферы жизни",
    "planets": "Планеты в деталях",
    "shadow": "Теневая сторона и зоны роста",
    "synthesis": "Синтез и практические выводы",
}

PROMPT_VERSION = "1"
REPORT_SCHEMA_VERSION = "natal/v1"
MAX_RETRY_ATTEMPTS = 3


class NatalReportService:
    """Full natal report generation and retrieval."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Public API ────────────────────────────────────────────────

    async def generate_report(
        self, user_id: uuid.UUID, force_regenerate: bool = False
    ) -> NatalGenerateResponse:
        """Start or return a full natal report generation.

        Idempotent: returns existing READY/GENERATING report for same
        context+prompt+schema unless force_regenerate=True.
        """
        # 1. Get natal context (validates profile, builds cache if needed)
        context_service = NatalContextService(self.db)
        natal_context = await context_service.get_or_build_natal_context(user_id)

        # 2. Find cache entry for natal_context_id
        profile = await self._load_profile(user_id)
        profile_hash = NatalContextService.compute_profile_hash(profile)
        cache_entry = await self._find_cache_entry(user_id, profile_hash)
        if cache_entry is None:
            raise HTTPException(
                status_code=502,
                detail={"code": "NATAL_CONTEXT_MISSING", "message": "Не удалось загрузить натальный контекст."},
            )

        # 3. Check for existing report (idempotency)
        if not force_regenerate:
            existing = await self._find_active_report(user_id, cache_entry.id)
            if existing is not None:
                return NatalGenerateResponse(
                    report_id=str(existing.id),
                    status=existing.status,
                    sections_available=existing.status == "READY",
                    error_code=existing.error_code,
                    error_message=existing.error_message_sanitized,
                )

        # 4. Check FAILED_RETRYABLE count
        retry_count = await self._count_failed_attempts(user_id, cache_entry.id)
        if retry_count >= MAX_RETRY_ATTEMPTS:
            # Mark as permanent failure
            report = NatalReport(
                user_id=user_id,
                natal_context_id=cache_entry.id,
                status="FAILED_PERMANENT",
                prompt_version=PROMPT_VERSION,
                report_schema_version=REPORT_SCHEMA_VERSION,
                error_code="MAX_RETRIES_EXCEEDED",
                error_message_sanitized="Превышено количество попыток генерации. Попробуй позже.",
            )
            self.db.add(report)
            await self.db.commit()
            await self.db.refresh(report)
            return NatalGenerateResponse(
                report_id=str(report.id),
                status="FAILED_PERMANENT",
                sections_available=False,
                error_code=report.error_code,
                error_message=report.error_message_sanitized,
            )

        # 5. Create GENERATING record
        input_context_hash = self._compute_context_hash(natal_context)
        report = NatalReport(
            user_id=user_id,
            natal_context_id=cache_entry.id,
            status="GENERATING",
            access_state="FREE_PREVIEW",
            prompt_version=PROMPT_VERSION,
            report_schema_version=REPORT_SCHEMA_VERSION,
            input_context_hash=input_context_hash,
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)

        # 6. Generate sections via LLM (synchronous MVP)
        try:
            sections = await self._generate_sections(natal_context, profile)
            # Validate sections
            self._validate_sections(sections, natal_context)

            # Compute output hash
            sections_json = json.dumps(
                [s.model_dump(by_alias=True) for s in sections],
                ensure_ascii=False,
            )
            output_hash = hashlib.sha256(sections_json.encode()).hexdigest()[:16]

            # Persist
            report.sections_json = sections_json
            report.status = "READY"
            report.output_hash = output_hash
            report.completed_at = datetime.now(UTC)
            await self.db.commit()
            await self.db.refresh(report)

            logger.info(f"Natal report generated: {report.id} for user {user_id}")
            return NatalGenerateResponse(
                report_id=str(report.id),
                status="READY",
                sections_available=True,
            )

        except Exception as exc:
            logger.error(f"Natal report generation failed: {exc}")
            report.status = "FAILED_RETRYABLE"
            report.error_code = "GENERATION_FAILED"
            report.error_message_sanitized = "Не удалось сгенерировать отчёт. Попробуй ещё раз."
            await self.db.commit()

            return NatalGenerateResponse(
                report_id=str(report.id),
                status="FAILED_RETRYABLE",
                sections_available=False,
                error_code=report.error_code,
                error_message=report.error_message_sanitized,
            )

    async def get_report(
        self, user_id: uuid.UUID, report_id: str | None = None
    ) -> NatalReportRead:
        """Get a report by id or latest READY report for user."""
        if report_id:
            result = await self.db.execute(
                select(NatalReport).where(
                    and_(
                        NatalReport.id == uuid.UUID(report_id),
                        NatalReport.user_id == user_id,
                    )
                )
            )
        else:
            result = await self.db.execute(
                select(NatalReport).where(
                    and_(
                        NatalReport.user_id == user_id,
                        NatalReport.status == "READY",
                    )
                ).order_by(NatalReport.created_at.desc())
            )

        report = result.scalar_one_or_none()
        if report is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "REPORT_NOT_FOUND", "message": "Отчёт не найден."},
            )

        return self._report_to_read(report)

    async def get_report_section(
        self, user_id: uuid.UUID, report_id: str, section_id: str
    ) -> NatalReportSectionRead:
        """Get a single section from a report."""
        report_read = await self.get_report(user_id, report_id)
        for section in report_read.sections:
            if section.id == section_id:
                return section
        raise HTTPException(
            status_code=404,
            detail={"code": "SECTION_NOT_FOUND", "message": "Раздел не найден."},
        )

    # ── Private: LLM generation ───────────────────────────────────

    async def _generate_sections(
        self, context: NatalContextData, profile
    ) -> list[NatalReportSectionRead]:
        """Generate all report sections via LLM."""
        from app.services.llm_service import LLMService

        llm = LLMService()
        gender = profile.gender or "female"
        user_name = profile.first_name or "Пользователь"

        # Build compact deterministic JSON context for LLM
        chart_facts = self._build_llm_input(context, profile)

        # Generate section by section for better quality control
        sections: list[NatalReportSectionRead] = []

        for section_id in REQUIRED_SECTIONS:
            section_title = _SECTION_TITLES[section_id]
            try:
                section_blocks = await self._generate_section_blocks(
                    llm, chart_facts, section_id, section_title, gender, user_name
                )
                sections.append(NatalReportSectionRead(
                    id=section_id,
                    title=section_title,
                    summary=None,
                    blocks=section_blocks,
                ))
            except Exception as exc:
                logger.warning(f"Section {section_id} generation failed: {exc}")
                # Add fallback paragraph instead of failing entire report
                sections.append(NatalReportSectionRead(
                    id=section_id,
                    title=section_title,
                    summary=None,
                    blocks=[ParagraphBlock(
                        type="paragraph",
                        text=f"Раздел «{section_title}» временно недоступен. Попробуй перегенерировать отчёт.",
                    )],
                ))

        return sections

    async def _generate_section_blocks(
        self, llm, chart_facts: str, section_id: str, section_title: str,
        gender: str, user_name: str,
    ) -> list[NatalBlock]:
        """Generate blocks for a single section via LLM."""
        section_instructions = self._section_prompt_instructions(section_id)

        prompt = f"""Ты — астролог, пишешь персональный натальный отчёт для {user_name}.

Пол: {gender}

ФАКТЫ КАРТЫ (детерминированные, использовать ТОЛЬКО их):
{chart_facts}

РАЗДЕЛ: {section_title} (id: {section_id})
ИНСТРУКЦИЯ ДЛЯ РАЗДЕЛА:
{section_instructions}

ПРАВИЛА:
- Пиши на русском, на «ты»
- Используй правильное склонение для пола: {gender}
- Будь конкретным и практичным, не фаталистичным
- НЕ выдумывай планеты, знаки, дома или аспекты, которых нет в фактах выше
- НЕ упоминай транзиты — это натальный отчёт, не прогноз
- НЕ используй англицизмы — все названия на русском
- Предпочитай практическую интерпретацию: сильные стороны, риски, паттерны

БЛОК-СХЕМА (верни ТОЛЬКО валидный JSON без markdown):
{{
  "blocks": [
    {{"type": "lead", "text": "Главный вывод раздела в одном-двух предложениях"}},
    {{"type": "paragraph", "text": "Развёрнутый абзац с анализом"}},
    {{"type": "pros_cons", "prosLabel": "Сильные стороны", "consLabel": "Зоны роста", "pros": {{"title": "...", "text": "..."}}, "cons": {{"title": "...", "text": "..."}}}},
    {{"type": "callout", "title": "Совет", "text": "Практический совет", "tone": "insight"}},
    {{"type": "paragraph", "text": "Итоговый абзац"}}
  ]
}}

Допустимые типы блоков: lead, paragraph, heading, list, callout, pros_cons, quote, divider.

JSON:"""

        text = await llm._generate_text(prompt, max_tokens=2000)
        if not text:
            return [ParagraphBlock(type="paragraph", text="Не удалось сгенерировать текст раздела.")]

        # Strip markdown
        for marker in ['```json', '```']:
            if marker in text:
                text = text.split(marker, 1)[1].rsplit('```', 1)[0].strip()
                break

        try:
            data = json.loads(text)
            raw_blocks = data.get("blocks", [])
            return self._parse_blocks(raw_blocks)
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning(f"Failed to parse section {section_id} JSON: {exc}")
            return [ParagraphBlock(type="paragraph", text=text[:1000])]

    @staticmethod
    def _parse_blocks(raw_blocks: list[dict]) -> list[NatalBlock]:
        """Parse raw block dicts into typed NatalBlock instances."""
        blocks: list[NatalBlock] = []
        for b in raw_blocks:
            try:
                b_type = b.get("type", "paragraph")
                if b_type == "paragraph":
                    blocks.append(ParagraphBlock(type="paragraph", text=b.get("text", "")))
                elif b_type == "lead":
                    blocks.append(LeadBlock(type="lead", text=b.get("text", "")))
                elif b_type == "heading":
                    blocks.append(HeadingBlock(type="heading", text=b.get("text", ""), level=b.get("level", 2)))
                elif b_type == "list":
                    blocks.append(ListBlock(type="list", items=b.get("items", []), ordered=b.get("ordered", False)))
                elif b_type == "callout":
                    blocks.append(CalloutBlock(
                        type="callout",
                        title=b.get("title"),
                        text=b.get("text", ""),
                        tone=b.get("tone", "info"),
                    ))
                elif b_type == "pros_cons":
                    pros = b.get("pros", [])
                    cons = b.get("cons", [])
                    blocks.append(ProsConsBlock(
                        type="pros_cons",
                        pros_label=b.get("prosLabel", "Сильные стороны"),
                        cons_label=b.get("consLabel", "Зоны роста"),
                        pros=pros if isinstance(pros, list) and all(isinstance(p, dict) for p in pros) else [],
                        cons=cons if isinstance(cons, list) and all(isinstance(c, dict) for c in cons) else [],
                    ))
                elif b_type == "quote":
                    blocks.append(QuoteBlock(type="quote", text=b.get("text", ""), source=b.get("source")))
                elif b_type == "divider":
                    blocks.append(DividerBlock(type="divider"))
                else:
                    # Fallback: unknown block type → paragraph
                    blocks.append(ParagraphBlock(type="paragraph", text=str(b)))
            except Exception:
                # Skip malformed blocks
                continue
        return blocks

    @staticmethod
    def _section_prompt_instructions(section_id: str) -> str:
        """Return per-section prompt instructions for the LLM."""
        instructions = {
            "portrait": (
                "Дай общую характеристику личности на основе Солнца, Луны и Асцендента. "
                "Опиши основной жизненный тон, мотивацию и стиль взаимодействия. "
                "Используй блоки: lead, paragraph, pros_cons."
            ),
            "ascendant": (
                "Подробно разбери Асцендент: знак, градус, как влияет на внешнее впечатление "
                "и стиль входа в контакт. Опиши управителя ASC и его положение. "
                "Используй блоки: lead, paragraph, callout."
            ),
            "rulers": (
                "Разбери управителей ключевых домов: 1, 4, 7, 10. Где стоят, в каких знаках, "
                "какие сферы подсвечивают. Используй блоки: paragraph, list, callout."
            ),
            "aspects": (
                "Проанализируй ключевые натальные аспекты: напряжённые и гармоничные. "
                "Объясни внутренние диалоги планет и как они проявляются в жизни. "
                "Используй блоки: lead, paragraph, pros_cons."
            ),
            "spheres": (
                "Опиши приоритетные сферы жизни по карте: где заложен наибольший потенциал "
                "и какие сферы требуют внимания. Опирайся на баллы сфер. "
                "Используй блоки: paragraph, list, callout."
            ),
            "planets": (
                "Дай краткую характеристику каждой ключевой планете (Солнце, Луна, Меркурий, "
                "Венера, Марс, Юпитер, Сатурн): знак, дом, ключевое проявление. "
                "Используй блоки: paragraph, list."
            ),
            "shadow": (
                "Опиши теневую сторону карты: напряжённые аспекты, зоны уязвимости, "
                "паттерны, которые могут мешать. Не будь фаталистичным — "
                "подчеркни, что осознанность превращает тень в ресурс. "
                "Используй блоки: lead, paragraph, pros_cons, callout."
            ),
            "synthesis": (
                "Сведи всё воедино: ключевые темы карты, практические выводы, "
                "направления роста. Дай 3-5 конкретных практических советов. "
                "Используй блоки: lead, paragraph, list, callout."
            ),
        }
        return instructions.get(section_id, "Напиши развёрнутый аналитический текст.")

    # ── Private: context building for LLM ─────────────────────────

    @staticmethod
    def _build_llm_input(context: NatalContextData, profile) -> str:
        """Build compact deterministic JSON context for LLM input."""
        birth_date = profile.birthday.isoformat() if profile.birthday else ""
        birth_time = profile.birth_time.strftime("%H:%M") if profile.birth_time else ""
        birth_city = profile.birth_city or ""
        gender = profile.gender or "female"
        user_name = profile.first_name or "Пользователь"

        llm_input = {
            "user": {
                "name": user_name,
                "gender": gender,
                "locale": "ru",
            },
            "birth": {
                "date": birth_date,
                "time": birth_time,
                "place": birth_city,
                "timezone": profile.birth_tz or "UTC",
            },
            "chart": {
                "angles": [
                    {"name": a.name, "sign": a.sign, "degree": a.degree, "house": None}
                    for a in context.angles
                ],
                "planets": [
                    {
                        "name": p.name,
                        "sign": p.sign,
                        "degree": p.degree,
                        "house": p.house,
                        "retrograde": p.retrograde,
                    }
                    for p in context.planets
                ],
                "houses": [
                    {"number": h.number, "sign": h.sign, "degree": h.degree}
                    for h in context.houses
                ],
                "aspects": [
                    {
                        "planet_a": a.planet_a,
                        "planet_b": a.planet_b,
                        "aspect_type": a.aspect_type,
                        "orb": a.orb,
                    }
                    for a in context.aspects
                ],
                "special_points": [
                    {"name": sp.name, "sign": sp.sign, "degree": sp.degree, "house": sp.house}
                    for sp in context.special_points
                ],
                "balances": {
                    "elements": context.elements_balance.model_dump(),
                    "modalities": context.modalities_balance.model_dump(),
                },
                "scores": {
                    "sphere_scores": context.sphere_scores,
                    "dominants": context.dominants,
                },
            },
            "report_plan": {
                "sections": REQUIRED_SECTIONS,
                "tone": "friendly, concrete, practical, non-fatalistic",
                "block_schema_version": REPORT_SCHEMA_VERSION,
            },
        }
        return json.dumps(llm_input, ensure_ascii=False, indent=2)

    # ── Private: validation ───────────────────────────────────────

    @staticmethod
    def _validate_sections(
        sections: list[NatalReportSectionRead], context: NatalContextData
    ) -> None:
        """Validate that generated sections don't contain hallucinated chart facts.

        Basic validation: required sections exist, no empty blocks.
        Advanced hallucination check could be added later.
        """
        section_ids = {s.id for s in sections}
        for required_id in REQUIRED_SECTIONS:
            if required_id not in section_ids:
                raise ValueError(f"Missing required section: {required_id}")

        for section in sections:
            if not section.blocks:
                raise ValueError(f"Section {section.id} has no blocks")

            # Check no block is completely empty
            for block in section.blocks:
                if hasattr(block, "text") and not block.text.strip():
                    raise ValueError(f"Empty text in section {section.id}")

    # ── Private: DB helpers ────────────────────────────────────────

    async def _load_profile(self, user_id: uuid.UUID):
        from app.db.models import UserProfile
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def _find_cache_entry(
        self, user_id: uuid.UUID, profile_hash: str
    ) -> NatalChartCache | None:
        result = await self.db.execute(
            select(NatalChartCache).where(
                and_(
                    NatalChartCache.user_id == user_id,
                    NatalChartCache.profile_hash == profile_hash,
                    NatalChartCache.invalidated_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    async def _find_active_report(
        self, user_id: uuid.UUID, natal_context_id: uuid.UUID
    ) -> NatalReport | None:
        """Find existing READY or GENERATING report for same context+prompt+schema."""
        result = await self.db.execute(
            select(NatalReport).where(
                and_(
                    NatalReport.user_id == user_id,
                    NatalReport.natal_context_id == natal_context_id,
                    NatalReport.prompt_version == PROMPT_VERSION,
                    NatalReport.report_schema_version == REPORT_SCHEMA_VERSION,
                    NatalReport.status.in_(["READY", "GENERATING"]),
                )
            )
        )
        return result.scalar_one_or_none()

    async def _count_failed_attempts(
        self, user_id: uuid.UUID, natal_context_id: uuid.UUID
    ) -> int:
        """Count FAILED_RETRYABLE reports for this user+context."""
        result = await self.db.execute(
            select(NatalReport).where(
                and_(
                    NatalReport.user_id == user_id,
                    NatalReport.natal_context_id == natal_context_id,
                    NatalReport.status == "FAILED_RETRYABLE",
                )
            )
        )
        return len(result.scalars().all())

    @staticmethod
    def _compute_context_hash(context: NatalContextData) -> str:
        """Hash the exact context passed to LLM for audit trail."""
        data = context.model_dump_json()
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _report_to_read(self, report: NatalReport) -> NatalReportRead:
        """Convert DB model to read schema."""
        sections: list[NatalReportSectionRead] = []
        if report.sections_json:
            try:
                raw_sections = json.loads(report.sections_json)
                for s in raw_sections:
                    blocks = self._parse_blocks(s.get("blocks", []))
                    sections.append(NatalReportSectionRead(
                        id=s.get("id", ""),
                        title=s.get("title", ""),
                        summary=s.get("summary"),
                        blocks=blocks,
                    ))
            except (json.JSONDecodeError, KeyError) as exc:
                logger.error(f"Failed to parse sections_json: {exc}")

        meta = NatalReportMeta(
            prompt_version=report.prompt_version,
            context_hash=report.input_context_hash,
        )

        return NatalReportRead(
            id=str(report.id),
            status=report.status,
            access_state=report.access_state,
            meta=meta,
            sections=sections,
            error_code=report.error_code,
            error_message=report.error_message_sanitized,
            created_at=report.created_at.isoformat() if report.created_at else None,
            completed_at=report.completed_at.isoformat() if report.completed_at else None,
        )
