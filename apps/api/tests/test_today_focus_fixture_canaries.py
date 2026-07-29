# ############################################################################
# AI_HEADER: MODULE_TESTS_TODAY_FOCUS_FIXTURE_CANARIES
# ROLE: Loader, schema, oracle, permutation, and privacy verification for TodayFocus canary fixtures.
# DEPENDENCIES: pytest, json, pathlib, app.services.today_focus_builder
# ############################################################################

from datetime import date, datetime, timezone
import json
from pathlib import Path
import random
import pytest

from app.services.today_focus_builder import TodayFactor, build_today_focus

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "today_focus"
FACTORS_DIR = FIXTURES_DIR / "factors"
PUBLIC_DIR = FIXTURES_DIR / "public"

ALLOWED_FACTOR_KEYS = {
    "fixtureVersion",
    "caseId",
    "targetDate",
    "timezone",
    "factors",
    "valenceAssessments",
    "expected",
    "decisionRequired",
}

ALLOWED_FACTOR_ITEM_KEYS = {
    "factorId",
    "activationIds",
    "technique",
    "techniqueFamily",
    "sourceKey",
    "targetKey",
    "targetType",
    "aspectType",
    "themeKeys",
    "productSpheres",
    "polarity",
    "strength",
    "salience",
    "activeFrom",
    "exactAt",
    "activeUntil",
    "phase",
    "temporalRole",
    "house",
}

PRIVACY_DENYLIST = [
    "tg",
    "telegram",
    "username",
    "userId",
    "user_id",
    "uuid",
    "birthday",
    "coordinates",
    "initData",
    "cookie",
    "token",
    "profile",
    "prompt",
    "response",
]


def _parse_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    return datetime.fromisoformat(val.replace("Z", "+00:00")).astimezone(timezone.utc)


def _parse_date(val: str) -> date:
    return date.fromisoformat(val)


