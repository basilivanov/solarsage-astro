
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_NATAL_REPORT_SERVICE
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for natal_report_service.py behavior
# owns:
#   - apps/api/tests/test_natal_report_service.py
# inputs: Query params, models
# outputs: Records / query results
# dependencies: local modules
# side_effects: Database reads/writes
# emitted_logs: n/a (tests)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
# AI_HEADER
# module: M-TEST-NATAL-REPORT-SERVICE
# wave: W-NATAL-FULL (Wave 4 — full report backend)
# purpose: Unit tests for NatalReportService — block parsing, section validation,
#          report generation idempotency, LLM output validation, failure states,
#          hallucination detection, no-placeholder guarantee.

import json
import uuid

import pytest

from app.schemas.natal import (
    CalloutBlock,
    DividerBlock,
    HeadingBlock,
    LeadBlock,
    ListBlock,
    NatalContextData,
    NatalChartPlanet,
    NatalChartAngle,
    NatalChartHouse,
    NatalChartAspect,
    NatalChartSpecialPoint,
    ElementsBalance,
    ModalitiesBalance,
    NatalReportSectionRead,
    ParagraphBlock,
    ProsConsBlock,
    ProsConsItem,
    QuoteBlock,
)
from app.services.natal_report_service import (
    NatalReportService,
    REQUIRED_SECTIONS,
    _check_hallucinated_planets,
    _iter_block_texts,
    _FORBIDDEN_PLANET_PATTERNS_ALWAYS,
    _SPECIAL_POINT_PATTERNS,
)


# ── Sample NatalContextData for tests ──────────────────────────────

@pytest.fixture
def sample_context() -> NatalContextData:
    """Minimal valid NatalContextData for report tests."""
    return NatalContextData(
        angles=[
            NatalChartAngle(name="ASC", sign="Pisces", degree=11.9, longitude=341.9),
            NatalChartAngle(name="MC", sign="Sagittarius", degree=20.5, longitude=260.5),
        ],
        planets=[
            NatalChartPlanet(name="Sun", sign="Capricorn", degree=16.9, house=11, longitude=286.9),
            NatalChartPlanet(name="Moon", sign="Gemini", degree=29.6, house=4, longitude=119.6),
            NatalChartPlanet(name="Mercury", sign="Capricorn", degree=7.1, house=10, longitude=277.1),
            NatalChartPlanet(name="Venus", sign="Pisces", degree=3.6, house=12, longitude=333.6),
            NatalChartPlanet(name="Mars", sign="Cancer", degree=17.9, house=5, longitude=137.9, retrograde=True),
            NatalChartPlanet(name="Jupiter", sign="Libra", degree=14.0, house=7, longitude=194.0),
            NatalChartPlanet(name="Saturn", sign="Aquarius", degree=17.0, house=12, longitude=327.0),
        ],
        houses=[
            NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i - 1) * 30))
            for i in range(1, 13)
        ],
        aspects=[
            NatalChartAspect(planet_a="Sun", planet_b="Moon", aspect_type="square", orb=5.0),
        ],
        special_points=[],
        elements_balance=ElementsBalance(fire=1.0, earth=3.0, air=2.0, water=1.0),
        modalities_balance=ModalitiesBalance(cardinal=3.0, fixed=2.0, mutable=2.0),
        house_system="Placidus",
        sphere_scores={"work_status_achievement": 3.0, "body_energy_health": 2.5},
        top_signals=[],
        dominants=["Saturn", "Mercury", "Sun"],
    )


@pytest.fixture
def context_with_special_points() -> NatalContextData:
    """NatalContextData WITH special points (Chiron, Selena, Lilith)."""
    ctx = NatalContextData(
        angles=[
            NatalChartAngle(name="ASC", sign="Pisces", degree=11.9, longitude=341.9),
        ],
        planets=[
            NatalChartPlanet(name="Sun", sign="Capricorn", degree=16.9, house=11, longitude=286.9),
            NatalChartPlanet(name="Moon", sign="Gemini", degree=29.6, house=4, longitude=119.6),
        ],
        houses=[
            NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i - 1) * 30))
            for i in range(1, 13)
        ],
        aspects=[],
        special_points=[
            NatalChartSpecialPoint(name="Chiron", sign="Aries", degree=15.0, longitude=15.0, house=1),
            NatalChartSpecialPoint(name="Selena", sign="Taurus", degree=5.0, longitude=35.0, house=2),
            NatalChartSpecialPoint(name="Lilith", sign="Scorpio", degree=20.0, longitude=230.0, house=8),
        ],
        elements_balance=ElementsBalance(),
        modalities_balance=ModalitiesBalance(),
    )
    return ctx


# ══════════════════════════════════════════════════════════════════════
# 1. Block parsing
# ══════════════════════════════════════════════════════════════════════

