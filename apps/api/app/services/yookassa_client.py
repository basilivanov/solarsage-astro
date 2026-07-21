# ############################################################################
# AI_HEADER: MODULE_YOOKASSA_CLIENT — isolated async-safe YooKassa HTTP client.
# ROLE: The ONLY module talking to the YooKassa API: Basic Auth server-side,
#       Idempotence-Key <= 64, capture=true, save_payment_method on initial
#       recurrent payments, rebill via payment_method_id. Fully async — no
#       sync SDK call ever blocks the event loop.
# DEPENDENCIES: httpx, app.core.config
# GRACE_ANCHORS: [YK_CREATE, YK_GET]
# ############################################################################

# START_MODULE_CONTRACT: M-YOOKASSA-CLIENT
# purpose: Encapsulate every YooKassa API call behind one async client. No
#   other module performs HTTP against YooKassa.
# owns:
#   - apps/api/app/services/yookassa_client.py
# inputs: payment creation parameters (amount kopecks, currency, description,
#   metadata, return_url, payment_method_id for rebill), provider payment id.
# outputs: typed dicts (provider_payment_id, confirmation_url/token, status,
#   paid, amount, currency, metadata, payment_method_id/saved).
# dependencies: httpx.AsyncClient, settings (shop id/secret from env only).
# side_effects: HTTPS POST/GET to api.yookassa.ru.
# emitted_logs: none (no secrets or payloads logged here).
# invariants:
#   - Basic Auth = shop_id:secret_key, server-side only, never logged.
#   - Idempotence-Key header is always <= 64 chars.
#   - capture=true on every created payment; initial recurrent payment uses
#     save_payment_method=true + merchant_customer_id; rebill charges by
#     payment_method_id without user confirmation.
#   - No synchronous YooKassa SDK calls inside the event loop.
# failure_policy: raises YooKassaError on transport/HTTP errors; the caller
#   maps it to domain errors. 4xx/5xx bodies are never re-raised raw to users.
# END_MODULE_CONTRACT: M-YOOKASSA-CLIENT

# START_MODULE_MAP: M-YOOKASSA-CLIENT
# public_entrypoints:
#   - YooKassaClient.create_initial_payment
#   - YooKassaClient.create_one_time_payment
#   - YooKassaClient.create_recurrent_payment
#   - YooKassaClient.get_payment
#   - get_yookassa_client
# semantic_blocks:
#   - YK_CREATE: payment creation (initial recurrent / one-time / rebill)
#   - YK_GET: authenticated payment read (webhook verification)
# owned_tests:
#   - apps/api/tests/test_billing_yookassa_client.py
# END_MODULE_MAP: M-YOOKASSA-CLIENT

from __future__ import annotations

import uuid

import httpx

from app.core.config import settings

_API_BASE = "https://api.yookassa.ru/v3"
_MAX_IDEMPOTENCE_KEY = 64


class YooKassaError(RuntimeError):
    """YooKassa transport/API failure (never carries secrets)."""


def _kopecks_to_value(kopecks: int) -> str:
    return f"{kopecks // 100}.{kopecks % 100:02d}"


