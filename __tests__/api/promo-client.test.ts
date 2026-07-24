// ############################################################################
// AI_HEADER: FRONTEND_TEST_PROMO_CLIENT — unit tests for promo API client.
// ROLE: Validate previewPromo, redeemPromo, instrumentedFetch parameters, PromoApiError, and privacy contracts.
// DEPENDENCIES: vitest, lib/api/promo, lib/log/instrumented-fetch
// GRACE_ANCHORS: [PROMO_CLIENT_TESTS]
// WAVE: W-NAMED-PROMO-CAMPAIGN
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-PROMO-CLIENT
// purpose: Test instrumentedFetch options, success payload validation, backend error detail normalization, ALREADY_REDEEMED preservation, unknown error fallback, invalid contract failure, network exception propagation, and privacy safety (no token in errors).
// owns:
//   - __tests__/api/promo-client.test.ts
// inputs: mock instrumentedFetch responses and test tokens
// outputs: Vitest assertion results
// dependencies:
//   - M-FRONTEND-API-PROMO (lib/api/promo)
//   - M-LOG-INSTRUMENTED-FETCH (instrumentedFetch mock)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-PROMO-CLIENT

// START_MODULE_MAP: M-TESTS-PROMO-CLIENT
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - WIRING_TESTS: test operation, routeTemplate, method, headers, credentials, body
//   - SUCCESS_TESTS: test valid previewPromo and redeemPromo responses
//   - ERROR_TESTS: test PromoApiError status, code, detail normalization, and ALREADY_REDEEMED preservation
//   - CONTRACT_FAILURE_TESTS: test invalid 200 shapes and malformed error bodies
//   - PRIVACY_TESTS: test token absence in error objects and propagated exceptions
// owned_tests:
//   - __tests__/api/promo-client.test.ts
// END_MODULE_MAP: M-TESTS-PROMO-CLIENT

import { beforeEach, describe, expect, it, vi } from "vitest"

const { mockInstrumentedFetch } = vi.hoisted(() => ({
  mockInstrumentedFetch: vi.fn(),
}))

vi.mock("@/lib/log/instrumented-fetch", () => ({
  instrumentedFetch: mockInstrumentedFetch,
}))

import { previewPromo, redeemPromo, PromoApiError } from "@/lib/api/promo"
import type { PromoPreviewResponse, PromoRedeemResponse } from "@/packages/contracts"

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    statusText: status === 200 ? "OK" : "Error",
    headers: { "Content-Type": "application/json" },
  })
}

const VALID_PREVIEW_RESPONSE: PromoPreviewResponse = {
  offer: {
    displayName: "Летний Спешл 2026",
    accessDays: 30,
    bonusCredits: 50,
    unlockNatal: true,
  },
  profileComplete: true,
}

const VALID_REDEEM_RESPONSE: PromoRedeemResponse = {
  status: "redeemed",
  offer: {
    displayName: "Летний Спешл 2026",
    accessDays: 30,
    bonusCredits: 50,
    unlockNatal: true,
  },
  grants: {
    accessStartsAt: "2026-07-25T00:00:00Z",
    accessUntil: "2026-08-24T00:00:00Z",
    bonusCredits: 50,
    bonusCreditsExpiresAt: "2026-08-24T00:00:00Z",
    natalUnlocked: true,
    natalAlreadyOwned: false,
  },
}