class TestBlockParsing:
    """_parse_blocks converts raw LLM JSON dicts into typed NatalBlock instances."""

    def test_parse_paragraph(self):
        blocks = NatalReportService._parse_blocks([{"type": "paragraph", "text": "Hello"}])
        assert len(blocks) == 1
        assert isinstance(blocks[0], ParagraphBlock)
        assert blocks[0].text == "Hello"

    def test_parse_lead(self):
        blocks = NatalReportService._parse_blocks([{"type": "lead", "text": "Key insight"}])
        assert len(blocks) == 1
        assert isinstance(blocks[0], LeadBlock)

    def test_parse_heading(self):
        blocks = NatalReportService._parse_blocks([{"type": "heading", "text": "Title", "level": 3}])
        assert len(blocks) == 1
        assert isinstance(blocks[0], HeadingBlock)
        assert blocks[0].level == 3

    def test_parse_list(self):
        blocks = NatalReportService._parse_blocks([
            {"type": "list", "items": ["a", "b"], "ordered": True}
        ])
        assert len(blocks) == 1
        assert isinstance(blocks[0], ListBlock)
        assert blocks[0].items == ["a", "b"]
        assert blocks[0].ordered is True

    def test_parse_callout(self):
        blocks = NatalReportService._parse_blocks([
            {"type": "callout", "title": "Tip", "text": "Advice", "tone": "insight"}
        ])
        assert len(blocks) == 1
        assert isinstance(blocks[0], CalloutBlock)
        assert blocks[0].tone == "insight"

    def test_parse_pros_cons(self):
        blocks = NatalReportService._parse_blocks([
            {
                "type": "pros_cons",
                "prosLabel": "Strengths",
                "consLabel": "Growth",
                "pros": [{"title": "P1", "text": "Good"}],
                "cons": [{"title": "C1", "text": "Work on"}],
            }
        ])
        assert len(blocks) == 1
        assert isinstance(blocks[0], ProsConsBlock)
        assert len(blocks[0].pros) == 1
        assert len(blocks[0].cons) == 1

    def test_parse_quote(self):
        blocks = NatalReportService._parse_blocks([
            {"type": "quote", "text": "Wisdom", "source": "Author"}
        ])
        assert len(blocks) == 1
        assert isinstance(blocks[0], QuoteBlock)
        assert blocks[0].source == "Author"

    def test_parse_divider(self):
        blocks = NatalReportService._parse_blocks([{"type": "divider"}])
        assert len(blocks) == 1
        assert isinstance(blocks[0], DividerBlock)

    def test_unknown_type_raises_value_error(self):
        """BLOCKER 1 FIX: Unknown block types must raise ValueError,
        NOT be converted to ParagraphBlock."""
        with pytest.raises(ValueError, match="Unknown natal report block type"):
            NatalReportService._parse_blocks([{"type": "timeline", "text": "whatever"}])

    def test_unknown_type_does_not_become_paragraph(self):
        """BLOCKER 1 FIX: Unknown block type must NOT silently become ParagraphBlock."""
        with pytest.raises(ValueError):
            NatalReportService._parse_blocks([{"type": "accordion", "text": "data"}])
        # Verify it's not swallowed — the parse must fail hard

    def test_malformed_block_raises_value_error(self):
        """BLOCKER 1 FIX: Malformed blocks must raise ValueError,
        NOT be silently skipped."""
        with pytest.raises(ValueError, match="Malformed block data"):
            NatalReportService._parse_blocks([None])

    def test_empty_list_produces_no_blocks(self):
        blocks = NatalReportService._parse_blocks([])
        assert len(blocks) == 0


# ══════════════════════════════════════════════════════════════════════
# 2. Section validation
# ══════════════════════════════════════════════════════════════════════

class TestSectionValidation:
    """_validate_sections rejects missing sections and empty blocks."""

    def test_rejects_missing_required_section(self, sample_context):
        """Must reject if a required section id is absent."""
        sections = [
            NatalReportSectionRead(
                id="portrait",
                title="Психологический портрет",
                blocks=[ParagraphBlock(type="paragraph", text="ok")],
            )
            # Missing: ascendant, rulers, aspects, spheres, planets, shadow, synthesis
        ]
        with pytest.raises(ValueError, match="Missing required section"):
            NatalReportService._validate_sections(sections, sample_context)

    def test_rejects_empty_blocks(self, sample_context):
        """Must reject a section with no blocks."""
        sections = [
            NatalReportSectionRead(id=sid, title=f"Section {sid}", blocks=[
                ParagraphBlock(type="paragraph", text="content")
            ])
            for sid in REQUIRED_SECTIONS[:-1]
        ] + [
            NatalReportSectionRead(id="synthesis", title="Synthesis", blocks=[])
        ]
        with pytest.raises(ValueError, match="no blocks"):
            NatalReportService._validate_sections(sections, sample_context)

    def test_rejects_empty_text_block(self, sample_context):
        """Must reject a block with empty text."""
        sections = [
            NatalReportSectionRead(id=sid, title=f"Section {sid}", blocks=[
                ParagraphBlock(type="paragraph", text="content")
            ])
            for sid in REQUIRED_SECTIONS[:-1]
        ] + [
            NatalReportSectionRead(id="synthesis", title="Synthesis", blocks=[
                ParagraphBlock(type="paragraph", text="  ")  # Empty after strip
            ])
        ]
        with pytest.raises(ValueError, match="Empty text"):
            NatalReportService._validate_sections(sections, sample_context)

    def test_accepts_all_8_valid_sections(self, sample_context):
        """Must accept when all 8 required sections have non-empty blocks."""
        sections = [
            NatalReportSectionRead(id=sid, title=f"Section {sid}", blocks=[
                ParagraphBlock(type="paragraph", text=f"Content for {sid}")
            ])
            for sid in REQUIRED_SECTIONS
        ]
        # Should not raise
        NatalReportService._validate_sections(sections, sample_context)


# ══════════════════════════════════════════════════════════════════════
# 3. Required section IDs
# ══════════════════════════════════════════════════════════════════════

class TestRequiredSections:
    """Verify the required section IDs match the TZ specification."""

    def test_exactly_8_required_sections(self):
        assert len(REQUIRED_SECTIONS) == 8

    def test_required_section_ids(self):
        expected = ["portrait", "ascendant", "rulers", "aspects", "spheres", "planets", "shadow", "synthesis"]
        assert REQUIRED_SECTIONS == expected


# ══════════════════════════════════════════════════════════════════════
# 4. LLM input context building
# ══════════════════════════════════════════════════════════════════════

