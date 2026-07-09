import json
from pathlib import Path

def test_mercury_convergence_fixture():
    golden_dir = Path(__file__).resolve().parent / "fixtures" / "golden"
    fixture = json.loads((golden_dir / "mercury_convergence_case_v2.json").read_text(encoding="utf-8"))

    v2 = fixture.get("v2")
    assert v2 is not None

    # Assert topActivatedTargets MERCURY has familyCount = 3
    targets = v2["activationSummary"]["topActivatedTargets"]
    assert len(targets) > 0
    mercury = next((t for t in targets if t["targetKey"] == "MERCURY"), None)
    assert mercury is not None
    assert mercury["familyCount"] == 3
    assert sorted(mercury["techniques"]) == ["annual_profection", "firdar_minor", "transit_to_natal"]

    # Assert whyToday has exactly 3 items for different families
    why = v2["whyToday"]
    assert len(why) == 3
    ids = {item["id"] for item in why}
    assert ids == {"why-planet-MERCURY-transit", "why-planet-MERCURY-profection", "why-planet-MERCURY-firdar"}


def test_antidominance_fixture():
    golden_dir = Path(__file__).resolve().parent / "fixtures" / "golden"
    fixture = json.loads((golden_dir / "antidominance_case_v2.json").read_text(encoding="utf-8"))

    v2 = fixture.get("v2")
    assert v2 is not None

    # Assert relationships_partnership has dominanceCapped = True
    scores = v2["scoreBreakdown"]
    rel = scores.get("relationships_partnership")
    assert rel is not None
    assert rel["dominanceCapped"] is True

    # Assert there is a contribution from cap source with negative amount
    cap = next((c for c in rel["contributions"] if c["source"] == "cap"), None)
    assert cap is not None
    assert cap["amount"] < 0
    assert "Dominance cap applied" in cap["evidence"]