class YooKassaClient:
    """Async-safe YooKassa API client (httpx; Basic Auth; no sync SDK)."""

    def __init__(
        self,
        shop_id: str,
        secret_key: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not shop_id or not secret_key:
            raise YooKassaError("YooKassa shop_id/secret_key are not configured")
        self._auth = httpx.BasicAuth(shop_id, secret_key)
        # Test-only seam: production passes nothing (real network); tests
        # inject httpx.MockTransport. BillingService signatures are unchanged.
        self._transport = transport

    # START_BLOCK: YK_CREATE
    async def _post(self, path: str, payload: dict, idempotence_key: str) -> dict:
        if len(idempotence_key) > _MAX_IDEMPOTENCE_KEY:
            raise YooKassaError("idempotence key exceeds 64 chars")
        try:
            async with httpx.AsyncClient(
                auth=self._auth, transport=self._transport, timeout=httpx.Timeout(15.0)
            ) as client:
                response = await client.post(
                    f"{_API_BASE}{path}",
                    json=payload,
                    headers={"Idempotence-Key": idempotence_key},
                )
        except httpx.HTTPError as exc:
            raise YooKassaError(f"yookassa transport error: {type(exc).__name__}") from exc
        if response.status_code >= 400:
            # Never re-raise the provider body (may echo request/secrets).
            raise YooKassaError(f"yookassa http {response.status_code}")
        try:
            return response.json()
        except ValueError:
            raise YooKassaError("yookassa malformed response") from None

    @staticmethod
    def _payment_id(payment: dict) -> str:
        provider_payment_id = payment.get("id")
        if not provider_payment_id or not isinstance(provider_payment_id, str):
            raise YooKassaError("yookassa malformed response: missing payment id")
        return provider_payment_id

    @staticmethod
    def _confirmation_url(payment: dict) -> str | None:
        confirmation = payment.get("confirmation") or {}
        return confirmation.get("confirmation_url")

    async def create_initial_payment(
        self,
        *,
        user_id: uuid.UUID,
        owner_id: uuid.UUID,
        amount_kopecks: int,
        currency: str,
        description: str,
        return_url: str,
        product_slug: str,
        idempotence_key: str,
    ) -> dict:
        # START_FUNCTION_CONTRACT: F-M-YOOKASSA-CLIENT.create_initial_payment
        # purpose: Create the FIRST recurrent payment with the payment method
        #   saved for later rebilling.
        # inputs: user/owner ids, amount (kopecks), currency, description,
        #   return_url, product_slug, idempotence_key (<=64).
        # returns: dict with provider_payment_id, confirmation_url, status.
        # side_effects: POST /payments with save_payment_method=true,
        #   merchant_customer_id and capture=true.
        # error_behavior: YooKassaError on transport/HTTP failure.
        # END_FUNCTION_CONTRACT: F-M-YOOKASSA-CLIENT.create_initial_payment
        payload = {
            "amount": {"value": _kopecks_to_value(amount_kopecks), "currency": currency},
            "confirmation": {"type": "redirect", "return_url": return_url},
            "capture": True,
            "save_payment_method": True,
            "merchant_customer_id": str(user_id),
            "description": description[:128],
            "metadata": {
                "user_id": str(user_id),
                "owner_id": str(owner_id),
                "product_slug": product_slug,
                "type": "initial_recurrent",
            },
        }
        payment = await self._post("/payments", payload, idempotence_key)
        return {
            "provider_payment_id": self._payment_id(payment),
            "confirmation_url": self._confirmation_url(payment),
            "status": payment.get("status", "pending"),
        }

    async def create_one_time_payment(
        self,
        *,
        user_id: uuid.UUID,
        owner_id: uuid.UUID,
        amount_kopecks: int,
        currency: str,
        description: str,
        return_url: str,
        product_slug: str,
        idempotence_key: str,
    ) -> dict:
        # START_FUNCTION_CONTRACT: F-M-YOOKASSA-CLIENT.create_one_time_payment
        # purpose: Create a one-time payment (horary pack, natal report).
        # inputs: as create_initial_payment minus save_payment_method.
        # returns: dict with provider_payment_id, confirmation_url, status.
        # side_effects: POST /payments with capture=true (no method saving).
        # error_behavior: YooKassaError on transport/HTTP failure.
        # END_FUNCTION_CONTRACT: F-M-YOOKASSA-CLIENT.create_one_time_payment
        payload = {
            "amount": {"value": _kopecks_to_value(amount_kopecks), "currency": currency},
            "confirmation": {"type": "redirect", "return_url": return_url},
            "capture": True,
            "description": description[:128],
            "metadata": {
                "user_id": str(user_id),
                "owner_id": str(owner_id),
                "product_slug": product_slug,
                "type": "one_time",
            },
        }
        payment = await self._post("/payments", payload, idempotence_key)
        return {
            "provider_payment_id": self._payment_id(payment),
            "confirmation_url": self._confirmation_url(payment),
            "status": payment.get("status", "pending"),
        }

    async def create_recurrent_payment(
        self,
        *,
        user_id: uuid.UUID,
        owner_id: uuid.UUID,
        payment_method_id: str,
        amount_kopecks: int,
        currency: str,
        description: str,
        product_slug: str,
        period_label: str,
        idempotence_key: str,
    ) -> dict:
        # START_FUNCTION_CONTRACT: F-M-YOOKASSA-CLIENT.create_recurrent_payment
        # purpose: Charge a saved payment_method_id for the next period.
        # inputs: ids, payment_method_id, amount, currency, description,
        #   product_slug, period_label, idempotence_key (<=64).
        # returns: dict with provider_payment_id, status.
        # side_effects: POST /payments with payment_method_id and capture=true.
        # error_behavior: YooKassaError on transport/HTTP failure.
        # END_FUNCTION_CONTRACT: F-M-YOOKASSA-CLIENT.create_recurrent_payment
        payload = {
            "amount": {"value": _kopecks_to_value(amount_kopecks), "currency": currency},
            "capture": True,
            "payment_method_id": payment_method_id,
            "description": description[:128],
            "metadata": {
                "user_id": str(user_id),
                "owner_id": str(owner_id),
                "product_slug": product_slug,
                "type": "recurrent",
                "period": period_label,
            },
        }
        payment = await self._post("/payments", payload, idempotence_key)
        return {
            "provider_payment_id": self._payment_id(payment),
            "status": payment.get("status", "pending"),
        }
    # END_BLOCK: YK_CREATE

    # START_BLOCK: YK_GET
    async def get_payment(self, provider_payment_id: str) -> dict:
        # START_FUNCTION_CONTRACT: F-M-YOOKASSA-CLIENT.get_payment
        # purpose: Authenticated read of a payment by id — the mandatory
        #   second verification step of the webhook contract (never trust the
        #   webhook payload alone).
        # inputs: provider_payment_id.
        # returns: dict with id, status, paid, amount_value (str), currency,
        #   metadata, payment_method_id, payment_method_saved.
        # side_effects: GET /payments/<id> with Basic Auth.
        # error_behavior: YooKassaError on transport/HTTP failure.
        # END_FUNCTION_CONTRACT: F-M-YOOKASSA-CLIENT.get_payment
        try:
            async with httpx.AsyncClient(
                auth=self._auth, transport=self._transport, timeout=httpx.Timeout(10.0)
            ) as client:
                response = await client.get(f"{_API_BASE}/payments/{provider_payment_id}")
        except httpx.HTTPError as exc:
            raise YooKassaError(f"yookassa transport error: {type(exc).__name__}") from exc
        if response.status_code >= 400:
            raise YooKassaError(f"yookassa http {response.status_code}")
        try:
            payment = response.json()
        except ValueError:
            raise YooKassaError("yookassa malformed response") from None
        method = payment.get("payment_method") or {}
        return {
            "provider_payment_id": self._payment_id(payment),
            "status": payment.get("status"),
            "paid": bool(payment.get("paid")),
            "amount_value": str((payment.get("amount") or {}).get("value", "")),
            "currency": str((payment.get("amount") or {}).get("currency", "")),
            "metadata": payment.get("metadata") or {},
            "payment_method_id": method.get("id"),
            "payment_method_saved": bool(method.get("saved")),
        }
    # END_BLOCK: YK_GET


def get_yookassa_client() -> YooKassaClient:
    """Factory: build the client from env config or fail closed."""
    if not settings.yookassa_enabled:
        raise YooKassaError("YooKassa is not enabled (YOOKASSA_ENABLED=false)")
    return YooKassaClient(settings.yookassa_shop_id, settings.yookassa_secret_key)