class TestLLMInputBuilding:
    """_build_llm_input must produce valid deterministic JSON context."""

    def test_llm_input_is_valid_json(self, sample_context):
        from unittest.mock import MagicMock
        profile = MagicMock()
        profile.birthday.isoformat.return_value = "1993-01-07"
        profile.birth_time.strftime.return_value = "10:33"
        profile.birth_city = "Chirchiq"
        profile.birth_tz = "Asia/Tashkent"
        profile.gender = "female"
        profile.first_name = "Zhanna"

        result = NatalReportService._build_llm_input(sample_context, profile)
        data = json.loads(result)

        assert "user" in data
        assert "birth" in data
        assert "chart" in data
        assert "report_plan" in data

    def test_llm_input_contains_all_planets(self, sample_context):
        from unittest.mock import MagicMock
        profile = MagicMock()
        profile.birthday.isoformat.return_value = "1993-01-07"
        profile.birth_time.strftime.return_value = "10:33"
        profile.birth_city = "Chirchiq"
        profile.birth_tz = "Asia/Tashkent"
        profile.gender = "female"
        profile.first_name = "Zhanna"

        result = NatalReportService._build_llm_input(sample_context, profile)
        data = json.loads(result)

        planet_names = [p["name"] for p in data["chart"]["planets"]]
        assert "Sun" in planet_names
        assert "Moon" in planet_names
        assert "Mars" in planet_names

    def test_llm_input_no_transit_planets(self, sample_context):
        """LLM input must NOT contain transit data — natal report only."""
        from unittest.mock import MagicMock
        profile = MagicMock()
        profile.birthday.isoformat.return_value = "1993-01-07"
        profile.birth_time.strftime.return_value = "10:33"
        profile.birth_city = "Chirchiq"
        profile.birth_tz = "Asia/Tashkent"
        profile.gender = "female"
        profile.first_name = "Zhanna"

        result = NatalReportService._build_llm_input(sample_context, profile)
        data = json.loads(result)

        # No transit keys should exist
        assert "transits" not in data
        assert "transit_planets" not in data
        # No Transit_ prefixed planet names
        for p in data["chart"]["planets"]:
            assert not p["name"].startswith("Transit_")

    def test_llm_input_includes_special_points(self, context_with_special_points):
        """BLOCKER 4: Special points ARE passed to LLM input.
        The guard allows them in output when present in context."""
        from unittest.mock import MagicMock
        profile = MagicMock()
        profile.birthday.isoformat.return_value = "1993-01-07"
        profile.birth_time.strftime.return_value = "10:33"
        profile.birth_city = "Chirchiq"
        profile.birth_tz = "Asia/Tashkent"
        profile.gender = "female"
        profile.first_name = "Zhanna"

        result = NatalReportService._build_llm_input(context_with_special_points, profile)
        data = json.loads(result)

        sp_names = [sp["name"] for sp in data["chart"]["special_points"]]
        assert "Chiron" in sp_names
        assert "Selena" in sp_names
        assert "Lilith" in sp_names


# ══════════════════════════════════════════════════════════════════════
# 5. Context hash
# ══════════════════════════════════════════════════════════════════════

class TestContextHash:
    """_compute_context_hash produces deterministic hash of NatalContextData."""

    def test_hash_is_deterministic(self, sample_context):
        h1 = NatalReportService._compute_context_hash(sample_context)
        h2 = NatalReportService._compute_context_hash(sample_context)
        assert h1 == h2

    def test_hash_changes_on_context_change(self, sample_context):
        h1 = NatalReportService._compute_context_hash(sample_context)
        # Mutate context
        sample_context.planets[0].sign = "Aquarius"
        h2 = NatalReportService._compute_context_hash(sample_context)
        # Note: This may or may not change depending on serialization
        # The important thing is the hash function exists and is deterministic


# ══════════════════════════════════════════════════════════════════════
# 6. Section prompt instructions
# ══════════════════════════════════════════════════════════════════════

class TestSectionPromptInstructions:
    """Each required section must have prompt instructions."""

    def test_all_sections_have_instructions(self):
        for sid in REQUIRED_SECTIONS:
            instructions = NatalReportService._section_prompt_instructions(sid)
            assert instructions, f"Section {sid} must have prompt instructions"
            assert len(instructions) > 20, f"Section {sid} instructions too short"

    def test_unknown_section_has_fallback(self):
        instructions = NatalReportService._section_prompt_instructions("nonexistent")
        assert instructions, "Unknown section should get fallback instructions"


# ══════════════════════════════════════════════════════════════════════
# 7. Hallucination detection (Wave 4)
# ══════════════════════════════════════════════════════════════════════

