# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_BILLING_YOOKASSA_CLIENT — provider client contract.
# ROLE: Direct contract proof for YooKassaClient via httpx.MockTransport:
#       Basic Auth, endpoints, Idempotence-Key, exact payloads, response
#       mapping, truncation, key limit, and sanitized errors. No real network.
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-BILLING-YOOKASSA-CLIENT
# purpose: Directed unit tests of the ONLY module that talks to YooKassa.
# owns:
#   - apps/api/tests/test_billing_yookassa_client.py
# inputs: injected httpx.MockTransport handlers.
# outputs: assertions on outgoing requests and mapped results/errors.
# dependencies: YooKassaClient, httpx.
# side_effects: none (MockTransport only).
# emitted_logs: none.
# invariants:
#   - Basic Auth is exactly shop_id:secret_key on every call.
#   - Idempotence-Key >64 rejects BEFORE any HTTP.
#   - Errors never carry provider bodies or credentials.
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TESTS-BILLING-YOOKASSA-CLIENT

from __future__ import annotations

import base64
import json
import uuid

import httpx
import pytest

from app.services.yookassa_client import YooKassaClient, YooKassaError

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OWNER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _client(handler) -> YooKassaClient:
    return YooKassaClient("shop-1", "secret-1", transport=httpx.MockTransport(handler))


def _capture(handler):
    captured: dict = {}

    def _handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return handler(request)

    return captured, _handler


def _assert_auth(request: httpx.Request) -> None:
    auth = request.headers["authorization"]
    assert auth.startswith("Basic ")
    creds = base64.b64decode(auth.split(" ", 1)[1]).decode()
    assert creds == "shop-1:secret-1"


def _body(request: httpx.Request) -> dict:
    return json.loads(request.content.decode())


@pytest.mark.asyncio
async def test_initial_recurrent_exact_payload_and_mapping() -> None:
    captured, handler = _capture(
        lambda request: httpx.Response(
            200,
            json={
                "id": "prov-1",
                "status": "pending",
                "confirmation": {"confirmation_url": "https://pay.example/c"},
            },
        )
    )
    client = _client(handler)
    result = await client.create_initial_payment(
        user_id=USER_ID,
        owner_id=OWNER_ID,
        amount_kopecks=9900,
        currency="RUB",
        description="Подписка SolarSage — месяц",
        return_url="https://app.example/return",
        product_slug="subscription_month",
        idempotence_key="init-owner-first",
    )
    request = captured["request"]
    assert str(request.url) == "https://api.yookassa.ru/v3/payments"
    _assert_auth(request)
    assert request.headers["idempotence-key"] == "init-owner-first"
    body = _body(request)
    assert body["amount"] == {"value": "99.00", "currency": "RUB"}
    assert body["capture"] is True
    assert body["save_payment_method"] is True
    assert body["merchant_customer_id"] == str(USER_ID)
    assert body["confirmation"] == {"type": "redirect", "return_url": "https://app.example/return"}
    assert body["metadata"] == {
        "user_id": str(USER_ID),
        "owner_id": str(OWNER_ID),
        "product_slug": "subscription_month",
        "type": "initial_recurrent",
    }
    assert result == {
        "provider_payment_id": "prov-1",
        "confirmation_url": "https://pay.example/c",
        "status": "pending",
    }


@pytest.mark.asyncio
async def test_one_time_exact_payload() -> None:
    captured, handler = _capture(
        lambda request: httpx.Response(
            200,
            json={
                "id": "prov-2",
                "status": "pending",
                "confirmation": {"confirmation_url": "https://pay.example/once"},
            },
        )
    )
    client = _client(handler)
    result = await client.create_one_time_payment(
        user_id=USER_ID,
        owner_id=OWNER_ID,
        amount_kopecks=12000,
        currency="RUB",
        description="3 хорарных вопроса",
        return_url="https://app.example/return",
        product_slug="horary_3",
        idempotence_key="purchase-owner",
    )
    request = captured["request"]
    assert str(request.url) == "https://api.yookassa.ru/v3/payments"
    _assert_auth(request)
    assert request.headers["idempotence-key"] == "purchase-owner"
    body = _body(request)
    assert body == {
        "amount": {"value": "120.00", "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": "https://app.example/return"},
        "capture": True,
        "description": "3 хорарных вопроса",
        "metadata": {
            "user_id": str(USER_ID),
            "owner_id": str(OWNER_ID),
            "product_slug": "horary_3",
            "type": "one_time",
        },
    }
    assert result == {
        "provider_payment_id": "prov-2",
        "confirmation_url": "https://pay.example/once",
        "status": "pending",
    }


