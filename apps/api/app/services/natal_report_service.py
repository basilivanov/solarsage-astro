# AI_HEADER: MODULE_NATAL_REPORT_SERVICE
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

# START_MODULE_MAP: M-NATAL-REPORT-SERVICE
# public_entrypoints:
#   - generate_report
#   - get_report
#   - get_report_section
# semantic_blocks:
#   - REPORT_GENERATION: generate full natal report via LLM
#   - REPORT_RETRIEVAL: get report by id or latest
#   - REPORT_SECTION: get single section
# END_MODULE_MAP: M-NATAL-REPORT-SERVICE

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import NatalChartCache, NatalReport, UserProfile
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
    HighlightsBlock,
    BulletsBlock,
)
from app.services.natal_context_service import NatalContextService
from app.core.logging import log_event, log_block

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

# ── Known astrological proper nouns (for hallucination detection) ──
# These are planet names that LLM might fabricate — obviously not real
# natal planets. We don't block all unknown words, only clearly
# astrological-planet-like fabrications.
# NOTE: Chiron/Selena/Lilith are special points, not natal planets.
# They are conditionally allowed if present in the deterministic context's
# special_points list (see _check_hallucinated_planets).
_FORBIDDEN_PLANET_PATTERNS_ALWAYS = [
    "зевс", "гера", "афина", "аполлон", "артемида",
    "кронос", "немезида", "вулкан", "изида",
    "xenu", "nibiru", "pholus", "ceres", "pallas", "juno", "vesta",
    # Trans-Plutonian fabrications
    "прозерпина",
]

# Special-point names that are allowed ONLY when present in the
# deterministic context's special_points list.
# Maps Russian search terms to the English sidecar names for matching.
_SPECIAL_POINT_PATTERNS = [
    ("хирон", "chiron"),
    ("селена", "selena"),
    ("лилит", "lilith"),
]


def _check_hallucinated_planets(
    text: str,
    known_planet_names: set[str],
    allowed_special_point_names: set[str],
    section_id: str,
) -> None:
    """Check text for clearly fabricated planet names.

    This is a context-aware guard:
    - Always rejects fabricated planets (Зевс, Гера, Прозерпина, etc.).
    - Rejects special-point names (Хирон, Селена, Лилит) only if they
      are NOT in the deterministic context's special_points list.
      If the LLM input explicitly included them as special points,
      the LLM is allowed to reference them.

    known_planet_names: set of allowed planet names (from context) for future use.
    allowed_special_point_names: lowercased names from context.special_points
      that are permitted in LLM output.
    """
    text_lower = text.lower()

    # Always-forbidden fabricated planet names
    for forbidden in _FORBIDDEN_PLANET_PATTERNS_ALWAYS:
        if forbidden in text_lower:
            raise ValueError(
                f"Hallucinated planet name '{forbidden}' found in section {section_id}. "
                f"LLM must only reference planets from the provided chart context."
            )

    # Conditionally-allowed special-point names
    # The sidecar returns English names (Chiron, Selena, Lilith), but LLM
    # writes in Russian (Хирон, Селена, Лилит). We check the Russian text
    # against the English names from context.special_points.
    for ru_pattern, en_name in _SPECIAL_POINT_PATTERNS:
        if ru_pattern in text_lower and en_name not in allowed_special_point_names:
            raise ValueError(
                f"Hallucinated special point '{ru_pattern}' found in section {section_id}. "
                f"This point is not in the chart's deterministic special_points."
            )


def _iter_block_texts(block: NatalBlock):
    """Yield all human-readable text strings from a block, recursively.

    Covers every block type's text-bearing fields so hallucination
    detection scans everything, not just block.text.
    """
    if isinstance(block, ParagraphBlock | LeadBlock | HeadingBlock | QuoteBlock):
        if block.text:
            yield block.text
    elif isinstance(block, ListBlock):
        yield from (item for item in block.items if item)
    elif isinstance(block, CalloutBlock):
        if block.title:
            yield block.title
        if block.text:
            yield block.text
    elif isinstance(block, ProsConsBlock):
        for item in block.pros:
            if item.title:
                yield item.title
            if item.text:
                yield item.text
        for item in block.cons:
            if item.title:
                yield item.title
            if item.text:
                yield item.text
    elif isinstance(block, HighlightsBlock):
        for item in block.items:
            if item.title:
                yield item.title
            if item.text:
                yield item.text
    elif isinstance(block, BulletsBlock):
        yield from (item for item in block.items if item)
    # DividerBlock has no text fields


