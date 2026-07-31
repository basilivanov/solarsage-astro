# ############################################################################
# AI_HEADER: MODULE_TESTS_TODAY_FOCUS_CONTRACT
# ROLE: Contract tests for the legacy TodayFocus schema and pure builder.
# DEPENDENCIES: pytest, app.schemas.today_focus, app.services.today_focus_builder
# ############################################################################

from datetime import date, datetime, timezone
import pytest

from app.schemas.today_focus import (
    TodayFocus,
    TodayConvergence,
    TodayFocusEvent,
    TodayFeaturedSphere,
    TodayFocusFactor,
)
from app.services.today_focus_builder import TodayFactor, build_today_focus


def test_today_focus_schema_negative_validation_matrix():
    """Negative validation matrix for TodayFocus Pydantic schema (doc 29 §4.3, §6 п.6)."""
    from pydantic import ValidationError

    def _make_event(ev_id: str = "ev:1") -> TodayFocusEvent:
        return TodayFocusEvent(
            id=ev_id,
            kind="exact",
            occurs_at=datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc),
            local_date=date(2026, 7, 28),
            timezone="Europe/Moscow",
            precision="minute",
            human_title="Тест",
            source_activation_ids=["act-1"],
        )

    def _make_featured(key: str = "work") -> TodayFeaturedSphere:
        return TodayFeaturedSphere(
            key=key,
            relevance_rank=1,
            state="convergence_today",
            convergence_id="conv:1",
            source_event_ids=["ev:1"],
            source_activation_ids=["act-1"],
        )

    # 1. Invalid state x contentState pairs
    invalid_pairs = [
        ("convergence_today", "not_needed"),
        ("single_impulses", "not_needed"),
        ("background_only", "ready"),
        ("background_only", "pending"),
        ("background_only", "unavailable"),
        ("no_accent", "ready"),
        ("no_accent", "pending"),
        ("no_accent", "unavailable"),
        ("unavailable", "ready"),
        ("unavailable", "pending"),
        ("unavailable", "not_needed"),
    ]

    for st, cst in invalid_pairs:
        with pytest.raises(ValidationError, match="Invalid content_state"):
            TodayFocus(
                state=st,  # type: ignore[arg-type]
                events=[_make_event()] if st in ("convergence_today", "single_impulses") else [],
                content_state=cst,  # type: ignore[arg-type]
            )

    # 2. Events cap > 3
    with pytest.raises(ValidationError, match="exceeds cap of 3"):
        TodayFocus(
            state="single_impulses",
            events=[_make_event(f"ev:{i}") for i in range(4)],
            content_state="ready",
        )

    # 3. Featured spheres cap > 3
    with pytest.raises(ValidationError, match="exceeds cap of 3"):
        TodayFocus(
            state="convergence_today",
            featured_spheres=[_make_featured(f"s{i}") for i in range(4)],
            content_state="ready",
        )

    # 4. Duplicate event IDs
    with pytest.raises(ValidationError, match="duplicate public event IDs"):
        TodayFocus(
            state="single_impulses",
            events=[_make_event("ev:1"), _make_event("ev:1")],
            content_state="ready",
        )

    # 5. Empty event ID
    with pytest.raises(ValidationError, match="cannot be empty"):
        TodayFocus(
            state="single_impulses",
            events=[_make_event("   ")],
            content_state="ready",
        )