@pytest.mark.asyncio
async def test_rebill_exact_payload() -> None:
    captured, handler = _capture(
        lambda request: httpx.Response(200, json={"id": "prov-3", "status": "succeeded"})
    )
    client = _client(handler)
    result = await client.create_recurrent_payment(
        user_id=USER_ID,
        owner_id=OWNER_ID,
        payment_method_id="pm-saved-1",
        amount_kopecks=99900,
        currency="RUB",
        description="Подписка SolarSage — автопродление",
        product_slug="subscription_year",
        period_label="2027-07-21",
        idempotence_key="rebill-owner-2027-07-21",
    )
    request = captured["request"]
    assert str(request.url) == "https://api.yookassa.ru/v3/payments"
    _assert_auth(request)
    assert request.headers["idempotence-key"] == "rebill-owner-2027-07-21"
    body = _body(request)
    assert body == {
        "amount": {"value": "999.00", "currency": "RUB"},
        "capture": True,
        "payment_method_id": "pm-saved-1",
        "description": "Подписка SolarSage — автопродление",
        "metadata": {
            "user_id": str(USER_ID),
            "owner_id": str(OWNER_ID),
            "product_slug": "subscription_year",
            "type": "recurrent",
            "period": "2027-07-21",
        },
    }
    assert result == {"provider_payment_id": "prov-3", "status": "succeeded"}


@pytest.mark.asyncio
async def test_get_payment_auth_endpoint_and_mapping() -> None:
    captured, handler = _capture(
        lambda request: httpx.Response(
            200,
            json={
                "id": "prov-9",
                "status": "succeeded",
                "paid": True,
                "amount": {"value": "99.00", "currency": "RUB"},
                "metadata": {"user_id": "u", "owner_id": "o"},
                "payment_method": {"id": "pm-1", "saved": True},
            },
        )
    )
    client = _client(handler)
    result = await client.get_payment("prov-9")
    request = captured["request"]
    assert str(request.url) == "https://api.yookassa.ru/v3/payments/prov-9"
    _assert_auth(request)
    assert result["provider_payment_id"] == "prov-9"
    assert result["status"] == "succeeded"
    assert result["paid"] is True
    assert result["amount_value"] == "99.00"
    assert result["currency"] == "RUB"
    assert result["metadata"] == {"user_id": "u", "owner_id": "o"}
    assert result["payment_method_id"] == "pm-1"
    assert result["payment_method_saved"] is True


@pytest.mark.asyncio
async def test_description_truncated_to_128() -> None:
    captured, handler = _capture(lambda request: httpx.Response(200, json={"id": "prov-4"}))
    client = _client(handler)
    await client.create_one_time_payment(
        user_id=USER_ID,
        owner_id=OWNER_ID,
        amount_kopecks=5000,
        currency="RUB",
        description="x" * 500,
        return_url="https://app.example/return",
        product_slug="horary_1",
        idempotence_key="purchase-owner",
    )
    assert len(_body(captured["request"])["description"]) == 128


@pytest.mark.asyncio
async def test_idempotence_key_over_64_rejects_before_http() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"id": "prov-5"})

    client = _client(handler)
    with pytest.raises(YooKassaError, match="64"):
        await client.create_one_time_payment(
            user_id=USER_ID,
            owner_id=OWNER_ID,
            amount_kopecks=5000,
            currency="RUB",
            description="d",
            return_url="https://app.example/return",
            product_slug="horary_1",
            idempotence_key="k" * 65,
        )
    assert calls == []  # no HTTP happened


@pytest.mark.asyncio
async def test_transport_error_is_sanitized() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused by 10.0.0.1:443")

    client = _client(handler)
    with pytest.raises(YooKassaError) as exc_info:
        await client.get_payment("prov-x")
    message = str(exc_info.value)
    assert "transport error" in message
    assert "10.0.0.1" not in message
    assert "secret-1" not in message


@pytest.mark.asyncio
async def test_http_error_never_carries_provider_body_or_credentials() -> None:
    client = _client(
        lambda request: httpx.Response(401, json={"error": "invalid shop-1 secret-1 credentials"})
    )
    with pytest.raises(YooKassaError) as exc_info:
        await client.get_payment("prov-x")
    message = str(exc_info.value)
    assert message == "yookassa http 401"
    assert "invalid" not in message
    assert "secret-1" not in message


