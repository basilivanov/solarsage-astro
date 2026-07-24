// ############################################################################
// AI_HEADER: TEST_PAYMENT_CLIENT — typed billing client contract.
// ROLE: Proves lib/api/payment.ts: instrumentedFetch wiring, schema-validated success payloads,
//       responseContract validators, and PaymentApiError status/code preservation for 401/404/409/503.
// DEPENDENCIES: vitest, lib/api/payment, lib/log/instrumented-fetch
// GRACE_ANCHORS: [PAYMENT_CLIENT_TESTS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-PAYMENT-CLIENT
// purpose: Validate instrumentedFetch wiring, operation labels, route templates, POST inits, responseContract validators, cancelSubscription absence of contract, and RU error message mappings for payment client.
// owns:
//   - __tests__/api/payment-client.test.ts
// inputs: mock instrumentedFetch responses and wire fixtures
// outputs: Vitest assertion results
// dependencies:
//   - M-FRONTEND-API-PAYMENT (lib/api/payment)
//   - M-LOG-INSTRUMENTED-FETCH (instrumentedFetch mock)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-PAYMENT-CLIENT

// START_MODULE_MAP: M-TESTS-PAYMENT-CLIENT
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - WIRING_TESTS: test operation, routeTemplate and init for 6 payment calls
//   - CONTRACT_VALIDATOR_TESTS: test 5 responseContract validators and cancelSubscription contract absence
//   - ERROR_MAPPING_TESTS: test PaymentApiError status/code and paymentErrorMessage RU text mappings
// owned_tests:
//   - __tests__/api/payment-client.test.ts
// END_MODULE_MAP: M-TESTS-PAYMENT-CLIENT

import { beforeEach, afterEach, describe, expect, it, vi } from "vitest"

const { mockInstrumentedFetch } = vi.hoisted(() => ({
  mockInstrumentedFetch: vi.fn(),
}))

vi.mock("@/lib/log/instrumented-fetch", () => ({
  instrumentedFetch: mockInstrumentedFetch,
}))

import {
  PaymentApiError,
  getPaymentProducts,
  startSubscription,
  getSubscriptionStatus,
  cancelSubscription,
  startPurchase,
  getPurchaseStatus,
  paymentErrorMessage,
} from "@/lib/api/payment"

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    statusText: status === 200 ? "OK" : "ERR",
    headers: { "Content-Type": "application/json" },
  })
}

const VALID_PRODUCTS = {
  products: [
    {
      slug: "subscription_month",
      name: "Подписка на 1 месяц",
      description: null,
      productType: "subscription_recurrent",
      priceKopecks: 9900,
      currency: "RUB",
      periodDays: 30,
      horaryQuota: null,
    },
  ],
}

const VALID_SUB_START = {
  subscriptionId: "11111111-1111-1111-1111-111111111111",
  productSlug: "subscription_month",
  providerPaymentId: "prov-1",
  confirmationUrl: "https://pay.example/c",
  status: "pending",
}

const VALID_SUB_STATUS = {
  subscriptionId: "11111111-1111-1111-1111-111111111111",
  productSlug: "subscription_month",
  status: "active",
  hasAccess: true,
  expiresAt: "2026-12-31T00:00:00Z",
  autoRenew: true,
}

const VALID_PURCHASE_START = {
  purchaseId: "22222222-2222-2222-2222-222222222222",
  productSlug: "natal_full_report",
  providerPaymentId: "prov-2",
  confirmationUrl: "https://pay.example/p",
  status: "pending",
}

const VALID_PURCHASE_STATUS = {
  purchaseId: "22222222-2222-2222-2222-222222222222",
  productSlug: "natal_full_report",
  status: "succeeded",
  paidAt: "2026-07-24T12:00:00Z",
}