def _load_factor_fixture(filepath: Path) -> dict:
    with open(filepath, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _json_to_today_factors(factors_raw: list[dict]) -> list[TodayFactor]:
    res = []
    for f in factors_raw:
        tf = TodayFactor(
            factor_id=f["factorId"],
            activation_ids=tuple(f.get("activationIds") or ()),
            technique=f["technique"],
            technique_family=f["techniqueFamily"],
            source_key=f.get("sourceKey"),
            target_key=f.get("targetKey"),
            theme_keys=tuple(f.get("themeKeys") or ()),
            product_spheres=tuple(f.get("productSpheres") or ()),
            polarity=f["polarity"],
            strength=float(f["strength"]),
            salience=float(f.get("salience", f["strength"])),
            active_from=_parse_dt(f.get("activeFrom")),
            exact_at=_parse_dt(f.get("exactAt")),
            active_until=_parse_dt(f.get("activeUntil")),
            phase=f.get("phase"),
            temporal_role=f["temporalRole"],
            aspect_type=f.get("aspectType"),
            target_type=f.get("targetType"),
            house=f.get("house"),
        )
        res.append(tf)
    return res


def test_fixture_files_exist_and_under_max_size():
    """Verify all factor (A-J) and public fixtures exist and do not exceed 64 KB."""
    factor_files = list(FACTORS_DIR.glob("*.json"))
    assert len(factor_files) >= 10, f"Expected at least 10 factor fixture files, found {len(factor_files)}"

    for path in FIXTURES_DIR.rglob("*.json"):
        size = path.stat().st_size
        assert size <= 65536, f"File {path} size {size} exceeds 64 KB limit (max size guard)"


def test_privacy_denylist_scanner():
    """Scan all fixture JSON files recursively against privacy denylist."""
    def _scan_obj(obj: any, path: str):
        if isinstance(obj, dict):
            for k, v in obj.items():
                for banned in PRIVACY_DENYLIST:
                    assert banned.lower() not in k.lower(), f"Privacy violation key '{k}' matches banned term '{banned}' at {path}"
                _scan_obj(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                _scan_obj(item, f"{path}[{idx}]")
        elif isinstance(obj, str):
            pass  # strings checked if needed, key names are primary

    for path in FIXTURES_DIR.rglob("*.json"):
        with open(path, "r", encoding="utf-8") as fh:
            content = json.load(fh)
        _scan_obj(content, str(path))


def test_factor_fixtures_top_level_and_item_allowlist():
    """Validate factor fixtures conform strictly to top-level and item allowlists."""
    for path in FACTORS_DIR.glob("*.json"):
        data = _load_factor_fixture(path)
        extra_keys = set(data.keys()) - ALLOWED_FACTOR_KEYS
        assert not extra_keys, f"File {path.name} contains disallowed top-level keys: {extra_keys}"
        assert data["fixtureVersion"] == "today-focus-factor.v1"

        for f in data.get("factors", []):
            extra_f_keys = set(f.keys()) - ALLOWED_FACTOR_ITEM_KEYS
            assert not extra_f_keys, f"File {path.name} factor {f.get('factorId')} has disallowed keys: {extra_f_keys}"


@pytest.mark.parametrize("filepath", sorted(FACTORS_DIR.glob("*.json"), key=lambda p: p.name))
def test_factor_fixture_oracle_and_provenance(filepath: Path):
    """Run TodayFocus builder on factor fixture and assert oracle output and provenance."""
    data = _load_factor_fixture(filepath)
    factors = _json_to_today_factors(data["factors"])
    target_date = _parse_date(data["targetDate"])
    tz_name = data["timezone"]
    expected = data["expected"]

    focus = build_today_focus(factors, tz_name=tz_name, target_date=target_date)

    # State assertion
    assert focus.state == expected["state"], f"State mismatch in {filepath.name}"

    # Events assertions
    exp_events = expected.get("events", [])
    assert len(focus.events) == len(exp_events), f"Events count mismatch in {filepath.name}"

    for act_ev, exp_ev in zip(focus.events, exp_events):
        assert act_ev.id == exp_ev["id"], f"Event ID mismatch in {filepath.name}"
        assert act_ev.kind == exp_ev["kind"], f"Event kind mismatch in {filepath.name}"
        if exp_ev.get("occursAt") is None:
            assert act_ev.occurs_at is None
        else:
            assert act_ev.occurs_at == _parse_dt(exp_ev["occursAt"])

        # Provenance invariant: sourceActivationIds must exist in factor input activationIds
        all_input_act_ids = {act_id for f in factors for act_id in f.activation_ids}
        for src_id in act_ev.source_activation_ids:
            assert src_id in all_input_act_ids, f"Provenance violation in {filepath.name}: source_id {src_id} not in input activations"

    # Convergence assertion
    exp_conv = expected.get("convergence")
    if exp_conv is None:
        assert focus.convergence is None
    else:
        assert focus.convergence is not None
        assert focus.convergence.id == exp_conv["id"]
        assert focus.convergence.independent_factor_count == exp_conv["independentFactorCount"]
        assert focus.convergence.theme_key == exp_conv["themeKey"]

    # Case J check
    if data.get("caseId") == "family-reducer-boundary-j":
        assert data.get("decisionRequired") is True


@pytest.mark.parametrize("filepath", sorted(FACTORS_DIR.glob("*.json"), key=lambda p: p.name))
def test_factor_fixture_permutation_invariance(filepath: Path):
    """Assert input factors permutation invariance for every fixture."""
    data = _load_factor_fixture(filepath)
    factors = _json_to_today_factors(data["factors"])
    if len(factors) <= 1:
        return

    target_date = _parse_date(data["targetDate"])
    tz_name = data["timezone"]

    focus_orig = build_today_focus(factors, tz_name=tz_name, target_date=target_date)

    shuffled_factors = list(factors)
    random.seed(42)
    random.shuffle(shuffled_factors)

    focus_shuffled = build_today_focus(shuffled_factors, tz_name=tz_name, target_date=target_date)

    assert focus_orig.state == focus_shuffled.state
    assert [e.id for e in focus_orig.events] == [e.id for e in focus_shuffled.events]
    assert [e.occurs_at for e in focus_orig.events] == [e.occurs_at for e in focus_shuffled.events]
    if focus_orig.convergence:
        assert focus_orig.convergence.id == focus_shuffled.convergence.id


def test_public_fixture_unavailable_state_contains_no_llm_text():
    """Verify public fixture with contentState=unavailable carries no LLM text."""
    path = PUBLIC_DIR / "case_g_public_unavailable.json"
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    focus = data["focus"]
    assert focus["contentState"] == "unavailable"
    if focus.get("convergence"):
        assert focus["convergence"].get("summary") is None
    for ev in focus.get("events", []):
        assert ev.get("meaning") is None
    for s in focus.get("featuredSpheres", []):
        assert s.get("summary") is None
        assert s.get("action") is None
