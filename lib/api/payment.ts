// ############################################################################
// AI_HEADER: FRONTEND_API_PAYMENT — typed YooKassa billing client.
// ROLE: Typed facade for the billing endpoints (catalog, subscription
//       start/status/cancel, one-time purchase start/status) consumed by the
//       profile access card, paywall, natal CTA and horary purchase sheet.
//       Prices ALWAYS come from GET /api/payment/products — never hardcoded.
// DEPENDENCIES: packages/contracts (+ runtime wire schemas); lib/log/instrumented-fetch
// GRACE_ANCHORS: [FRONTEND_API_PAYMENT]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-PAYMENT
// purpose: Typed billing client with schema-validated responses, diagnostic contracts, and a stable
//   PaymentApiError carrying HTTP status + backend code for 401/402/404/409/503 handling via instrumentedFetch.
// owns:
//   - lib/api/payment.ts
// inputs: product slugs, purchase id, cancel reason.
// outputs: ProductsListResponse, SubscriptionStart/Status responses,
//   PurchaseStart/Status responses; PaymentApiError on non-ok.
// dependencies: packages/contracts (+ runtime wire schemas); lib/log/instrumented-fetch.
// side_effects: credentialed /api/payment/* GET and POST requests via instrumentedFetch.
// emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed, frontend.api_request_failed, frontend.api_response_invalid
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
//   - paymentErrorMessage
// semantic_blocks:
//   - TYPED_ERROR: PaymentApiError with status/code.
//   - ERROR_BUILD: map backend detail to the typed error.
//   - CATALOG: products list fetch.
//   - SUBSCRIPTION: start/status/cancel calls.
//   - PURCHASE: start/status calls.
//   - ERROR_TEXT: paymentErrorMessage RU mapping for user-facing flows.
// owned_tests:
//   - __tests__/api/payment-client.test.ts
//   - __tests__/billing/purchase-flow.test.ts
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
import { instrumentedFetch } from "@/lib/log/instrumented-fetch"

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
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-PAYMENT.getPaymentProducts
  // purpose: Fetch available payment products via instrumentedFetch with ProductsListResponse responseContract.
  // inputs: none
  // returns: Promise<ProductsListResponse>
  // side_effects: GET /api/payment/products via instrumentedFetch
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-PAYMENT.getPaymentProducts
  const res = await instrumentedFetch({
    operation: "payment.get_products",
    routeTemplate: "GET /api/payment/products",
    url: `${API_BASE}/api/payment/products`,
    init: { credentials: "include" },
    responseContract: {
      contractName: "ProductsListResponse",
      contractVersion: "v1",
      validate: (json) => {
        const parsed = ProductsListResponseWireSchema.safeParse(json)
        if (parsed.success) return { valid: true }
        const fields = parsed.error.issues.map((i) => String(i.path[0] || "unknown"))
        return { valid: false, missingFields: fields, invalidFieldTypes: fields }
      },
    },
  })
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
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-PAYMENT.startSubscription
  // purpose: Start a subscription purchase via instrumentedFetch with SubscriptionStartResponse responseContract.
  // inputs: productSlug — subscription product slug
  // returns: Promise<SubscriptionStartResponse>
  // side_effects: POST /api/payment/subscription/start via instrumentedFetch
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-PAYMENT.startSubscription
  const res = await instrumentedFetch({
    operation: "payment.start_subscription",
    routeTemplate: "POST /api/payment/subscription/start",
    url: `${API_BASE}/api/payment/subscription/start`,
    init: {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ productSlug }),
    },
    responseContract: {
      contractName: "SubscriptionStartResponse",
      contractVersion: "v1",
      validate: (json) => {
        const parsed = SubscriptionStartResponseWireSchema.safeParse(json)
        if (parsed.success) return { valid: true }
        const fields = parsed.error.issues.map((i) => String(i.path[0] || "unknown"))
        return { valid: false, missingFields: fields, invalidFieldTypes: fields }
      },
    },
  })
  if (!res.ok) {
    throw await buildPaymentApiError(res)
  }
  return SubscriptionStartResponseWireSchema.parse(await res.json())
}