describe("lib/api/payment typed client — Slice 10 Instrumentation & Contracts", () => {
  beforeEach(() => {
    mockInstrumentedFetch.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("getPaymentProducts returns validated catalog via instrumentedFetch with ProductsListResponse contract", async () => {
    mockInstrumentedFetch.mockResolvedValue(jsonResponse(200, VALID_PRODUCTS))
    const result = await getPaymentProducts()

    expect(result.products[0].slug).toBe("subscription_month")
    expect(result.products[0].priceKopecks).toBe(9900)

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "payment.get_products",
        routeTemplate: "GET /api/payment/products",
        url: "/api/payment/products",
        init: { credentials: "include" },
        responseContract: expect.objectContaining({
          contractName: "ProductsListResponse",
          contractVersion: "v1",
        }),
      })
    )

    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate(VALID_PRODUCTS)).toEqual({ valid: true })
    expect(contract.validate({})).toEqual(
      expect.objectContaining({ valid: false, missingFields: expect.any(Array) })
    )
  })

  it("getPaymentProducts 503 throws PaymentApiError with status", async () => {
    mockInstrumentedFetch.mockResolvedValue(jsonResponse(503, { detail: "Payments are not available" }))
    const err = await getPaymentProducts().catch((e: unknown) => e)
    expect(err).toBeInstanceOf(PaymentApiError)
    expect((err as PaymentApiError).status).toBe(503)
  })

  it("startSubscription posts slug and validates SubscriptionStartResponse contract", async () => {
    mockInstrumentedFetch.mockResolvedValue(jsonResponse(200, VALID_SUB_START))
    const result = await startSubscription("subscription_month")

    expect(result.confirmationUrl).toBe("https://pay.example/c")

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "payment.start_subscription",
        routeTemplate: "POST /api/payment/subscription/start",
        url: "/api/payment/subscription/start",
        init: expect.objectContaining({
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ productSlug: "subscription_month" }),
        }),
        responseContract: expect.objectContaining({
          contractName: "SubscriptionStartResponse",
          contractVersion: "v1",
        }),
      })
    )

    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate(VALID_SUB_START)).toEqual({ valid: true })
    expect(contract.validate({})).toEqual(expect.objectContaining({ valid: false }))
  })

  it("getSubscriptionStatus passes correct operation, routeTemplate, and SubscriptionStatusResponse contract", async () => {
    mockInstrumentedFetch.mockResolvedValue(jsonResponse(200, VALID_SUB_STATUS))
    const result = await getSubscriptionStatus()

    expect(result.status).toBe("active")

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "payment.get_subscription_status",
        routeTemplate: "GET /api/payment/subscription/status",
        url: "/api/payment/subscription/status",
        init: { credentials: "include" },
        responseContract: expect.objectContaining({
          contractName: "SubscriptionStatusResponse",
          contractVersion: "v1",
        }),
      })
    )

    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate(VALID_SUB_STATUS)).toEqual({ valid: true })
    expect(contract.validate({})).toEqual(expect.objectContaining({ valid: false }))
  })

  it("cancelSubscription posts reason, uses cancel operation, and has NO responseContract", async () => {
    mockInstrumentedFetch.mockResolvedValue(new Response(null, { status: 204 }))

    await cancelSubscription("User requested")

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "payment.cancel_subscription",
        routeTemplate: "POST /api/payment/subscription/cancel",
        url: "/api/payment/subscription/cancel",
        init: expect.objectContaining({
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reason: "User requested" }),
        }),
      })
    )

    const callOpts = mockInstrumentedFetch.mock.calls[0][0]
    expect(callOpts.responseContract).toBeUndefined()
  })

  it("startPurchase posts product slug, validates PurchaseStartResponse contract, and preserves 409 code", async () => {
    // 200 OK Case
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(200, VALID_PURCHASE_START))
    const result = await startPurchase("natal_full_report")

    expect(result.purchaseId).toBe("22222222-2222-2222-2222-222222222222")
    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "payment.start_purchase",
        routeTemplate: "POST /api/payment/purchase/start",
        url: "/api/payment/purchase/start",
        init: expect.objectContaining({
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ productSlug: "natal_full_report" }),
        }),
        responseContract: expect.objectContaining({
          contractName: "PurchaseStartResponse",
          contractVersion: "v1",
        }),
      })
    )

    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate(VALID_PURCHASE_START)).toEqual({ valid: true })
    expect(contract.validate({})).toEqual(expect.objectContaining({ valid: false }))

    // 409 Error Case
    mockInstrumentedFetch.mockResolvedValueOnce(
      jsonResponse(409, { detail: { code: "ALREADY_ENTITLED", message: "Report already purchased" } })
    )
    const err = await startPurchase("natal_full_report").catch((e: unknown) => e)
    expect(err).toBeInstanceOf(PaymentApiError)
    expect((err as PaymentApiError).status).toBe(409)
    expect((err as PaymentApiError).code).toBe("ALREADY_ENTITLED")
  })

  it("getPurchaseStatus uses dynamic purchaseId in URL while routeTemplate is GET /api/payment/purchase/{id}, validating contract and 404 code", async () => {
    // 200 OK Case
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(200, VALID_PURCHASE_STATUS))
    const res = await getPurchaseStatus("pur-999")
    expect(res.status).toBe("succeeded")

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "payment.get_purchase_status",
        routeTemplate: "GET /api/payment/purchase/{id}",
        url: "/api/payment/purchase/pur-999",
        init: { credentials: "include" },
        responseContract: expect.objectContaining({
          contractName: "PurchaseStatusResponse",
          contractVersion: "v1",
        }),
      })
    )

    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate(VALID_PURCHASE_STATUS)).toEqual({ valid: true })
    expect(contract.validate({})).toEqual(expect.objectContaining({ valid: false }))

    // 404 Error Case
    mockInstrumentedFetch.mockResolvedValueOnce(
      jsonResponse(404, { detail: { code: "PURCHASE_NOT_FOUND", message: "Purchase not found" } })
    )
    const err = await getPurchaseStatus("missing").catch((e: unknown) => e)
    expect((err as PaymentApiError).status).toBe(404)
    expect((err as PaymentApiError).code).toBe("PURCHASE_NOT_FOUND")
  })
})

