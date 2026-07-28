# ############################################################################
# AI_HEADER: MODULE_TESTS_FOCUS_EVENT_DRILLDOWN
# ROLE: Unit and integration tests for Focus Event Drilldown API (Slice E1).
# DEPENDENCIES: pytest, httpx, app.services.focus_event_drilldown_builder, app.api.day
# ############################################################################

import json
from datetime import date, datetime, timezone
import pytest
from httpx import AsyncClient

from app.db.models import TodayPayloadCache, User
from app.services.focus_event_drilldown_builder import build_focus_event_drilldown


def test_builder_aspect_event_full_evidence():
    """Builder case (a): Aspect event Moon square Pluto with complete evidence fields."""
    event = {
        "id": "ev:act:t2n__MOON__SQUARE__PLUTO",
        "kind": "exact",
        "occursAt": "2026-07-28T13:31:00Z",
        "localDate": "2026-07-28",
        "timezone": "Europe/Moscow",
        "precision": "minute",
        "humanTitle": "Луна в напряжении с твоим Плутоном",
        "technicalTitle": "Луна квадратура Плутон",
        "meaning": "Реакция может быть глубже обычного — не принимай её за решение.",
        "sourceActivationIds": ["act-moon-sq-pluto"],
    }

    evidence = [
        {
            "id": "act-moon-sq-pluto",
            "planet": "Transit_Moon",
            "targetPlanet": "Pluto",
            "targetType": "natal_planet",
            "sourceFrame": "transit",
            "targetFrame": "natal",
            "technique": "transit_to_natal",
            "techniqueFamily": "transit",
            "aspect": "square",
            "polarity": "tense",
            "orb": 0.3166,  # 0°19′
            "strength": 0.72,
            "phase": "exact",
            "activeFrom": "2026-07-27T01:12:00Z",
            "activeUntil": "2026-07-29T19:40:00Z",
        }
    ]

    drilldown = build_focus_event_drilldown(event, evidence)

    assert drilldown.event_id == "ev:act:t2n__MOON__SQUARE__PLUTO"
    assert drilldown.human_title == "Луна в напряжении с твоим Плутоном"
    assert drilldown.kind == "exact"
    assert drilldown.kind_label == "точный пик"
    assert drilldown.local_time == "16:31"  # 13:31 UTC is 16:31 Europe/Moscow
    assert drilldown.timezone == "Europe/Moscow"
    assert drilldown.technique_label == "Транзит к твоей натальной карте"

    # Source & Target
    assert drilldown.source is not None
    assert drilldown.source.planet_key == "MOON"
    assert drilldown.source.label == "Луна"
    assert drilldown.source.frame_label == "транзитная"

    assert drilldown.target is not None
    assert drilldown.target.planet_key == "PLUTO"
    assert drilldown.target.label == "Плутон"
    assert drilldown.target.frame_label == "твой натальный"

    # Aspect details & mechanics
    assert drilldown.aspect_label == "Квадрат"
    assert drilldown.aspect_symbol == "□"
    assert drilldown.aspect_tone == "tense"
    assert drilldown.aspect_mechanics is not None

    # Numbers
    num_labels = [n.label for n in drilldown.numbers]
    assert "Орб" in num_labels
    assert "Точное время" in num_labels
    assert "Фаза" in num_labels
    assert "Окно действия" in num_labels
    assert "Сила влияния" in num_labels
    assert "Полюс" in num_labels

    orb_num = next(n for n in drilldown.numbers if n.label == "Орб")
    assert orb_num.value == "0°19′"

    time_num = next(n for n in drilldown.numbers if n.label == "Точное время")
    assert "16:31 · Europe/Moscow" in time_num.value

    strength_num = next(n for n in drilldown.numbers if n.label == "Сила влияния")
    assert strength_num.value == "72%"