class NatalReportService:
    """Full natal report generation and retrieval."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Public API ────────────────────────────────────────────────

    async def generate_report(
        self, user_id: uuid.UUID, force_regenerate: bool = False
    ) -> NatalGenerateResponse:
        # START_FUNCTION_CONTRACT: F-M-NATAL-REPORT-SERVICE.generate_report
        # purpose: Start or return full natal report generation (idempotent).
        # inputs: user_id (UUID), force_regenerate (bool)
        # returns: NatalGenerateResponse with report_id, status, sections_available
        # side_effects: creates NatalReport rows, triggers LLM generation
        # emitted_logs: natal.report_generation_requested, natal.report_generation_succeeded, natal.report_generation_failed
        # error_behavior: HTTPException 502 on missing context, FAILED_RETRYABLE on LLM failure, FAILED_PERMANENT after MAX_RETRY_ATTEMPTS
        # END_FUNCTION_CONTRACT: F-M-NATAL-REPORT-SERVICE.generate_report
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

            with log_block(slice="W-NATAL-FULL", module="M-NATAL-REPORT-SERVICE", block="GENERATE_REPORT"):
                log_event(
                    "natal.report_generation_succeeded",
                    level="info",
                    msg=f"Natal report generated: {report.id}",
                    payload={"report_id": str(report.id)},
                )
            return NatalGenerateResponse(
                report_id=str(report.id),
                status="READY",
                sections_available=True,
            )

        except Exception as exc:
            with log_block(slice="W-NATAL-FULL", module="M-NATAL-REPORT-SERVICE", block="GENERATE_REPORT"):
                log_event(
                    "natal.report_generation_failed",
                    level="error",
                    msg=f"Natal report generation failed: {type(exc).__name__}",
                    error={
                        "kind": type(exc).__name__,
                        "message": str(exc)[:200],
                    }
                )
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
        # START_FUNCTION_CONTRACT: F-M-NATAL-REPORT-SERVICE.get_report
        # purpose: Get report by id or latest READY report for user.
        # inputs: user_id (UUID), report_id (str | None)
        # returns: NatalReportRead with sections, meta, status
        # side_effects: reads from DB
        # emitted_logs: none
        # error_behavior: HTTPException 404 if report not found
        # END_FUNCTION_CONTRACT: F-M-NATAL-REPORT-SERVICE.get_report
        """Get a report by id or latest READY report for user.

        W-NATAL-FULL Wave 4: Populates NatalReportMeta with profile data.
        """
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

        report_read = self._report_to_read(report)
        # Populate meta with profile data
        report_read.meta = await self._populate_report_meta(report, report_read.meta)
        return report_read

    async def get_report_section(
        self, user_id: uuid.UUID, report_id: str, section_id: str
    ) -> NatalReportSectionRead:
        # START_FUNCTION_CONTRACT: F-M-NATAL-REPORT-SERVICE.get_report_section
        # purpose: Get a single section from a natal report.
        # inputs: user_id (UUID), report_id (str), section_id (str)
        # returns: NatalReportSectionRead with blocks for that section
        # side_effects: reads from DB
        # emitted_logs: none
        # error_behavior: HTTPException 404 if report or section not found
        # END_FUNCTION_CONTRACT: F-M-NATAL-REPORT-SERVICE.get_report_section
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
        """Generate all report sections via LLM.

        W-NATAL-FULL Wave 4: No placeholder sections on failure.
        If any section fails, the entire generation fails with
        FAILED_RETRYABLE — never persist a partial/fake report.
        """
        from app.services.llm import LLMService

        llm = LLMService()
        gender = profile.gender or "female"
        user_name = profile.first_name or "Пользователь"

        # Build compact deterministic JSON context for LLM
        chart_facts = self._build_llm_input(context, profile)

        # Generate section by section for better quality control
        sections: list[NatalReportSectionRead] = []

        for section_id in REQUIRED_SECTIONS:
            section_title = _SECTION_TITLES[section_id]
            section_blocks = await self._generate_section_blocks(
                llm, chart_facts, section_id, section_title, gender, user_name
            )
            # W-NATAL-FULL: No placeholder sections — if LLM fails, raise.
            # The caller catches the exception and sets status=FAILED_RETRYABLE.
            if not section_blocks:
                raise ValueError(f"Section {section_id} produced no blocks")
            sections.append(NatalReportSectionRead(
                id=section_id,
                title=section_title,
                summary=None,
                blocks=section_blocks,
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
        # W-NATAL-FULL: No placeholder text — raise on LLM failure.
        # Caller catches and sets FAILED_RETRYABLE.
        if not text:
            raise ValueError(f"LLM returned empty response for section {section_id}")

        # Strip markdown
        for marker in ['```json', '```']:
            if marker in text:
                text = text.split(marker, 1)[1].rsplit('```', 1)[0].strip()
                break

        try:
            data = json.loads(text)
            raw_blocks = data.get("blocks", [])
            blocks = self._parse_blocks(raw_blocks)
            # W-NATAL-FULL: Reject empty parsed blocks — no placeholder.
            if not blocks:
                raise ValueError(f"Section {section_id}: no valid blocks parsed from LLM output")
            return blocks
        except (json.JSONDecodeError, KeyError) as exc:
            with log_block(slice="W-NATAL-FULL", module="M-NATAL-REPORT-SERVICE", block="GENERATE_SECTION"):
                log_event(
                    "llm.response_rejected",
                    level="warn",
                    msg=f"Failed to parse section {section_id} JSON: {type(exc).__name__}",
                    payload={
                        "reason": "schema_invalid",
                    }
                )
            raise ValueError(f"Section {section_id}: invalid JSON from LLM") from exc

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
                    # W-NATAL-FULL: unknown block type is a hard error.
                    # LLM must only emit the 8+2 valid block types.
                    raise ValueError(f"Unknown natal report block type: {b_type}")
            except ValueError:
                # Re-raise validation errors (unknown types, bad data)
                raise
            except Exception as exc:
                # Malformed block data — fail generation, don't silently skip
                raise ValueError(f"Malformed block data: {b}") from exc
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

        W-NATAL-FULL Wave 4: Full validation per TZ §11:
        1. Required sections exist
        2. No empty blocks
        3. Hallucinated planet names rejected (across ALL text fields)
        4. Hallucinated sign names rejected
        5. Invalid block types rejected (enforced by _parse_blocks raising)
        """
        # Build whitelists from deterministic context
        known_planets = {p.name.lower() for p in context.planets}
        known_signs = {
            "aries", "taurus", "gemini", "cancer", "leo", "virgo",
            "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
            # Russian names (LLM may use either)
            "овен", "телец", "близнецы", "рак", "лев", "дева",
            "весы", "скорпион", "стрелец", "козерог", "водолей", "рыбы",
            # Prepositional forms
            "овне", "тельце", "близнецах", "раке", "льве", "деве",
            "весах", "скорпионе", "стрельце", "козероге", "водолее", "рыбах",
        }
        known_planet_names_ru = {
            "солнце", "луна", "меркурий", "венера", "марс",
            "юпитер", "сатурн", "уран", "нептун", "плутон",
            # Instrumental case (с Солнцем, с Луной...)
            "солнцем", "луной", "меркурием", "венерой", "марсом",
            "юпитером", "сатурном", "ураном", "нептуном", "плутоном",
        }
        # All known planet names: English + Russian variants
        all_known_planet_names = known_planets | known_planet_names_ru

        # Build allowed special-point names from deterministic context.
        # LLM is allowed to reference special points that were explicitly
        # provided in the chart context.
        allowed_special_point_names = {
            sp.name.lower() for sp in context.special_points
        }

        # Fabricated sign names — signs that don't exist in standard astrology.
        # Use stem matching because Russian text uses declined forms
        # (Змееносце, Змееносцем, etc.)
        forbidden_sign_stems = ["змееносц", "ophiuchus"]

        section_ids = {s.id for s in sections}
        for required_id in REQUIRED_SECTIONS:
            if required_id not in section_ids:
                raise ValueError(f"Missing required section: {required_id}")

        valid_block_types = {
            "lead", "paragraph", "heading", "list", "callout",
            "pros_cons", "quote", "divider", "highlights", "bullets",
        }

        for section in sections:
            if not section.blocks:
                raise ValueError(f"Section {section.id} has no blocks")

            for block in section.blocks:
                # Check block type is valid
                block_type = getattr(block, "type", None)
                if block_type and block_type not in valid_block_types:
                    raise ValueError(
                        f"Invalid block type '{block_type}' in section {section.id}. "
                        f"Valid types: {valid_block_types}"
                    )

                # Check no block is completely empty (for text-bearing blocks)
                if hasattr(block, "text") and not getattr(block, "text", "").strip():
                    raise ValueError(f"Empty text in section {section.id}")

                # Hallucination check: scan ALL text fields via _iter_block_texts
                for text_fragment in _iter_block_texts(block):
                    _check_hallucinated_planets(
                        text_fragment,
                        all_known_planet_names,
                        allowed_special_point_names,
                        section.id,
                    )
                    # Sign hallucination check: reject fabricated zodiac signs
                    text_lower = text_fragment.lower()
                    for forbidden_stem in forbidden_sign_stems:
                        if forbidden_stem in text_lower:
                            raise ValueError(
                                f"Hallucinated sign name '{forbidden_stem}' found in section {section.id}. "
                                f"Only standard 12 zodiac signs are valid."
                            )

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
        """Convert DB model to read schema.

        W-NATAL-FULL Wave 4: Populate NatalReportMeta with profile data
        from the associated NatalChartCache + UserProfile.
        """
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
                with log_block(slice="W-NATAL-FULL", module="M-NATAL-REPORT-SERVICE", block="REPORT_TO_READ"):
                    log_event(
                        "system.error",
                        level="error",
                        msg=f"Failed to parse sections_json: {type(exc).__name__}",
                        error={
                            "kind": type(exc).__name__,
                            "message": str(exc)[:200],
                        }
                    )

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

    async def _populate_report_meta(
        self, report: NatalReport, meta: NatalReportMeta
    ) -> NatalReportMeta:
        """Enrich NatalReportMeta with profile data from DB.

        Called after _report_to_read to fill user_name, birth_date, etc.
        """
        try:
            # Get the natal context cache entry to find the user_id
            cache_result = await self.db.execute(
                select(NatalChartCache).where(
                    NatalChartCache.id == report.natal_context_id
                )
            )
            cache_entry = cache_result.scalar_one_or_none()
            if cache_entry:
                profile_result = await self.db.execute(
                    select(UserProfile).where(
                        UserProfile.user_id == cache_entry.user_id
                    )
                )
                profile = profile_result.scalar_one_or_none()
                if profile:
                    meta.user_name = profile.first_name
                    meta.birth_date = profile.birthday.isoformat() if profile.birthday else None
                    meta.birth_time = profile.birth_time.strftime("%H:%M") if profile.birth_time else None
                    meta.birth_place = profile.birth_city
                    meta.house_system = cache_entry.house_system
        except Exception as exc:
            with log_block(slice="W-NATAL-FULL", module="M-NATAL-REPORT-SERVICE", block="POPULATE_META"):
                log_event(
                    "system.error",
                    level="warn",
                    msg=f"Failed to populate report meta: {type(exc).__name__}",
                    error={
                        "kind": type(exc).__name__,
                        "message": str(exc)[:200],
                    }
                )
        return meta