@pytest.mark.asyncio
async def test_malformed_json_and_missing_id_are_sanitized() -> None:
    client = _client(lambda request: httpx.Response(200, content=b"<html>not json</html>"))
    with pytest.raises(YooKassaError, match="malformed"):
        await client.get_payment("prov-x")

    client2 = _client(lambda request: httpx.Response(
        200,
        json={
            "status": "succeeded",
            "paid": True,
            "amount": {"value": "99.00", "currency": "RUB"},
            "metadata": {},
        },
    ))
    with pytest.raises(YooKassaError, match="missing payment id"):
        await client2.get_payment("prov-x")


@pytest.mark.asyncio
async def test_top_level_list_is_sanitized_on_post_and_get() -> None:
    for call in ("post", "get"):
        client = _client(lambda request: httpx.Response(200, json=[]))
        with pytest.raises(YooKassaError, match="malformed") as exc_info:
            if call == "post":
                await client.create_one_time_payment(
                    user_id=USER_ID,
                    owner_id=OWNER_ID,
                    amount_kopecks=5000,
                    currency="RUB",
                    description="d",
                    return_url="https://app.example/return",
                    product_slug="horary_1",
                    idempotence_key="purchase-owner",
                )
            else:
                await client.get_payment("prov-x")
        assert "AttributeError" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_nested_shape_strings_are_sanitized() -> None:
    # confirmation as a string (POST path)
    client = _client(
        lambda request: httpx.Response(200, json={"id": "prov-7", "status": "pending", "confirmation": "bad"})
    )
    with pytest.raises(YooKassaError, match="invalid confirmation"):
        await client.create_one_time_payment(
            user_id=USER_ID,
            owner_id=OWNER_ID,
            amount_kopecks=5000,
            currency="RUB",
            description="d",
            return_url="https://app.example/return",
            product_slug="horary_1",
            idempotence_key="purchase-owner",
        )

    # amount as a string (GET path)
    client2 = _client(
        lambda request: httpx.Response(
            200,
            json={"id": "prov-8", "status": "succeeded", "paid": True, "amount": "bad"},
        )
    )
    with pytest.raises(YooKassaError, match="invalid amount"):
        await client2.get_payment("prov-8")

    # payment_method as a string (GET path)
    client3 = _client(
        lambda request: httpx.Response(
            200,
            json={
                "id": "prov-9",
                "status": "succeeded",
                "paid": True,
                "amount": {"value": "99.00", "currency": "RUB"},
                "metadata": {},
                "payment_method": "bad",
            },
        )
    )
    with pytest.raises(YooKassaError, match="invalid payment_method"):
        await client3.get_payment("prov-9")

    # metadata as a string (GET path)
    client4 = _client(
        lambda request: httpx.Response(
            200,
            json={
                "id": "prov-10",
                "status": "succeeded",
                "paid": True,
                "amount": {"value": "99.00", "currency": "RUB"},
                "metadata": "bad",
            },
        )
    )
    with pytest.raises(YooKassaError, match="invalid metadata"):
        await client4.get_payment("prov-10")


@pytest.mark.asyncio
async def test_post_transport_failure_is_sanitized() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused by 10.0.0.1:443")

    client = _client(handler)
    with pytest.raises(YooKassaError) as exc_info:
        await client.create_one_time_payment(
            user_id=USER_ID,
            owner_id=OWNER_ID,
            amount_kopecks=5000,
            currency="RUB",
            description="d",
            return_url="https://app.example/return",
            product_slug="horary_1",
            idempotence_key="purchase-owner",
        )
    message = str(exc_info.value)
    assert "transport error" in message
    assert "10.0.0.1" not in message
    assert "secret-1" not in message


def _get_client(body: dict) -> YooKassaClient:
    return _client(lambda request: httpx.Response(200, json=body))