def test_today_focus_events_sorting_and_tz():
    """Contract §5: events are sorted by occurs_at + id and occurs_at has timezone."""
    dt1 = datetime(2026, 7, 28, 10, 30, 0, tzinfo=timezone.utc)
    dt2 = datetime(2026, 7, 28, 16, 52, 0, tzinfo=timezone.utc)

    f1 = TodayFactor(
        factor_id="sig:aspect:MOON:OPPOSITION:NEPTUNE",
        activation_ids=("act-2",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MOON",
        target_key="NEPTUNE",
        theme_keys=("action",),
        product_spheres=("relationships",),
        polarity="tense",
        strength=0.75,
        salience=0.75,
        active_from=None,
        exact_at=dt1,
        active_until=None,
        phase="exact",
        temporal_role="anchor_today",
    )
    f2 = TodayFactor(
        factor_id="sig:aspect:MARS:OPPOSITION:NEPTUNE",
        activation_ids=("act-1",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MARS",
        target_key="NEPTUNE",
        theme_keys=("action",),
        product_spheres=("work",),
        polarity="tense",
        strength=0.85,
        salience=0.85,
        active_from=None,
        exact_at=dt2,
        active_until=None,
        phase="exact",
        temporal_role="anchor_today",
    )

    res = build_today_focus([f1, f2], tz_name="Europe/Moscow", target_date=date(2026, 7, 28))
    assert res.state == "convergence_today"
    assert len(res.events) == 2
    # Events sorted by occurs_at (dt1 < dt2)
    assert res.events[0].occurs_at == dt1
    assert res.events[1].occurs_at == dt2
    assert res.events[0].occurs_at.tzinfo is not None


def test_check_focus_narrative_safety_validation():
    """C2: Test LLM focus narrative validation rules (banned jargon, length, keys match)."""
    from app.services.llm_claim_validator import LLMClaimValidator

    validator = LLMClaimValidator()

    valid_raw = {
        "convergence_summary": "Сложный день: важно сохранять баланс и проверять факты.",
        "event_meanings": {
            "ev:1": "Первый импульс требует хладнокровия.",
            "ev:2": "Вторая встреча откроет полезные детали.",
        },
        "featured_spheres": {
            "work": {
                "summary": "На работе возможны переговоры.",
                "action": "Проверь документы перед отправкой.",
            }
        },
    }

    # 1. Valid case
    sanitized, reason = validator.check_focus_narrative_safety(
        valid_raw,
        state="convergence_today",
        expected_event_ids=["ev:1", "ev:2"],
        expected_sphere_keys=["work"],
    )
    assert sanitized is not None
    assert reason is None
    assert sanitized["convergence_summary"] == "Сложный день: важно сохранять баланс и проверять факты."

    # 2. Banned jargon in summary
    jargon_raw = valid_raw.copy()
    jargon_raw["convergence_summary"] = "Транзит Марса создает напряжение."
    sanitized, reason = validator.check_focus_narrative_safety(
        jargon_raw,
        state="convergence_today",
        expected_event_ids=["ev:1", "ev:2"],
        expected_sphere_keys=["work"],
    )
    assert sanitized is None
    assert reason == "banned_jargon"

    # 3. Missing event ID key
    missing_key_raw = valid_raw.copy()
    missing_key_raw["event_meanings"] = {"ev:1": "Только одно направление."}
    sanitized, reason = validator.check_focus_narrative_safety(
        missing_key_raw,
        state="convergence_today",
        expected_event_ids=["ev:1", "ev:2"],
        expected_sphere_keys=["work"],
    )
    assert sanitized is None
    assert reason == "parse"

    # 4. Length limit exceeded (> 100 for action)
    long_action_raw = valid_raw.copy()
    long_action_raw["featured_spheres"] = {
        "work": {
            "summary": "Сводка.",
            "action": "А" * 105,
        }
    }
    sanitized, reason = validator.check_focus_narrative_safety(
        long_action_raw,
        state="convergence_today",
        expected_event_ids=["ev:1", "ev:2"],
        expected_sphere_keys=["work"],
    )
    assert sanitized is None
    assert reason == "length"


def test_convergence_background_factors_camel_serialization():
    """TodayConvergence serializes background_factors as camelCase backgroundFactors with roles and titles."""
    conv = TodayConvergence(
        id="conv:1",
        theme_key="PLUTO",
        title="Что сошлось именно сегодня",
        summary=None,
        independent_factor_count=3,
        technique_families=["transit", "return"],
        source_activation_ids=["act-1", "act-2", "act-3"],
        background_factors=[
            TodayFocusFactor(
                id="f:act:t2n__MARS__TRINE__PLUTO",
                role="supporting",
                human_title="Марс в гармонии с твоим Плутоном",
                technical_title="Марс тригон Плутон",
                source_activation_ids=["act-2"],
            ),
            TodayFocusFactor(
                id="f:act:lunar_return__ANGULAR_PLANET__PLUTO__HOUSE_4",
                role="background",
                human_title="Лунар: Плутон — тема месяца",
                technical_title="Лунар: Плутон на углу (4 дом)",
                source_activation_ids=["act-3"],
            ),
        ],
    )
    dumped = conv.model_dump(by_alias=True)
    assert "backgroundFactors" in dumped
    bf = dumped["backgroundFactors"]
    assert len(bf) == 2
    assert bf[0]["role"] == "supporting"
    assert bf[0]["humanTitle"] == "Марс в гармонии с твоим Плутоном"
    assert bf[0]["technicalTitle"] == "Марс тригон Плутон"
    assert bf[0]["sourceActivationIds"] == ["act-2"]
    assert bf[1]["role"] == "background"
    # Default when omitted: empty list, still serialized
    conv_min = TodayConvergence(
        id="conv:2",
        theme_key="SUN",
        title="t",
        summary=None,
        independent_factor_count=2,
    )
    assert conv_min.model_dump(by_alias=True)["backgroundFactors"] == []
