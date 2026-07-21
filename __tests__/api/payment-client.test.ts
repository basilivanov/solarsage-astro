// ############################################################################
// AI_HEADER: TEST_PAYMENT_CLIENT — typed billing client contract.
// ROLE: Proves lib/api/payment.ts: schema-validated success payloads and
//       PaymentApiError status/code preservation for 401/404/409/503.
// ############################################################################

import { beforeEach, describe, expect, it, vi } from "vitest"

import {
  PaymentApiError,
  getPaymentProducts,
  getPurchaseStatus,
  paymentErrorMessage,
  startPurchase,
  startSubscription,
} from "@/lib/api/payment"

const mockFetch = vi.fn()
globalThis.fetch = mockFetch as unknown as typeof fetch

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    statusText: status === 200 ? "OK" : "ERR",
    headers: { "Content-Type": "application/json" },
  })
}

const PRODUCTS = {
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

describe("lib/api/payment typed client", () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it("getPaymentProducts returns validated catalog", async () => {
    mockFetch.mockResolvedValue(jsonResponse(200, PRODUCTS))
    const result = await getPaymentProducts()
    expect(result.products[0].slug).toBe("subscription_month")
    expect(result.products[0].priceKopecks).toBe(9900)
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/payment/products",
      expect.objectContaining({ credentials: "include" })
    )
  })

  it("getPaymentProducts 503 throws PaymentApiError with status", async () => {
    mockFetch.mockResolvedValue(jsonResponse(503, { detail: "Payments are not available" }))
    const err = await getPaymentProducts().catch((e: unknown) => e)
    expect(err).toBeInstanceOf(PaymentApiError)
    expect((err as PaymentApiError).status).toBe(503)
  })

  it("startSubscription posts slug and validates response", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(200, {
        subscriptionId: "11111111-1111-1111-1111-111111111111",
        productSlug: "subscription_month",
        providerPaymentId: "prov-1",
        confirmationUrl: "https://pay.example/c",
        status: "pending",
      })
    )
    const result = await startSubscription("subscription_month")
    expect(result.confirmationUrl).toBe("https://pay.example/c")
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit]
    expect(JSON.parse(String(init.body))).toEqual({ productSlug: "subscription_month" })
  })

  it("startPurchase 409 preserves backend code (ALREADY_ENTITLED)", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(409, { detail: { code: "ALREADY_ENTITLED", message: "Report already purchased" } })
    )
    const err = await startPurchase("natal_full_report").catch((e: unknown) => e)
    expect(err).toBeInstanceOf(PaymentApiError)
    expect((err as PaymentApiError).status).toBe(409)
    expect((err as PaymentApiError).code).toBe("ALREADY_ENTITLED")
  })

  it("getPurchaseStatus 404 throws PaymentApiError with PURCHASE_NOT_FOUND", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(404, { detail: { code: "PURCHASE_NOT_FOUND", message: "Purchase not found" } })
    )
    const err = await getPurchaseStatus("missing").catch((e: unknown) => e)
    expect((err as PaymentApiError).status).toBe(404)
    expect((err as PaymentApiError).code).toBe("PURCHASE_NOT_FOUND")
  })

  it("getPurchaseStatus validates the wire shape", async () => {
    mockFetch.mockResolvedValue(jsonResponse(200, { bogus: true }))
    await expect(getPurchaseStatus("id")).rejects.toThrow()
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
