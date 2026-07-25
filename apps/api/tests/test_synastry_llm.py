"""Unit tests for synastry_llm module."""

from app.services.synastry_llm import (
    ASPECT_MEANINGS,
    BANNED_PHRASES,
    PLANET_MEANINGS,
    build_drilldown_prompt,
    build_report_prompt,
    validate_drilldown_output,
    validate_llm_output,
)


def test_synastry_llm_imports():
    assert "Sun" in PLANET_MEANINGS
    assert "conjunction" in ASPECT_MEANINGS
    assert "обречены" in BANNED_PHRASES


def test_build_report_prompt_no_pii():
    prompt = build_report_prompt(
        score=85,
        status="good",
        counters={"good": 5, "mid": 2, "bad": 1},
        aspects=[{"owner_planet": "Sun", "partner_planet": "Moon", "aspect": "trine", "orb_degrees": 1.2}],
        partner_precision="exact",
    )
    assert "system" in prompt
    assert "user" in prompt
    assert "85/100" in prompt["user"]
    assert "Максим" not in prompt["user"]


def test_build_drilldown_prompt():
    prompt = build_drilldown_prompt(
        {"owner_planet": "Mercury", "partner_planet": "Mercury", "aspect": "square", "tone": "tense"}
    )
    assert "system" in prompt
    assert "Mercury square Mercury" in prompt["user"]


def test_validate_llm_output_valid():
    sample = {
        "summary": "Гармоничное взаимодействие с глубоким пониманием.",
        "translations": [{"title": "Общий язык", "text": "Вам легко договориться."}],
    }
    ok, err = validate_llm_output(sample, report_precision="exact")
    assert ok is True
    assert err is None


def test_validate_llm_output_banned_phrase():
    for phrase in ["обречены", "всегда", "никогда", "идеальная пара", "развод неминуем"]:
        sample = {"summary": f"Эта пара {phrase}."}
        ok, err = validate_llm_output(sample, report_precision="exact")
        assert ok is False
        assert "Banned phrase" in err


def test_validate_llm_output_approximate_forbidden_terms():
    for term in ["5-м доме", "в доме партнера", "асцендент партнера"]:
        sample = {"summary": f"Планета находится в {term}."}
        ok, err = validate_llm_output(sample, report_precision="approximate")
        assert ok is False
        assert "Forbidden" in err


def test_validate_llm_output_length_limits():
    long_summary = {"summary": "A" * 400}
    ok, err = validate_llm_output(long_summary, report_precision="exact")
    assert ok is False
    assert "Summary exceeds" in err


def test_validate_drilldown_output():
    valid = {
        "intro": "Описание аспекта.",
        "scenes": [
            {"title": "Сцена 1", "text": "Текст 1"},
            {"title": "Сцена 2", "text": "Текст 2"},
            {"title": "Сцена 3", "text": "Текст 3"},
        ],
        "repairs": ["1. Шаг один", "2. Шаг два", "3. Шаг три"],
        "not_means": ["Не означает 1", "Не означает 2", "Не означает 3"],
    }
    ok, err = validate_drilldown_output(valid)
    assert ok is True

    invalid_not_means = dict(valid, not_means=["Только один пункт"])
    ok2, err2 = validate_drilldown_output(invalid_not_means)
    assert ok2 is False
    assert "3 items" in err2
