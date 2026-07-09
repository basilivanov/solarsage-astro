import json
from pathlib import Path

def test_basil_golden_v1_v2_compact_invariants():
    """Verify Basil 2026-07-08 golden snapshot files are contract-valid and preserve key baseline invariants."""
    golden_dir = Path(__file__).resolve().parent / "fixtures" / "golden"

    # 1. Verify V1 Golden
    v1_path = golden_dir / "basil_2026_07_08_v1.json"
    assert v1_path.exists()
    v1 = json.loads(v1_path.read_text(encoding="utf-8"))

    assert v1["date"] == "2026-07-08"
    assert v1["dayStatus"] == "supportive"
    assert len(v1["topFlags"]) == 3
    assert len(v1["sphereScores"]) == 9

    # Verify metadata is correct
    assert v1["meta"]["fixture_id"] == "basil_2026_07_08_v1"
    assert v1["meta"]["payload_version"] == "today.v1"

    # 2. Verify V2 Golden
    v2_path = golden_dir / "basil_2026_07_08_v2.json"
    assert v2_path.exists()
    v2 = json.loads(v2_path.read_text(encoding="utf-8"))

    assert v2["date"] == "2026-07-08"
    assert v2["dayStatus"] == "steady"
    assert len(v2["topFlags"]) == 3
    assert len(v2["sphereScores"]) == 9

    # Verify V2 block
    assert v2["v2"] is not None
    assert len(v2["v2"]["activationEvidence"]) > 0
    assert len(v2["v2"]["scoreBreakdown"]) == 9

    assert v2["meta"]["fixture_id"] == "basil_2026_07_08_v2"
    assert v2["meta"]["payload_version"] == "today.v2"