describe("lib/api/promo", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe("previewPromo", () => {
    it("calls instrumentedFetch with correct routeTemplate, operation, credentials, and body", async () => {
      mockInstrumentedFetch.mockResolvedValueOnce(
        jsonResponse(200, VALID_PREVIEW_RESPONSE)
      )

      const res = await previewPromo("m7q4n9x2r5kd")

      expect(mockInstrumentedFetch).toHaveBeenCalledTimes(1)
      expect(mockInstrumentedFetch).toHaveBeenCalledWith({
        operation: "promo.preview",
        routeTemplate: "POST /api/promo/preview",
        url: "/api/promo/preview",
        init: {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          credentials: "include",
          body: JSON.stringify({ token: "m7q4n9x2r5kd" }),
        },
      })
      expect(res).toEqual(VALID_PREVIEW_RESPONSE)
    })

    it("parses valid preview response payload", async () => {
      mockInstrumentedFetch.mockResolvedValueOnce(
        jsonResponse(200, VALID_PREVIEW_RESPONSE)
      )

      const result = await previewPromo("m7q4n9x2r5kd")
      expect(result.offer.displayName).toBe("Летний Спешл 2026")
      expect(result.offer.accessDays).toBe(30)
      expect(result.offer.bonusCredits).toBe(50)
      expect(result.offer.unlockNatal).toBe(true)
      expect(result.profileComplete).toBe(true)
    })

    it("throws PromoApiError(UNKNOWN) on invalid 200 response contract shape", async () => {
      mockInstrumentedFetch.mockResolvedValue(
        jsonResponse(200, { invalid: "shape" })
      )

      try {
        await previewPromo("m7q4n9x2r5kd")
        expect.unreachable("should have thrown")
      } catch (err) {
        expect(err).toBeInstanceOf(PromoApiError)
        const promoErr = err as PromoApiError
        expect(promoErr.status).toBe(200)
        expect(promoErr.code).toBe("UNKNOWN")
        expect(promoErr.message).toBe("Недопустимый формат ответа сервера.")
      }
    })
  })

  describe("redeemPromo", () => {
    it("calls instrumentedFetch with correct routeTemplate, operation, credentials, and body", async () => {
      mockInstrumentedFetch.mockResolvedValueOnce(
        jsonResponse(200, VALID_REDEEM_RESPONSE)
      )

      const res = await redeemPromo("m7q4n9x2r5kd")

      expect(mockInstrumentedFetch).toHaveBeenCalledTimes(1)
      expect(mockInstrumentedFetch).toHaveBeenCalledWith({
        operation: "promo.redeem",
        routeTemplate: "POST /api/promo/redeem",
        url: "/api/promo/redeem",
        init: {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          credentials: "include",
          body: JSON.stringify({ token: "m7q4n9x2r5kd" }),
        },
      })
      expect(res).toEqual(VALID_REDEEM_RESPONSE)
    })

    it("parses valid redeem response payload", async () => {
      mockInstrumentedFetch.mockResolvedValueOnce(
        jsonResponse(200, VALID_REDEEM_RESPONSE)
      )

      const result = await redeemPromo("m7q4n9x2r5kd")
      expect(result.status).toBe("redeemed")
      expect(result.offer.displayName).toBe("Летний Спешл 2026")
      expect(result.grants.bonusCredits).toBe(50)
      expect(result.grants.natalUnlocked).toBe(true)
    })

    it("throws PromoApiError(UNKNOWN) on invalid 200 response contract shape", async () => {
      mockInstrumentedFetch.mockResolvedValueOnce(
        jsonResponse(200, { status: "invalid" })
      )

      try {
        await redeemPromo("m7q4n9x2r5kd")
        expect.unreachable("should have thrown")
      } catch (err) {
        expect(err).toBeInstanceOf(PromoApiError)
        const promoErr = err as PromoApiError
        expect(promoErr.status).toBe(200)
        expect(promoErr.code).toBe("UNKNOWN")
        expect(promoErr.message).toBe("Недопустимый формат ответа сервера.")
      }
    })
  })

  describe("error status and code preservation", () => {
    it("normalizes 400 INVALID_CODE backend error detail", async () => {
      mockInstrumentedFetch.mockResolvedValueOnce(
        jsonResponse(400, {
          detail: { code: "INVALID_CODE", message: "Неверный промокод" },
        })
      )

      try {
        await previewPromo("m7q4n9x2r5kd")
        expect.unreachable("should have thrown")
      } catch (err) {
        expect(err).toBeInstanceOf(PromoApiError)
        const promoErr = err as PromoApiError
        expect(promoErr.status).toBe(400)
        expect(promoErr.code).toBe("INVALID_CODE")
        expect(promoErr.message).toBe("Неверный промокод")
      }
    })

    it("normalizes 410 CAMPAIGN_EXPIRED backend error detail", async () => {
      mockInstrumentedFetch.mockResolvedValueOnce(
        jsonResponse(410, {
          detail: { code: "CAMPAIGN_EXPIRED", message: "Срок акции истёк" },
        })
      )

      try {
        await previewPromo("m7q4n9x2r5kd")
        expect.unreachable("should have thrown")
      } catch (err) {
        expect(err).toBeInstanceOf(PromoApiError)
        const promoErr = err as PromoApiError
        expect(promoErr.status).toBe(410)
        expect(promoErr.code).toBe("CAMPAIGN_EXPIRED")
        expect(promoErr.message).toBe("Срок акции истёк")
      }
    })

    it("normalizes 409 CAMPAIGN_FULL backend error detail", async () => {
      mockInstrumentedFetch.mockResolvedValueOnce(
        jsonResponse(409, {
          detail: { code: "CAMPAIGN_FULL", message: "Все промокоды использованы" },
        })
      )

      try {
        await previewPromo("m7q4n9x2r5kd")
        expect.unreachable("should have thrown")
      } catch (err) {
        expect(err).toBeInstanceOf(PromoApiError)
        const promoErr = err as PromoApiError
        expect(promoErr.status).toBe(409)
        expect(promoErr.code).toBe("CAMPAIGN_FULL")
        expect(promoErr.message).toBe("Все промокоды использованы")
      }
    })

    it("preserves typed ALREADY_REDEEMED code without converting to success", async () => {
      mockInstrumentedFetch.mockResolvedValueOnce(
        jsonResponse(409, {
          detail: {
            code: "ALREADY_REDEEMED",
            message: "Вы уже активировали этот промокод",
          },
        })
      )

      try {
        await redeemPromo("m7q4n9x2r5kd")
        expect.unreachable("should have thrown")
      } catch (err) {
        expect(err).toBeInstanceOf(PromoApiError)
        const promoErr = err as PromoApiError
        expect(promoErr.status).toBe(409)
        expect(promoErr.code).toBe("ALREADY_REDEEMED")
        expect(promoErr.message).toBe("Вы уже активировали этот промокод")
      }
    })

    it("normalizes 409 PROFILE_INCOMPLETE backend error detail", async () => {
      mockInstrumentedFetch.mockResolvedValueOnce(
        jsonResponse(409, {
          detail: { code: "PROFILE_INCOMPLETE", message: "Заполните профиль" },
        })
      )

      try {
        await redeemPromo("m7q4n9x2r5kd")
        expect.unreachable("should have thrown")
      } catch (err) {
        expect(err).toBeInstanceOf(PromoApiError)
        const promoErr = err as PromoApiError
        expect(promoErr.status).toBe(409)
        expect(promoErr.code).toBe("PROFILE_INCOMPLETE")
        expect(promoErr.message).toBe("Заполните профиль")
      }
    })

    it("handles malformed/non-JSON error body as UNKNOWN fallback", async () => {
      mockInstrumentedFetch.mockResolvedValueOnce(
        new Response("<html>500 Internal Server Error</html>", {
          status: 500,
          statusText: "Internal Server Error",
          headers: { "Content-Type": "text/html" },
        })
      )

      try {
        await previewPromo("m7q4n9x2r5kd")
        expect.unreachable("should have thrown")
      } catch (err) {
        expect(err).toBeInstanceOf(PromoApiError)
        const promoErr = err as PromoApiError
        expect(promoErr.status).toBe(500)
        expect(promoErr.code).toBe("UNKNOWN")
        expect(promoErr.message).toBe("Не удалось проверить промокод.")
      }
    })

    it("handles unknown error code in valid JSON error detail as UNKNOWN fallback", async () => {
      mockInstrumentedFetch.mockResolvedValueOnce(
        jsonResponse(500, { detail: { code: "SOME_UNEXPECTED_CODE", message: "Fail" } })
      )

      try {
        await redeemPromo("m7q4n9x2r5kd")
        expect.unreachable("should have thrown")
      } catch (err) {
        expect(err).toBeInstanceOf(PromoApiError)
        const promoErr = err as PromoApiError
        expect(promoErr.status).toBe(500)
        expect(promoErr.code).toBe("UNKNOWN")
        expect(promoErr.message).toBe("Не удалось активировать промокод.")
      }
    })
  })

  describe("network exceptions & privacy", () => {
    it("propagates network exceptions untouched", async () => {
      const netError = new TypeError("Failed to fetch")
      mockInstrumentedFetch.mockRejectedValueOnce(netError)

      await expect(previewPromo("m7q4n9x2r5kd")).rejects.toThrow(netError)
    })

    it("never includes token in PromoApiError message, status, or properties", async () => {
      const sentinelToken = "sentinel_secret_token_12345"

      mockInstrumentedFetch.mockResolvedValueOnce(
        jsonResponse(400, {
          detail: { code: "INVALID_CODE", message: "Неверный промокод" },
        })
      )

      try {
        await previewPromo(sentinelToken)
        expect.unreachable("should have thrown")
      } catch (err) {
        expect(err).toBeInstanceOf(PromoApiError)
        const promoErr = err as PromoApiError
        expect(promoErr.message).not.toContain(sentinelToken)
        expect(JSON.stringify(promoErr)).not.toContain(sentinelToken)
      }
    })
  })
})
