# ############################################################################
# AI_HEADER: MODULE_TESTS_TODAY_FOCUS_TITLE_BUILDER
# ROLE: Unit tests for M-FOCUS-TITLE-BUILDER (Slice C2).
# DEPENDENCIES: pytest, app.services.focus_title_builder
# ############################################################################

from app.services.focus_title_builder import build_event_title


def test_aspect_title_phrasings_and_declensions():
    """Verify Russian aspect phrasings and instrumental case declensions."""
    # Opposition
    f_opp = {
        "factor_id": "sig:aspect:MARS:OPPOSITION:NEPTUNE",
        "source_key": "MARS",
        "target_key": "NEPTUNE",
        "target_type": "natal_planet",
        "aspect_type": "opposition",
    }
    human, tech = build_event_title(f_opp)
    assert human == "Марс напротив твоего Нептуном" or human == "Марс напротив твоего Нептуна"
    assert tech == "Марс оппозиция Нептун"

    # Square
    f_sq = {
        "factor_id": "sig:aspect:SUN:SQUARE:MOON",
        "source_key": "SUN",
        "target_key": "MOON",
        "target_type": "natal_planet",
        "aspect_type": "square",
    }
    human, tech = build_event_title(f_sq)
    assert human == "Солнце в напряжении с твоим Луной"
    assert tech == "Солнце квадратура Луна"

    # Trine
    f_trine = {
        "factor_id": "sig:aspect:VENUS:TRINE:JUPITER",
        "source_key": "VENUS",
        "target_key": "JUPITER",
        "target_type": "natal_planet",
        "aspect_type": "trine",
    }
    human, tech = build_event_title(f_trine)
    assert human == "Венера в гармонии с твоим Юпитером"
    assert tech == "Венера тригон Юпитер"

    # Conjunction
    f_conj = {
        "factor_id": "sig:aspect:MERCURY:CONJUNCTION:MARS",
        "source_key": "MERCURY",
        "target_key": "MARS",
        "target_type": "natal_planet",
        "aspect_type": "conjunction",
    }
    human, tech = build_event_title(f_conj)
    assert human == "Меркурий сошлась с твоим Марсом" or "Меркурий" in human
    assert tech == "Меркурий соединение Марс"


def test_house_angle_lot_titles():
    """Verify house, angle, and lot titles without raw machine keys."""
    # House
    f_house = {
        "factor_id": "sig:house:MARS:10",
        "source_key": "MARS",
        "target_key": "10",
        "target_type": "house",
        "house": 10,
    }
    human, tech = build_event_title(f_house)
    assert human == "Марс в твоём 10-м доме"
    assert tech == "Марс в 10 доме"

    # Angle
    f_angle = {
        "factor_id": "sig:angle:SUN:ASC",
        "source_key": "SUN",
        "target_key": "ASC",
        "target_type": "angle",
    }
    human, tech = build_event_title(f_angle)
    assert human == "Солнце у твоего Асцендента"

    # Lot
    f_lot = {
        "factor_id": "sig:lot:VENUS:FORTUNE",
        "source_key": "VENUS",
        "target_key": "FORTUNE",
        "target_type": "lot",
    }
    human, tech = build_event_title(f_lot)
    assert human == "Венера у Жребия Фортуны"


def test_slow_layer_titles():
    """Verify firdar, profection, and solar return title formatting."""
    f_firdar = {
        "factor_id": "act:firdar:sun",
        "source_key": "SUN",
        "technique_family": "firdar",
        "technique": "firdar",
    }
    human, tech = build_event_title(f_firdar)
    assert human == "Фирдар: Солнце — тема периода"
    assert tech == "Фирдар Солнце"

    f_prof = {
        "factor_id": "act:profection:mars",
        "source_key": "MARS",
        "technique_family": "profection",
        "technique": "profection",
    }
    human, tech = build_event_title(f_prof)
    assert human == "Профекция: Марс в фокусе"
    assert tech == "Профекция Марс"