def test_builder_lot_target_event():
    """Builder case (b): Event targeting a lot (transit_to_lot, targetType lot, NECESSITY)."""
    event = {
        "id": "ev:act:t2l__SUN__CONJUNCTION__NECESSITY",
        "kind": "starts",
        "occursAt": "2026-07-28T08:00:00Z",
        "localDate": "2026-07-28",
        "timezone": "Europe/Moscow",
        "precision": "minute",
        "humanTitle": "Солнце сошлось с твоим Жребием",
        "technicalTitle": "Солнце соединение Жребий",
        "meaning": "Акцент на ключевой точке года.",
        "sourceActivationIds": ["act-sun-conj-necessity"],
    }

    evidence = [
        {
            "id": "act-sun-conj-necessity",
            "planet": "Transit_Sun",
            "targetPlanet": "NECESSITY",
            "targetType": "lot",
            "technique": "transit_to_lot",
            "techniqueFamily": "transit",
            "aspect": "conjunction",
            "polarity": "supportive",
            "orb": 0.5,
            "strength": 0.8,
            "phase": "building",
        }
    ]

    drilldown = build_focus_event_drilldown(event, evidence)

    assert drilldown.technique_label == "Транзит к жребию"
    assert drilldown.target is not None
    assert drilldown.target.label == "Жребий"
    assert drilldown.target.frame_label == "твой жребий"
    assert drilldown.target.function_text == "особая расчётная точка карты"


def test_builder_empty_evidence_degrades_gracefully():
    """Builder case (c): Empty evidence list degrades gracefully without raising exceptions."""
    event = {
        "id": "ev:fallback:1",
        "kind": "exact",
        "occursAt": "2026-07-28T12:00:00Z",
        "localDate": "2026-07-28",
        "timezone": "UTC",
        "precision": "minute",
        "humanTitle": "Фактор дня",
        "technicalTitle": "Фактор дня",
        "meaning": None,
        "sourceActivationIds": [],
    }

    drilldown = build_focus_event_drilldown(event, [])

    assert drilldown.event_id == "ev:fallback:1"
    assert drilldown.human_title == "Фактор дня"
    assert drilldown.source is None
    assert drilldown.target is None
    assert isinstance(drilldown.numbers, list)