describe("paymentErrorMessage — RU mapping, never raw backend English", () => {
  it("maps known codes to curated Russian texts", () => {
    const reconciliation = new PaymentApiError({
      status: 409,
      code: "PAYMENT_NEEDS_RECONCILIATION",
      message: "A previous payment attempt is being reconciled",
    })
    expect(paymentErrorMessage(reconciliation)).toContain("обрабатывается")
    expect(paymentErrorMessage(reconciliation)).not.toContain("reconciled")

    const liveSub = new PaymentApiError({
      status: 409,
      code: "LIVE_SUBSCRIPTION_EXISTS",
      message: "A live subscription already exists",
    })
    expect(paymentErrorMessage(liveSub)).toBe("У вас уже есть активная подписка.")

    const pendingCancel = new PaymentApiError({
      status: 409,
      code: "PENDING_SUBSCRIPTION_NOT_CANCELABLE",
      message: "The pending payment remains open and payable",
    })
    expect(paymentErrorMessage(pendingCancel)).toContain("Незавершённый платёж")

    const product = new PaymentApiError({ status: 404, code: "PRODUCT_NOT_FOUND", message: "Product not found" })
    expect(paymentErrorMessage(product)).toBe("Тариф временно недоступен.")
  })

  it("falls back by status and stays generic for unknown errors", () => {
    expect(paymentErrorMessage(new PaymentApiError({ status: 503, message: "x" }))).toContain("временно недоступна")
    expect(paymentErrorMessage(new PaymentApiError({ status: 401, message: "x" }))).toContain("авторизация")
    expect(paymentErrorMessage(new PaymentApiError({ status: 500, code: "SOME_UNKNOWN", message: "raw" }))).toContain(
      "Не удалось выполнить платёжный запрос"
    )
    expect(paymentErrorMessage(new Error("boom"))).toContain("Не удалось выполнить платёжный запрос")
  })
})
