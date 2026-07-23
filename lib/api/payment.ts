
// ############################################################################
// AI_HEADER: FRONTEND_API_PAYMENT — typed YooKassa billing client.
// ROLE: Typed facade for the billing endpoints (catalog, subscription
//       start/status/cancel, one-time purchase start/status) consumed by the
//       profile access card, paywall, natal CTA and horary purchase sheet.
//       Prices ALWAYS come from GET /api/payment/products — never hardcoded.
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-PAYMENT
// purpose: Typed billing client with schema-validated responses and a stable
//   PaymentApiError carrying HTTP status + backend code for 401/402/404/409/503 handling.
// owns:
//   - lib/api/payment.ts
// inputs: product slugs, purchase id, cancel reason.
// outputs: ProductsListResponse, SubscriptionStart/Status responses,
//   PurchaseStart/Status responses; PaymentApiError on non-ok.
// dependencies: packages/contracts (+ runtime wire schemas); fetch.
// side_effects: credentialed /api/payment/* GET and POST requests.
// emitted_logs: none.
// invariants:
//   - All responses are validated against the generated wire schemas.
//   - PaymentApiError preserves status and optional backend detail.code.
//   - No price constants in this module: amounts live only in API payloads.
//   - The client never calls the provider or the webhook; polling reads
//     authenticated local status endpoints only.
// failure_policy: non-ok responses throw PaymentApiError; schema/network errors propagate.
// END_MODULE_CONTRACT: M-FRONTEND-API-PAYMENT

// START_MODULE_MAP: M-FRONTEND-API-PAYMENT
// public_entrypoints:
//   - PaymentApiError
//   - getPaymentProducts
//   - startSubscription
//   - getSubscriptionStatus
//   - cancelSubscription
//   - startPurchase
//   - getPurchaseStatus
// semantic_blocks:
//   - TYPED_ERROR: PaymentApiError with status/code.
//   - ERROR_BUILD: map backend detail to the typed error.
//   - CATALOG: products list fetch.
//   - SUBSCRIPTION: start/status/cancel calls.
//   - PURCHASE: start/status calls.
//   - ERROR_TEXT: paymentErrorMessage RU mapping for user-facing flows.
// owned_tests:
//   - __tests__/api/payment-client.test.ts
// END_MODULE_MAP: M-FRONTEND-API-PAYMENT

import type {
  ProductsListResponse,
  PurchaseStartResponse,
  PurchaseStatusResponse,
  SubscriptionStartResponse,
  SubscriptionStatusResponse,
} from "@/packages/contracts"
import {
  ProductsListResponseWireSchema,
  PurchaseStartResponseWireSchema,
  PurchaseStatusResponseWireSchema,
  SubscriptionStartResponseWireSchema,
  SubscriptionStatusResponseWireSchema,
} from "@/packages/contracts/runtime"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

// START_BLOCK: TYPED_ERROR
type PaymentErrorBody = {
  detail?: {
    code?: string
    message?: string
  } | string
}

export type Product = ProductsListResponse["products"][number]

export class PaymentApiError extends Error {
  status: number
  code?: string

  constructor({ status, code, message }: { status: number; code?: string; message: string }) {
    super(message)
    this.name = "PaymentApiError"
    this.status = status
    this.code = code
  }
}
// END_BLOCK: TYPED_ERROR

// START_BLOCK: ERROR_BUILD
async function buildPaymentApiError(res: Response): Promise<PaymentApiError> {
  const body = await res.json().catch(() => ({} as PaymentErrorBody))
  const detail = body?.detail
  const code = typeof detail === "object" && detail !== null ? detail.code : undefined
  const backendMessage =
    typeof detail === "object" && detail !== null ? detail.message : typeof detail === "string" ? detail : undefined
  const message =
    backendMessage ||
    (res.status === 503
      ? "Оплата временно недоступна"
      : res.status === 401
        ? "Требуется авторизация"
        : "Не удалось выполнить платёжный запрос")
  return new PaymentApiError({ status: res.status, code, message })
}
// END_BLOCK: ERROR_BUILD

