from solarsage.utils.ephemeris import calculate_julian_day, calculate_positions

def test_ephemeris_retrograde_calculation():
    # 2026-07-08 12:00 in Moscow: Mercury, Neptune, Pluto are retrograde
    jd = calculate_julian_day("2026-07-08", "12:00", "Europe/Moscow")
    positions = calculate_positions(jd)

    planets = {p["name"]: p for p in positions}

    # Assert retrograde planets
    assert planets["Mercury"]["retrograde"] is True
    assert planets["Neptune"]["retrograde"] is True
    assert planets["Pluto"]["retrograde"] is True

    # Assert direct planets
    assert planets["Sun"]["retrograde"] is False
    assert planets["Moon"]["retrograde"] is False