def _valid_get_body(**overrides) -> dict:
    body = {
        "id": "prov-ok",
        "status": "succeeded",
        "paid": True,
        "amount": {"value": "99.00", "currency": "RUB"},
        "metadata": {"user_id": "u", "owner_id": "o"},
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio
async def test_strict_paid_must_be_bool() -> None:
    with pytest.raises(YooKassaError, match="invalid paid"):
        await _get_client(_valid_get_body(paid="false")).get_payment("prov-ok")
    with pytest.raises(YooKassaError, match="invalid paid"):
        await _get_client(_valid_get_body(paid=1)).get_payment("prov-ok")
    with pytest.raises(YooKassaError, match="invalid paid"):
        await _get_client(_valid_get_body(paid=None)).get_payment("prov-ok")


@pytest.mark.asyncio
async def test_strict_status_must_be_nonempty_str() -> None:
    with pytest.raises(YooKassaError, match="invalid status"):
        await _get_client(_valid_get_body(status=123)).get_payment("prov-ok")
    with pytest.raises(YooKassaError, match="invalid status"):
        await _get_client(_valid_get_body(status="")).get_payment("prov-ok")


@pytest.mark.asyncio
async def test_strict_amount_contract() -> None:
    # Missing amount entirely.
    with pytest.raises(YooKassaError, match="missing amount"):
        await _get_client(_valid_get_body(amount=None)).get_payment("prov-ok")
    # Numeric value.
    with pytest.raises(YooKassaError, match="invalid amount value"):
        await _get_client(_valid_get_body(amount={"value": 9900, "currency": "RUB"})).get_payment("prov-ok")
    # Missing currency.
    with pytest.raises(YooKassaError, match="invalid amount currency"):
        await _get_client(_valid_get_body(amount={"value": "99.00"})).get_payment("prov-ok")
    # Empty currency.
    with pytest.raises(YooKassaError, match="invalid amount currency"):
        await _get_client(_valid_get_body(amount={"value": "99.00", "currency": ""})).get_payment("prov-ok")


@pytest.mark.asyncio
async def test_strict_metadata_must_be_present_dict() -> None:
    with pytest.raises(YooKassaError, match="invalid metadata"):
        await _get_client(_valid_get_body(metadata=None)).get_payment("prov-ok")
    with pytest.raises(YooKassaError, match="invalid metadata"):
        await _get_client(_valid_get_body(metadata="bad")).get_payment("prov-ok")


@pytest.mark.asyncio
async def test_strict_payment_method_scalars() -> None:
    # saved as a string.
    with pytest.raises(YooKassaError, match="invalid payment_method saved"):
        await _get_client(
            _valid_get_body(payment_method={"id": "pm-1", "saved": "false"})
        ).get_payment("prov-ok")
    # Numeric method id.
    with pytest.raises(YooKassaError, match="invalid payment_method id"):
        await _get_client(
            _valid_get_body(payment_method={"id": 123, "saved": False})
        ).get_payment("prov-ok")
    # saved=true without id.
    with pytest.raises(YooKassaError, match="saved method without id"):
        await _get_client(
            _valid_get_body(payment_method={"saved": True})
        ).get_payment("prov-ok")
    # Valid: no payment_method at all (a card payment that was not saved).
    result = await _get_client(_valid_get_body()).get_payment("prov-ok")
    assert result["payment_method_id"] is None
    assert result["payment_method_saved"] is False
    # Valid: saved method with id.
    result = await _get_client(
        _valid_get_body(payment_method={"id": "pm-1", "saved": True})
    ).get_payment("prov-ok")
    assert result["payment_method_id"] == "pm-1"
    assert result["payment_method_saved"] is True


@pytest.mark.asyncio
async def test_strict_create_response_status() -> None:
    # Non-string status in a create response is rejected.
    client = _client(lambda request: httpx.Response(200, json={"id": "prov-5", "status": 123}))
    with pytest.raises(YooKassaError, match="invalid status"):
        await client.create_one_time_payment(
            user_id=USER_ID,
            owner_id=OWNER_ID,
            amount_kopecks=5000,
            currency="RUB",
            description="d",
            return_url="https://app.example/return",
            product_slug="horary_1",
            idempotence_key="purchase-owner",
        )
    # Absent status takes the documented pending default.
    client2 = _client(lambda request: httpx.Response(200, json={"id": "prov-6", "confirmation": {}}))
    result = await client2.create_one_time_payment(
        user_id=USER_ID,
        owner_id=OWNER_ID,
        amount_kopecks=5000,
        currency="RUB",
        description="d",
        return_url="https://app.example/return",
        product_slug="horary_1",
        idempotence_key="purchase-owner",
    )
    assert result["status"] == "pending"