export async function getSubscriptionStatus(): Promise<SubscriptionStatusResponse> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-PAYMENT.getSubscriptionStatus
  // purpose: Fetch current subscription status via instrumentedFetch with SubscriptionStatusResponse responseContract.
  // inputs: none
  // returns: Promise<SubscriptionStatusResponse>
  // side_effects: GET /api/payment/subscription/status via instrumentedFetch
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-PAYMENT.getSubscriptionStatus
  const res = await instrumentedFetch({
    operation: "payment.get_subscription_status",
    routeTemplate: "GET /api/payment/subscription/status",
    url: `${API_BASE}/api/payment/subscription/status`,
    init: { credentials: "include" },
    responseContract: {
      contractName: "SubscriptionStatusResponse",
      contractVersion: "v1",
      validate: (json) => {
        const parsed = SubscriptionStatusResponseWireSchema.safeParse(json)
        if (parsed.success) return { valid: true }
        const fields = parsed.error.issues.map((i) => String(i.path[0] || "unknown"))
        return { valid: false, missingFields: fields, invalidFieldTypes: fields }
      },
    },
  })
  if (!res.ok) {
    throw await buildPaymentApiError(res)
  }
  return SubscriptionStatusResponseWireSchema.parse(await res.json())
}

export async function cancelSubscription(reason?: string): Promise<void> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-PAYMENT.cancelSubscription
  // purpose: Cancel subscription via instrumentedFetch without JSON responseContract.
  // inputs: reason — optional cancellation reason string
  // returns: Promise<void>
  // side_effects: POST /api/payment/subscription/cancel via instrumentedFetch
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-PAYMENT.cancelSubscription
  const res = await instrumentedFetch({
    operation: "payment.cancel_subscription",
    routeTemplate: "POST /api/payment/subscription/cancel",
    url: `${API_BASE}/api/payment/subscription/cancel`,
    init: {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason: reason ?? null }),
    },
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
  | "synastry"

const KNOWN_ERROR_MESSAGES: Record<string, string> = {
  PAYMENT_NEEDS_RECONCILIATION:
    "Платёж уже обрабатывается. Дождитесь финального статуса или напишите в поддержку.",
  LIVE_SUBSCRIPTION_EXISTS: "У вас уже есть активная подписка.",
  PENDING_SUBSCRIPTION_NOT_CANCELABLE:
    "Незавершённый платёж нельзя отменить здесь. Дождитесь его финального статуса.",
  PRODUCT_NOT_FOUND: "Тариф временно недоступен.",
  NATAL_CONTEXT_MISSING: "Сначала заполните данные рождения в профиле.",
}

// START_BLOCK: ERROR_TEXT
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
// END_BLOCK: ERROR_TEXT

export async function startPurchase(productSlug: OneTimeProductSlug): Promise<PurchaseStartResponse> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-PAYMENT.startPurchase
  // purpose: Start one-time purchase via instrumentedFetch with PurchaseStartResponse responseContract.
  // inputs: productSlug — one-time product slug
  // returns: Promise<PurchaseStartResponse>
  // side_effects: POST /api/payment/purchase/start via instrumentedFetch
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-PAYMENT.startPurchase
  const res = await instrumentedFetch({
    operation: "payment.start_purchase",
    routeTemplate: "POST /api/payment/purchase/start",
    url: `${API_BASE}/api/payment/purchase/start`,
    init: {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ productSlug }),
    },
    responseContract: {
      contractName: "PurchaseStartResponse",
      contractVersion: "v1",
      validate: (json) => {
        const parsed = PurchaseStartResponseWireSchema.safeParse(json)
        if (parsed.success) return { valid: true }
        const fields = parsed.error.issues.map((i) => String(i.path[0] || "unknown"))
        return { valid: false, missingFields: fields, invalidFieldTypes: fields }
      },
    },
  })
  if (!res.ok) {
    throw await buildPaymentApiError(res)
  }
  return PurchaseStartResponseWireSchema.parse(await res.json())
}

export async function getPurchaseStatus(purchaseId: string): Promise<PurchaseStatusResponse> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-PAYMENT.getPurchaseStatus
  // purpose: Fetch one-time purchase status via instrumentedFetch with PurchaseStatusResponse responseContract.
  // inputs: purchaseId — purchase string ID
  // returns: Promise<PurchaseStatusResponse>
  // side_effects: GET /api/payment/purchase/{id} via instrumentedFetch
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-PAYMENT.getPurchaseStatus
  const res = await instrumentedFetch({
    operation: "payment.get_purchase_status",
    routeTemplate: "GET /api/payment/purchase/{id}",
    url: `${API_BASE}/api/payment/purchase/${purchaseId}`,
    init: { credentials: "include" },
    responseContract: {
      contractName: "PurchaseStatusResponse",
      contractVersion: "v1",
      validate: (json) => {
        const parsed = PurchaseStatusResponseWireSchema.safeParse(json)
        if (parsed.success) return { valid: true }
        const fields = parsed.error.issues.map((i) => String(i.path[0] || "unknown"))
        return { valid: false, missingFields: fields, invalidFieldTypes: fields }
      },
    },
  })
  if (!res.ok) {
    throw await buildPaymentApiError(res)
  }
  return PurchaseStatusResponseWireSchema.parse(await res.json())
}
// END_BLOCK: PURCHASE