@pytest.mark.asyncio
async def test_focus_event_drilldown_endpoint_happy_and_404_paths(
    async_client: AsyncClient, make_initdata, db_session
):
    """Endpoint integration: GET /api/day/{date}/focus-event/{event_id} from cached payload."""
    from sqlalchemy import select

    raw_init = make_initdata(user_id=889900, username="drilldown_user")
    await async_client.post("/api/auth/telegram", json={"initData": raw_init})

    user = (await db_session.execute(select(User).where(User.tg_user_id == 889900))).scalar_one()

    # Minimal payload JSON with focus event and activation evidence
    event_id = "ev:act:t2n__MOON__SQUARE__PLUTO"
    payload_dict = {
        "meta": {
            "schemaVersion": "today/v1",
            "contractVersion": 3,
            "calculationVersion": 1,
            "normalizationVersion": 1,
            "scoringVersion": 1,
            "promptVersion": 4,
            "contentVersion": 11,
            "generatedAt": "2026-07-28T00:00:00Z",
            "cached": True,
            "payloadVersion": "today.v2.1",
            "frontendPayloadVersion": 3,
        },
        "focus": {
            "state": "convergence_today",
            "contentState": "ready",
            "events": [
                {
                    "id": event_id,
                    "kind": "exact",
                    "occursAt": "2026-07-28T13:31:00Z",
                    "localDate": "2026-07-28",
                    "timezone": "Europe/Moscow",
                    "precision": "minute",
                    "humanTitle": "Луна в напряжении с твоим Плутоном",
                    "technicalTitle": "Луна квадратура Плутон",
                    "meaning": "Реакция может быть глубже обычного.",
                    "sourceActivationIds": ["act-moon-sq-pluto"],
                }
            ],
            "featuredSpheres": [],
        },
        "v2": {
            "activationEvidence": [
                {
                    "id": "act-moon-sq-pluto",
                    "planet": "Transit_Moon",
                    "targetPlanet": "Pluto",
                    "targetType": "natal_planet",
                    "sourceFrame": "transit",
                    "targetFrame": "natal",
                    "technique": "transit_to_natal",
                    "techniqueFamily": "transit",
                    "aspect": "square",
                    "polarity": "tense",
                    "orb": 0.3166,
                    "strength": 0.72,
                    "phase": "exact",
                }
            ]
        },
    }

    # Insert into today_payloads_cache table
    cache_row = TodayPayloadCache(
        user_id=user.id,
        target_date=date(2026, 7, 28),
        profile_hash="test_profile_hash",
        cache_key_hash="test_key_hash",
        payload_json=json.dumps(payload_dict),
    )
    db_session.add(cache_row)
    await db_session.commit()

    # 1. Happy path: GET focus event drilldown
    resp = await async_client.get(f"/api/day/2026-07-28/focus-event/{event_id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # camelCase keys check
    assert data["eventId"] == event_id
    assert data["humanTitle"] == "Луна в напряжении с твоим Плутоном"
    assert data["kind"] == "exact"
    assert data["kindLabel"] == "точный пик"
    assert data["localTime"] == "16:31"
    assert data["timezone"] == "Europe/Moscow"
    assert data["meaning"] == "Реакция может быть глубже обычного."
    assert data["source"]["planetKey"] == "MOON"
    assert data["target"]["planetKey"] == "PLUTO"
    assert data["aspectLabel"] == "Квадрат"
    assert data["aspectSymbol"] == "□"
    assert isinstance(data["numbers"], list)

    # 2. Non-existent event_id -> 404
    resp_404 = await async_client.get("/api/day/2026-07-28/focus-event/ev:nonexistent")
    assert resp_404.status_code == 404
    assert resp_404.json()["detail"]["message"] == "event_not_found"

    # 3. Uncached date -> 404
    resp_uncached = await async_client.get("/api/day/2026-07-29/focus-event/ev:1")
    assert resp_uncached.status_code == 404
    assert resp_uncached.json()["detail"]["message"] == "day_payload_not_cached"


def test_builder_snake_case_cached_evidence_source_planet():
    """Real today_payloads_cache JSON is snake_case: source_planet must populate source side."""
    event = {
        "id": "ev:act:t2n__MOON__SQUARE__PLUTO",
        "kind": "exact",
        "occurs_at": "2026-07-28T10:31:25Z",
        "local_date": "2026-07-28",
        "timezone": "Europe/Moscow",
        "precision": "minute",
        "human_title": "Луна в напряжении с твоим Плутоном",
        "technical_title": "Луна квадратура Плутон",
        "meaning": None,
        "source_activation_ids": ["t2n__MOON__SQUARE__PLUTO"],
    }
    evidence = [
        {
            "id": "t2n__MOON__SQUARE__PLUTO",
            "technique": "transit_to_natal",
            "technique_family": "transit",
            "target_type": "planet",
            "source_planet": "Moon",
            "source_frame": "transit",
            "target_planet": "PLUTO",
            "target_frame": "natal",
            "aspect": "square",
            "orb": 0.78,
            "phase": "applying",
            "strength": 0.72,
            "polarity": "tense",
            "active_from": "2026-07-28T00:34:52Z",
            "active_until": "2026-07-28T20:26:01Z",
        }
    ]

    drilldown = build_focus_event_drilldown(event, evidence)

    assert drilldown.source is not None
    assert drilldown.source.planet_key == "MOON"
    assert drilldown.source.label == "Луна"
    assert drilldown.source.frame_label == "транзитная"
    assert drilldown.source.function_text == "эмоции и привычки"
    assert drilldown.target is not None
    assert drilldown.target.planet_key == "PLUTO"
    assert drilldown.local_time == "13:31"
    labels = [n.label for n in drilldown.numbers]
    assert "Орб" in labels and "Окно действия" in labels


def test_builder_lot_target_from_target_key_fallback():
    """Lot events carry target_key/lot instead of target_planet: target side shows Жребий."""
    event = {
        "id": "ev:act:t2l__MOON__QUINCUNX__NECESSITY",
        "kind": "exact",
        "occurs_at": "2026-07-28T21:35:00Z",
        "timezone": "Europe/Moscow",
        "human_title": "Луна в напряжении с твоим жребием",
        "technical_title": "Луна квиконс жребий",
        "meaning": None,
        "source_activation_ids": ["t2l__MOON__QUINCUNX__NECESSITY"],
    }
    evidence = [
        {
            "id": "t2l__MOON__QUINCUNX__NECESSITY",
            "technique": "transit_to_natal",
            "target_planet": None,
            "target_key": "NECESSITY",
            "target_type": "lot",
            "lot": "NECESSITY",
            "source_planet": "Moon",
            "aspect": "quincunx",
            "orb": 5.71,
            "phase": "separating",
            "polarity": "neutral",
        }
    ]

    drilldown = build_focus_event_drilldown(event, evidence)

    assert drilldown.source is not None and drilldown.source.label == "Луна"
    assert drilldown.target is not None
    assert drilldown.target.label == "Жребий"
    assert drilldown.target.frame_label == "твой жребий"
    assert "NECESSITY" not in (drilldown.target.function_text + drilldown.target.label)
    assert drilldown.aspect_label == "Квиконс"