// START_BLOCK: CATALOG
export async function getPaymentProducts(): Promise<ProductsListResponse> {
  const res = await fetch(`${API_BASE}/api/payment/products`, { credentials: "include" })
  if (!res.ok) {
    throw await buildPaymentApiError(res)
  }
  return ProductsListResponseWireSchema.parse(await res.json())
}
// END_BLOCK: CATALOG

// START_BLOCK: SUBSCRIPTION
export async function startSubscription(
  productSlug: "subscription_month" | "subscription_year"
): Promise<SubscriptionStartResponse> {
  const res = await fetch(`${API_BASE}/api/payment/subscription/start`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ productSlug }),
  })
  if (!res.ok) {
    throw await buildPaymentApiError(res)
  }
  return SubscriptionStartResponseWireSchema.parse(await res.json())
}

export async function getSubscriptionStatus(): Promise<SubscriptionStatusResponse> {
  const res = await fetch(`${API_BASE}/api/payment/subscription/status`, { credentials: "include" })
  if (!res.ok) {
    throw await buildPaymentApiError(res)
  }
  return SubscriptionStatusResponseWireSchema.parse(await res.json())
}

export async function cancelSubscription(reason?: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/payment/subscription/cancel`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason: reason ?? null }),
  })
  if (!res.ok) {
    throw await buildPaymentApiError(res)
  }
}
// END_BLOCK: SUBSCRIPTION

// START_BLOCK: PURCHASE
export type OneTimeProductSlug =
  | "natal_full_report"
  | "horary_1"
  | "horary_3"
  | "horary_5"
  | "horary_10"
  | "election_1"

const KNOWN_ERROR_MESSAGES: Record<string, string> = {
  PAYMENT_NEEDS_RECONCILIATION:
    "Платёж уже обрабатывается. Дождитесь финального статуса или напишите в поддержку.",
  LIVE_SUBSCRIPTION_EXISTS: "У вас уже есть активная подписка.",
  PENDING_SUBSCRIPTION_NOT_CANCELABLE:
    "Незавершённый платёж нельзя отменить здесь. Дождитесь его финального статуса.",
  PRODUCT_NOT_FOUND: "Тариф временно недоступен.",
  NATAL_CONTEXT_MISSING: "Сначала заполните данные рождения в профиле.",
}

/**
 * User-facing Russian message for any error thrown by this client. Known
 * backend codes map to curated texts; unknown errors stay generic — raw
 * English backend text is never shown to the user.
 */
export function paymentErrorMessage(error: unknown): string {
  if (error instanceof PaymentApiError) {
    if (error.code && error.code in KNOWN_ERROR_MESSAGES) {
      return KNOWN_ERROR_MESSAGES[error.code]
    }
    if (error.status === 503) {
      return "Оплата временно недоступна. Попробуйте позже."
    }
    if (error.status === 401) {
      return "Требуется авторизация. Откройте приложение заново."
    }
  }
  return "Не удалось выполнить платёжный запрос. Попробуйте ещё раз."
}

export async function startPurchase(productSlug: OneTimeProductSlug): Promise<PurchaseStartResponse> {
  const res = await fetch(`${API_BASE}/api/payment/purchase/start`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ productSlug }),
  })
  if (!res.ok) {
    throw await buildPaymentApiError(res)
  }
  return PurchaseStartResponseWireSchema.parse(await res.json())
}

export async function getPurchaseStatus(purchaseId: string): Promise<PurchaseStatusResponse> {
  const res = await fetch(`${API_BASE}/api/payment/purchase/${purchaseId}`, {
    credentials: "include",
  })
  if (!res.ok) {
    throw await buildPaymentApiError(res)
  }
  return PurchaseStatusResponseWireSchema.parse(await res.json())
}
// END_BLOCK: PURCHASE