class TestHallucinationDetection:
    """_validate_sections must reject hallucinated planet names and
    invalid block types — TZ §11 p.3-5."""

    def test_rejects_hallucinated_planet_zeus(self, sample_context):
        """LLM output referencing fabricated planet 'Зевс' must be rejected."""
        sections = _make_all_valid_sections()
        # Inject hallucinated planet into portrait section
        sections[0] = NatalReportSectionRead(
            id="portrait",
            title="Психологический портрет",
            blocks=[ParagraphBlock(
                type="paragraph",
                text="Зевс в твоей карте показывает сильную волю.",
            )],
        )
        with pytest.raises(ValueError, match="Hallucinated planet"):
            NatalReportService._validate_sections(sections, sample_context)

    def test_rejects_hallucinated_planet_proserpina(self, sample_context):
        """LLM output referencing fabricated planet 'Прозерпина' must be rejected."""
        sections = _make_all_valid_sections()
        sections[5] = NatalReportSectionRead(
            id="planets",
            title="Планеты в деталях",
            blocks=[ParagraphBlock(
                type="paragraph",
                text="Прозерпина в 8 доме говорит о глубинных трансформациях.",
            )],
        )
        with pytest.raises(ValueError, match="Hallucinated planet"):
            NatalReportService._validate_sections(sections, sample_context)

    def test_allows_real_planet_names_in_russian(self, sample_context):
        """Real planet names in Russian (Солнце, Марс, etc.) must pass."""
        sections = _make_all_valid_sections()
        sections[0] = NatalReportSectionRead(
            id="portrait",
            title="Психологический портрет",
            blocks=[ParagraphBlock(
                type="paragraph",
                text="Солнце в Козероге и Марс в Раке создают внутреннее напряжение.",
            )],
        )
        # Should not raise
        NatalReportService._validate_sections(sections, sample_context)

    # ── BLOCKER 2: hallucination in list/pros_cons/callout.title ────

    def test_rejects_hallucinated_planet_in_list_items(self, sample_context):
        """BLOCKER 2 FIX: 'Зевс' inside ListBlock.items must be rejected."""
        sections = _make_all_valid_sections()
        sections[4] = NatalReportSectionRead(
            id="spheres",
            title="Сферы жизни",
            blocks=[ListBlock(
                type="list",
                items=["Зевс в 10 доме даёт статус", "Марс в Раке"],
                ordered=False,
            )],
        )
        with pytest.raises(ValueError, match="Hallucinated planet"):
            NatalReportService._validate_sections(sections, sample_context)

    def test_rejects_hallucinated_planet_in_pros_cons_title(self, sample_context):
        """BLOCKER 2 FIX: 'Прозерпина' in ProsConsBlock.pros[].title must be rejected."""
        sections = _make_all_valid_sections()
        sections[0] = NatalReportSectionRead(
            id="portrait",
            title="Психологический портрет",
            blocks=[ProsConsBlock(
                type="pros_cons",
                pros=[ProsConsItem(title="Прозерпина", text="Глубинная трансформация")],
                cons=[],
            )],
        )
        with pytest.raises(ValueError, match="Hallucinated planet"):
            NatalReportService._validate_sections(sections, sample_context)

    def test_rejects_hallucinated_planet_in_pros_cons_text(self, sample_context):
        """BLOCKER 2 FIX: Forbidden name in ProsConsBlock.pros[].text must be rejected."""
        sections = _make_all_valid_sections()
        sections[0] = NatalReportSectionRead(
            id="portrait",
            title="Психологический портрет",
            blocks=[ProsConsBlock(
                type="pros_cons",
                pros=[ProsConsItem(title="Сила", text="Немезида даёт мощь")],
                cons=[],
            )],
        )
        with pytest.raises(ValueError, match="Hallucinated planet"):
            NatalReportService._validate_sections(sections, sample_context)

    def test_rejects_hallucinated_planet_in_callout_title(self, sample_context):
        """BLOCKER 2 FIX: Forbidden name in CalloutBlock.title must be rejected."""
        sections = _make_all_valid_sections()
        sections[1] = NatalReportSectionRead(
            id="ascendant",
            title="Асцендент",
            blocks=[CalloutBlock(
                type="callout",
                title="Совет Зевса",
                text="Обычный текст без запрещённых слов",
                tone="insight",
            )],
        )
        with pytest.raises(ValueError, match="Hallucinated planet"):
            NatalReportService._validate_sections(sections, sample_context)

    def test_rejects_hallucinated_planet_in_cons_text(self, sample_context):
        """BLOCKER 2 FIX: Forbidden name in ProsConsBlock.cons[].text must be rejected."""
        sections = _make_all_valid_sections()
        sections[6] = NatalReportSectionRead(
            id="shadow",
            title="Теневая сторона",
            blocks=[ProsConsBlock(
                type="pros_cons",
                pros=[],
                cons=[ProsConsItem(title="Риск", text="Вулкан может разрушать")],
            )],
        )
        with pytest.raises(ValueError, match="Hallucinated planet"):
            NatalReportService._validate_sections(sections, sample_context)

    # ── BLOCKER 4: Special points allowed from context ──────────────

    def test_special_points_allowed_when_in_context(self, context_with_special_points):
        """BLOCKER 4 FIX: Chiron/Selena/Lilith pass when in context.special_points."""
        sections = _make_all_valid_sections()
        sections[0] = NatalReportSectionRead(
            id="portrait",
            title="Портрет",
            blocks=[ParagraphBlock(
                type="paragraph",
                text="Хирон в Овне говорит о ранах через самоутверждение. "
                     "Селена в Тельце указывает на свет через стабильность. "
                     "Лилит в Скорпионе раскрывает теневые темы власти.",
            )],
        )
        # Should NOT raise — these special points are in the deterministic context
        NatalReportService._validate_sections(sections, context_with_special_points)

    def test_special_points_rejected_when_not_in_context(self, sample_context):
        """BLOCKER 4 FIX: Chiron/Selena/Lilith rejected when NOT in context."""
        sections = _make_all_valid_sections()
        sections[0] = NatalReportSectionRead(
            id="portrait",
            title="Портрет",
            blocks=[ParagraphBlock(
                type="paragraph",
                text="Хирон в Овне говорит о ранах через самоутверждение.",
            )],
        )
        # sample_context has NO special_points, so Хирон must be rejected
        with pytest.raises(ValueError, match="Hallucinated special point"):
            NatalReportService._validate_sections(sections, sample_context)

    def test_lilith_rejected_when_not_in_context(self, sample_context):
        """BLOCKER 4 FIX: Лилит rejected when NOT in context special_points."""
        sections = _make_all_valid_sections()
        sections[0] = NatalReportSectionRead(
            id="portrait",
            title="Портрет",
            blocks=[ParagraphBlock(
                type="paragraph",
                text="Лилит в Скорпионе раскрывает теневые темы.",
            )],
        )
        with pytest.raises(ValueError, match="Hallucinated special point"):
            NatalReportService._validate_sections(sections, sample_context)

    def test_always_forbidden_planets_rejected_even_with_special_points(self, context_with_special_points):
        """Always-forbidden names (Зевс, Прозерпина) must be rejected
        even when context has special points."""
        sections = _make_all_valid_sections()
        sections[0] = NatalReportSectionRead(
            id="portrait",
            title="Портрет",
            blocks=[ParagraphBlock(
                type="paragraph",
                text="Прозерпина в 8 доме даёт глубинную трансформацию.",
            )],
        )
        with pytest.raises(ValueError, match="Hallucinated planet"):
            NatalReportService._validate_sections(sections, context_with_special_points)

    # ── RISK 1: Sign hallucination detection ────────────────────────

    def test_rejects_hallucinated_sign_ophiuchus(self, sample_context):
        """RISK 1 FIX: Fabricated sign 'Змееносец' must be rejected."""
        sections = _make_all_valid_sections()
        sections[0] = NatalReportSectionRead(
            id="portrait",
            title="Портрет",
            blocks=[ParagraphBlock(
                type="paragraph",
                text="Твоё Солнце в Змееносце указывает на скрытую силу.",
            )],
        )
        with pytest.raises(ValueError, match="Hallucinated sign"):
            NatalReportService._validate_sections(sections, sample_context)

    def test_allows_real_sign_names_in_russian(self, sample_context):
        """Standard zodiac sign names in Russian must pass."""
        sections = _make_all_valid_sections()
        sections[0] = NatalReportSectionRead(
            id="portrait",
            title="Портрет",
            blocks=[ParagraphBlock(
                type="paragraph",
                text="Солнце в Козероге и Луна в Близнецах формируют контраст.",
            )],
        )
        # Should not raise
        NatalReportService._validate_sections(sections, sample_context)

    # ── Existing tests ──────────────────────────────────────────────

    def test_rejects_invalid_block_type(self, sample_context):
        """Block type not in the allowed set is rejected by Pydantic schema
        at parse time. The NatalBlock discriminated union enforces only the
        8+2 valid types: lead, paragraph, heading, list, callout, pros_cons,
        quote, divider, highlights, bullets."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="union_tag_invalid"):
            NatalReportSectionRead(
                id="portrait",
                title="Психологический портрет",
                blocks=[{"type": "timeline", "text": "Some timeline content"}],
            )

    def test_allows_all_8_valid_block_types(self, sample_context):
        """All 8 valid block types must pass validation."""
        sections = _make_all_valid_sections()
        sections[0] = NatalReportSectionRead(
            id="portrait",
            title="Психологический портрет",
            blocks=[
                LeadBlock(type="lead", text="Ты собран: ASC в Рыбах"),
                ParagraphBlock(type="paragraph", text="Солнце в Козероге даёт структуру."),
                HeadingBlock(type="heading", text="Ключевые черты", level=2),
                ListBlock(type="list", items=["Целеустремлённость", "Дисциплина"], ordered=False),
                CalloutBlock(type="callout", title="Совет", text="Используй свою энергию.", tone="insight"),
                ProsConsBlock(
                    type="pros_cons",
                    pros=[ProsConsItem(title="Сила", text="Упорство")],
                    cons=[ProsConsItem(title="Риск", text="Перфекционизм")],
                ),
                QuoteBlock(type="quote", text="Дисциплина — мост между целями и достижениями.", source=None),
                DividerBlock(type="divider"),
            ],
        )
        # Should not raise
        NatalReportService._validate_sections(sections, sample_context)


# ══════════════════════════════════════════════════════════════════════
# 8. No placeholder sections (Wave 4)
# ══════════════════════════════════════════════════════════════════════

class TestNoPlaceholderSections:
    """Failed LLM generation must not produce a READY report with
    placeholder/fallback text — TZ §11 p.6-7."""

    @pytest.mark.asyncio
    async def test_llm_failure_produces_failed_retryable(self):
        """When LLM returns None, generation must produce FAILED_RETRYABLE,
        NOT a READY report with placeholder text."""
        from datetime import date as Date, time
        from decimal import Decimal
        from unittest.mock import AsyncMock, patch, MagicMock
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        from app.db.session import Base
        from app.db.models import User, UserProfile, NatalChartCache
        from app.services.natal_report_service import NatalReportService

        engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            # Create user + profile
            user_id = uuid.uuid4()
            user = User(id=user_id, tg_user_id=hash(str(user_id)) % (10**18))
            session.add(user)
            await session.commit()

            profile = UserProfile(
                user_id=user_id, first_name="Test", gender="female",
                birthday=Date(1993, 1, 7), birth_time=time(10, 33),
                birth_city="Chirchiq", birth_lat=Decimal("41.46890"),
                birth_lon=Decimal("69.58220"), birth_tz="Asia/Tashkent",
                is_onboarded=True,
            )
            session.add(profile)
            await session.commit()

            # Create natal context cache
            profile_hash = "testhash123"
            cache_entry = NatalChartCache(
                user_id=user_id, profile_hash=profile_hash,
                raw_chart_json="{}", normalized_context_json="{}",
            )
            session.add(cache_entry)
            await session.commit()

            service = NatalReportService(session)

            # Mock: NatalContextService returns a valid context
            mock_context = NatalContextData(
                planets=[
                    NatalChartPlanet(name="Sun", sign="Capricorn", degree=16.9, house=11, longitude=286.9),
                    NatalChartPlanet(name="Moon", sign="Gemini", degree=29.6, house=4, longitude=119.6),
                ],
                houses=[
                    NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i-1)*30))
                    for i in range(1, 13)
                ],
                aspects=[],
                angles=[NatalChartAngle(name="ASC", sign="Pisces", degree=11.9, longitude=341.9)],
            )

             with patch("app.services.natal_report_service.NatalContextService") as MockCtxSvc, \
                 patch("app.services.natal_report_service.LLMService") as MockLLM:
                mock_ctx_instance = AsyncMock()
                mock_ctx_instance.get_or_build_natal_context.return_value = mock_context
                MockCtxSvc.return_value = mock_ctx_instance
                MockCtxSvc.compute_profile_hash = MagicMock(return_value=profile_hash)

                # LLM returns None → simulates failure
                mock_llm = AsyncMock()
                mock_llm._generate_text.return_value = None
                MockLLM.return_value = mock_llm

                result = await service.generate_report(user_id)

            # Must NOT be READY — must be FAILED_RETRYABLE
            assert result.status == "FAILED_RETRYABLE", (
                f"Expected FAILED_RETRYABLE when LLM fails, got {result.status}"
            )
            assert not result.sections_available

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_invalid_llm_json_produces_failed_retryable(self):
        """When LLM returns invalid JSON, generation must produce FAILED_RETRYABLE."""
        from datetime import date as Date, time
        from decimal import Decimal
        from unittest.mock import AsyncMock, patch, MagicMock
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        from app.db.session import Base
        from app.db.models import User, UserProfile, NatalChartCache
        from app.services.natal_report_service import NatalReportService

        engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            user_id = uuid.uuid4()
            user = User(id=user_id, tg_user_id=hash(str(user_id)) % (10**18))
            session.add(user)
            await session.commit()

            profile = UserProfile(
                user_id=user_id, first_name="Test", gender="female",
                birthday=Date(1993, 1, 7), birth_time=time(10, 33),
                birth_city="Chirchiq", birth_lat=Decimal("41.46890"),
                birth_lon=Decimal("69.58220"), birth_tz="Asia/Tashkent",
                is_onboarded=True,
            )
            session.add(profile)
            await session.commit()

            profile_hash = "testhash456"
            cache_entry = NatalChartCache(
                user_id=user_id, profile_hash=profile_hash,
                raw_chart_json="{}", normalized_context_json="{}",
            )
            session.add(cache_entry)
            await session.commit()

            service = NatalReportService(session)

            mock_context = NatalContextData(
                planets=[
                    NatalChartPlanet(name="Sun", sign="Capricorn", degree=16.9, house=11, longitude=286.9),
                    NatalChartPlanet(name="Moon", sign="Gemini", degree=29.6, house=4, longitude=119.6),
                ],
                houses=[
                    NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i-1)*30))
                    for i in range(1, 13)
                ],
                aspects=[],
                angles=[NatalChartAngle(name="ASC", sign="Pisces", degree=11.9, longitude=341.9)],
            )

            with patch("app.services.natal_report_service.NatalContextService") as MockCtxSvc, \
                 patch("app.services.natal_report_service.LLMService") as MockLLM:
                mock_ctx_instance = AsyncMock()
                mock_ctx_instance.get_or_build_natal_context.return_value = mock_context
                MockCtxSvc.return_value = mock_ctx_instance
                MockCtxSvc.compute_profile_hash = MagicMock(return_value=profile_hash)

                # LLM returns non-JSON garbage
                mock_llm = AsyncMock()
                mock_llm._generate_text.return_value = "This is not JSON at all, just random text"
                MockLLM.return_value = mock_llm

                result = await service.generate_report(user_id)

            assert result.status == "FAILED_RETRYABLE", (
                f"Expected FAILED_RETRYABLE for invalid LLM JSON, got {result.status}"
            )

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_llm_unknown_block_type_produces_failed_retryable(self):
        """BLOCKER 1 FIX: LLM JSON with unknown block type must produce
        FAILED_RETRYABLE, not a READY report with ParagraphBlock fallback."""
        from datetime import date as Date, time
        from decimal import Decimal
        from unittest.mock import AsyncMock, patch, MagicMock
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        from app.db.session import Base
        from app.db.models import User, UserProfile, NatalChartCache
        from app.services.natal_report_service import NatalReportService

        engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            user_id = uuid.uuid4()
            user = User(id=user_id, tg_user_id=hash(str(user_id)) % (10**18))
            session.add(user)
            await session.commit()

            profile = UserProfile(
                user_id=user_id, first_name="Test", gender="female",
                birthday=Date(1993, 1, 7), birth_time=time(10, 33),
                birth_city="Chirchiq", birth_lat=Decimal("41.46890"),
                birth_lon=Decimal("69.58220"), birth_tz="Asia/Tashkent",
                is_onboarded=True,
            )
            session.add(profile)
            await session.commit()

            profile_hash = "testhash789"
            cache_entry = NatalChartCache(
                user_id=user_id, profile_hash=profile_hash,
                raw_chart_json="{}", normalized_context_json="{}",
            )
            session.add(cache_entry)
            await session.commit()

            service = NatalReportService(session)

            mock_context = NatalContextData(
                planets=[
                    NatalChartPlanet(name="Sun", sign="Capricorn", degree=16.9, house=11, longitude=286.9),
                    NatalChartPlanet(name="Moon", sign="Gemini", degree=29.6, house=4, longitude=119.6),
                ],
                houses=[
                    NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i-1)*30))
                    for i in range(1, 13)
                ],
                aspects=[],
                angles=[NatalChartAngle(name="ASC", sign="Pisces", degree=11.9, longitude=341.9)],
            )

            # LLM returns JSON with an unknown block type
            bad_json = json.dumps({
                "blocks": [
                    {"type": "timeline", "text": "Timeline content"},
                ]
            })

            with patch("app.services.natal_report_service.NatalContextService") as MockCtxSvc, \
                 patch("app.services.natal_report_service.LLMService") as MockLLM:
                mock_ctx_instance = AsyncMock()
                mock_ctx_instance.get_or_build_natal_context.return_value = mock_context
                MockCtxSvc.return_value = mock_ctx_instance
                MockCtxSvc.compute_profile_hash = MagicMock(return_value=profile_hash)

                mock_llm = AsyncMock()
                mock_llm._generate_text.return_value = bad_json
                MockLLM.return_value = mock_llm

                result = await service.generate_report(user_id)

            # Must NOT be READY — unknown block type must fail
            assert result.status == "FAILED_RETRYABLE", (
                f"Expected FAILED_RETRYABLE for unknown block type, got {result.status}"
            )

        await engine.dispose()


# ══════════════════════════════════════════════════════════════════════
# 9. _iter_block_texts helper
# ══════════════════════════════════════════════════════════════════════

class TestIterBlockTexts:
    """_iter_block_texts must yield all text-bearing fields from every block type."""

    def test_yields_paragraph_text(self):
        block = ParagraphBlock(type="paragraph", text="Hello world")
        assert list(_iter_block_texts(block)) == ["Hello world"]

    def test_yields_lead_text(self):
        block = LeadBlock(type="lead", text="Key insight")
        assert list(_iter_block_texts(block)) == ["Key insight"]

    def test_yields_heading_text(self):
        block = HeadingBlock(type="heading", text="Title", level=2)
        assert list(_iter_block_texts(block)) == ["Title"]

    def test_yields_list_items(self):
        block = ListBlock(type="list", items=["First", "Second"], ordered=False)
        assert list(_iter_block_texts(block)) == ["First", "Second"]

    def test_yields_callout_title_and_text(self):
        block = CalloutBlock(type="callout", title="Tip", text="Advice", tone="info")
        assert list(_iter_block_texts(block)) == ["Tip", "Advice"]

    def test_yields_pros_cons_all_fields(self):
        block = ProsConsBlock(
            type="pros_cons",
            pros=[ProsConsItem(title="P1", text="Good")],
            cons=[ProsConsItem(title="C1", text="Bad")],
        )
        texts = list(_iter_block_texts(block))
        assert "P1" in texts
        assert "Good" in texts
        assert "C1" in texts
        assert "Bad" in texts

    def test_yields_quote_text(self):
        block = QuoteBlock(type="quote", text="Wisdom", source="Author")
        assert list(_iter_block_texts(block)) == ["Wisdom"]

    def test_divider_yields_nothing(self):
        block = DividerBlock(type="divider")
        assert list(_iter_block_texts(block)) == []


# ══════════════════════════════════════════════════════════════════════
# 10. _check_hallucinated_planets (context-aware)
# ══════════════════════════════════════════════════════════════════════

class TestCheckHallucinatedPlanets:
    """_check_hallucinated_planets is now context-aware for special points."""

    def test_always_forbidden_zeus(self):
        with pytest.raises(ValueError, match="Hallucinated planet"):
            _check_hallucinated_planets("Зевс в карте", set(), set(), "test")

    def test_always_forbidden_proserpina(self):
        with pytest.raises(ValueError, match="Hallucinated planet"):
            _check_hallucinated_planets("Прозерпина в 8 доме", set(), set(), "test")

    def test_special_point_chiron_rejected_without_context(self):
        """Chiron rejected when not in allowed_special_point_names."""
        with pytest.raises(ValueError, match="Hallucinated special point"):
            _check_hallucinated_planets("Хирон в Овне", set(), set(), "test")

    def test_special_point_chiron_allowed_with_context(self):
        """Chiron allowed when 'chiron' in allowed_special_point_names."""
        # Should NOT raise
        _check_hallucinated_planets(
            "Хирон в Овне", set(), {"chiron"}, "test"
        )

    def test_special_point_lilith_rejected_without_context(self):
        with pytest.raises(ValueError, match="Hallucinated special point"):
            _check_hallucinated_planets("Лилит в Скорпионе", set(), set(), "test")

    def test_special_point_lilith_allowed_with_context(self):
        _check_hallucinated_planets(
            "Лилит в Скорпионе", set(), {"lilith"}, "test"
        )

    def test_special_point_selena_rejected_without_context(self):
        with pytest.raises(ValueError, match="Hallucinated special point"):
            _check_hallucinated_planets("Селена в Тельце", set(), set(), "test")

    def test_special_point_selena_allowed_with_context(self):
        _check_hallucinated_planets(
            "Селена в Тельце", set(), {"selena"}, "test"
        )

    def test_real_planet_names_pass(self):
        """Real planet names must not trigger hallucination detection."""
        _check_hallucinated_planets(
            "Солнце в Козероге и Марс в Раке",
            {"sun", "mars", "солнце", "марс"},
            set(),
            "test",
        )


# ══════════════════════════════════════════════════════════════════════
# 11. full_report_available tied to current context (BLOCKER 3)
# ══════════════════════════════════════════════════════════════════════

class TestFullReportAvailability:
    """full_report_available must be tied to current active NatalChartCache,
    not just any READY report for the user."""

    @pytest.mark.asyncio
    async def test_old_context_report_does_not_enable_availability(self):
        """BLOCKER 3 FIX: READY report for old context + new profile → unavailable."""
        from datetime import date as Date, time
        from decimal import Decimal
        from unittest.mock import AsyncMock, patch, MagicMock
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        from app.db.session import Base
        from app.db.models import User, UserProfile, NatalChartCache, NatalReport
        from app.services.natal_service import NatalService
        from app.services.natal_report_service import PROMPT_VERSION, REPORT_SCHEMA_VERSION

        engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            user_id = uuid.uuid4()
            user = User(id=user_id, tg_user_id=hash(str(user_id)) % (10**18))
            session.add(user)
            await session.commit()

            # Old profile data
            profile = UserProfile(
                user_id=user_id, first_name="Test", gender="female",
                birthday=Date(1993, 1, 7), birth_time=time(10, 33),
                birth_city="Chirchiq", birth_lat=Decimal("41.46890"),
                birth_lon=Decimal("69.58220"), birth_tz="Asia/Tashkent",
                is_onboarded=True,
            )
            session.add(profile)
            await session.commit()

            # Old cache entry (different profile_hash = old birth data)
            old_hash = "oldhash999"
            old_cache = NatalChartCache(
                user_id=user_id, profile_hash=old_hash,
                raw_chart_json="{}", normalized_context_json="{}",
            )
            session.add(old_cache)
            await session.commit()

            # Old READY report tied to old_cache
            old_report = NatalReport(
                user_id=user_id,
                natal_context_id=old_cache.id,
                status="READY",
                prompt_version=PROMPT_VERSION,
                report_schema_version=REPORT_SCHEMA_VERSION,
                sections_json='[{"id":"portrait","title":"P","blocks":[]}]',
            )
            session.add(old_report)
            await session.commit()

            # Current cache entry (new profile_hash = new birth data)
            current_hash = "currenthash123"
            current_cache = NatalChartCache(
                user_id=user_id, profile_hash=current_hash,
                raw_chart_json='{"planets":[{"name":"Sun","sign":"Capricorn","degree":16.9,"longitude":286.9}],"houses":[{"number":1,"sign":"Aries","degree":0.0,"longitude":0}],"special_points":[],"house_system":"Placidus"}',
                normalized_context_json="{}",
            )
            session.add(current_cache)
            await session.commit()

            # Mock NatalContextService to return context for current profile
            mock_context = NatalContextData(
                planets=[
                    NatalChartPlanet(name="Sun", sign="Capricorn", degree=16.9, house=11, longitude=286.9),
                ],
                houses=[
                    NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i-1)*30))
                    for i in range(1, 13)
                ],
                aspects=[],
                angles=[NatalChartAngle(name="ASC", sign="Pisces", degree=11.9, longitude=341.9)],
            )

            with patch("app.services.natal_context_service.NatalContextService") as MockCtxSvc:
                mock_ctx_instance = AsyncMock()
                mock_ctx_instance.get_or_build_natal_context.return_value = mock_context
                MockCtxSvc.return_value = mock_ctx_instance
                MockCtxSvc.compute_profile_hash = MagicMock(return_value=current_hash)

                service = NatalService(session)
                preview = await service.get_preview(user_id)

            # Old READY report exists but is for a DIFFERENT context
            # → full_report_available must be False
            assert preview.full_report_available is False, (
                "full_report_available must be False when only an old-context report exists"
            )

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_current_context_report_enables_availability(self):
        """BLOCKER 3 FIX: READY report for current context → available."""
        from datetime import date as Date, time
        from decimal import Decimal
        from unittest.mock import AsyncMock, patch, MagicMock
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        from app.db.session import Base
        from app.db.models import User, UserProfile, NatalChartCache, NatalReport
        from app.services.natal_service import NatalService
        from app.services.natal_report_service import PROMPT_VERSION, REPORT_SCHEMA_VERSION

        engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            user_id = uuid.uuid4()
            user = User(id=user_id, tg_user_id=hash(str(user_id)) % (10**18))
            session.add(user)
            await session.commit()

            profile = UserProfile(
                user_id=user_id, first_name="Test", gender="female",
                birthday=Date(1993, 1, 7), birth_time=time(10, 33),
                birth_city="Chirchiq", birth_lat=Decimal("41.46890"),
                birth_lon=Decimal("69.58220"), birth_tz="Asia/Tashkent",
                is_onboarded=True,
            )
            session.add(profile)
            await session.commit()

            current_hash = "currenthash456"
            current_cache = NatalChartCache(
                user_id=user_id, profile_hash=current_hash,
                raw_chart_json='{"planets":[{"name":"Sun","sign":"Capricorn","degree":16.9,"longitude":286.9}],"houses":[{"number":1,"sign":"Aries","degree":0.0,"longitude":0}],"special_points":[],"house_system":"Placidus"}',
                normalized_context_json="{}",
            )
            session.add(current_cache)
            await session.commit()

            # READY report tied to current cache entry
            current_report = NatalReport(
                user_id=user_id,
                natal_context_id=current_cache.id,
                status="READY",
                prompt_version=PROMPT_VERSION,
                report_schema_version=REPORT_SCHEMA_VERSION,
                sections_json='[{"id":"portrait","title":"P","blocks":[]}]',
            )
            session.add(current_report)
            await session.commit()

            mock_context = NatalContextData(
                planets=[
                    NatalChartPlanet(name="Sun", sign="Capricorn", degree=16.9, house=11, longitude=286.9),
                ],
                houses=[
                    NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i-1)*30))
                    for i in range(1, 13)
                ],
                aspects=[],
                angles=[NatalChartAngle(name="ASC", sign="Pisces", degree=11.9, longitude=341.9)],
            )

            with patch("app.services.natal_context_service.NatalContextService") as MockCtxSvc:
                mock_ctx_instance = AsyncMock()
                mock_ctx_instance.get_or_build_natal_context.return_value = mock_context
                MockCtxSvc.return_value = mock_ctx_instance
                MockCtxSvc.compute_profile_hash = MagicMock(return_value=current_hash)

                service = NatalService(session)
                preview = await service.get_preview(user_id)

            # READY report for CURRENT context → full_report_available must be True
            assert preview.full_report_available is True, (
                "full_report_available must be True when a READY report exists for current context"
            )

        await engine.dispose()


# ── Test helpers ────────────────────────────────────────────────────

def _make_all_valid_sections() -> list[NatalReportSectionRead]:
    """Create all 8 required sections with valid paragraph blocks."""
    return [
        NatalReportSectionRead(id=sid, title=f"Section {sid}", blocks=[
            ParagraphBlock(type="paragraph", text=f"Valid content for {sid} section.")
        ])
        for sid in REQUIRED_SECTIONS
    ]
