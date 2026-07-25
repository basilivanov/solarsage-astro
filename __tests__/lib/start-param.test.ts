// ############################################################################
// AI_HEADER: MODULE_TESTS_START_PARAM
// ROLE: Unit tests for Telegram start_param classification, Base58 rules, and sessionStorage helpers (Slice 01)
// DEPENDENCIES: vitest, lib/telegram/start-param
// GRACE_ANCHORS: [TELEGRAM_START_PARAM_TESTS]
// WAVE: W-NAMED-PROMO-CAMPAIGN
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-START-PARAM
// purpose: Validate start_param intent classification (referral vs promo vs ignored), Base58 constraints, sessionStorage pending promo token isolation, and URL query parameter cleanup.
// owns:
//   - __tests__/lib/start-param.test.ts
// inputs: raw start_param strings and browser location/sessionStorage mocks
// outputs: Vitest assertion results
// dependencies:
//   - M-TELEGRAM-START-PARAM (lib/telegram/start-param)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-START-PARAM

// START_MODULE_MAP: M-TESTS-START-PARAM
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - CLASSIFICATION_TESTS: test referral, promo, and ignored routing rules
//   - STORAGE_TESTS: test sessionStorage promo token persistence and validation
//   - URL_CLEANUP_TESTS: test tgWebAppStartParam removal from window location
// owned_tests:
//   - __tests__/lib/start-param.test.ts
// END_MODULE_MAP: M-TESTS-START-PARAM

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import {
  classifyStartParam,
  savePendingPromoToken,
  getPendingPromoToken,
  clearPendingPromoToken,
  cleanStartParamFromUrl,
  PROMO_PENDING_SESSION_KEY,
} from "@/lib/telegram/start-param"

describe("Telegram start_param Classifier & Storage — Slice 01", () => {
  beforeEach(() => {
    if (typeof window !== "undefined" && window.sessionStorage) {
      window.sessionStorage.clear()
    }
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe("classifyStartParam", () => {
    it("classifies all-digits as referral intent", () => {
      expect(classifyStartParam("123456")).toEqual({ kind: "referral", code: "123456" })
      expect(classifyStartParam("987654321012")).toEqual({ kind: "referral", code: "987654321012" })
    })

    it("classifies valid 12..16 char Base58 lowercase token with letters as promo intent", () => {
      expect(classifyStartParam("m7q4n9x2r5kd")).toEqual({ kind: "promo", token: "m7q4n9x2r5kd" })
      expect(classifyStartParam("abc23456789a")).toEqual({ kind: "promo", token: "abc23456789a" })
    })

    it("classifies all-digits as referral even if length is 12..16 chars (never promo)", () => {
      expect(classifyStartParam("123456789012345")).toEqual({ kind: "referral", code: "123456789012345" })
    })

    it("classifies short (<12 chars) or long (>16 chars) tokens as ignored", () => {
      expect(classifyStartParam("m7q4n9x2r5k")).toEqual({ kind: "ignored" }) // 11 chars
      expect(classifyStartParam("m7q4n9x2r5kdm7q4n")).toEqual({ kind: "ignored" }) // 17 chars
    })

    it("classifies inputs with leading/trailing whitespace as ignored (exact regex match without trim)", () => {
      expect(classifyStartParam(" 123456 ")).toEqual({ kind: "ignored" })
      expect(classifyStartParam(" m7q4n9x2r5kd ")).toEqual({ kind: "ignored" })
    })

    it("classifies tokens with uppercase, underscores, dashes, or non-Base58 chars (0, o, 1, l, i) as ignored", () => {
      expect(classifyStartParam("M7Q4N9X2R5KD")).toEqual({ kind: "ignored" })
      expect(classifyStartParam("m7q4_9x2-5kd")).toEqual({ kind: "ignored" })
      expect(classifyStartParam("m7q0n9x2r5kd")).toEqual({ kind: "ignored" })
      expect(classifyStartParam("m7qon9x2r5kd")).toEqual({ kind: "ignored" })
      expect(classifyStartParam("m7q1n9x2r5kd")).toEqual({ kind: "ignored" })
      expect(classifyStartParam("m7qln9x2r5kd")).toEqual({ kind: "ignored" })
      expect(classifyStartParam("m7qin9x2r5kd")).toEqual({ kind: "ignored" })
    })

    it("classifies null, undefined, whitespace, or empty strings as ignored", () => {
      expect(classifyStartParam(null)).toEqual({ kind: "ignored" })
      expect(classifyStartParam(undefined)).toEqual({ kind: "ignored" })
      expect(classifyStartParam("")).toEqual({ kind: "ignored" })
      expect(classifyStartParam("   ")).toEqual({ kind: "ignored" })
    })
  })

  describe("SessionStorage Promo Token Helpers", () => {
    it("stores valid promo token in sessionStorage and retrieves it successfully", () => {
      const saved = savePendingPromoToken("m7q4n9x2r5kd")
      expect(saved).toBe(true)
      expect(window.sessionStorage.getItem(PROMO_PENDING_SESSION_KEY)).toBe("m7q4n9x2r5kd")
      expect(getPendingPromoToken()).toBe("m7q4n9x2r5kd")
    })

    it("refuses to store invalid tokens or tokens with whitespace", () => {
      expect(savePendingPromoToken("invalid_token")).toBe(false)
      expect(savePendingPromoToken(" m7q4n9x2r5kd ")).toBe(false)
      expect(getPendingPromoToken()).toBeNull()
    })

    it("clears invalid stored token upon retrieval", () => {
      window.sessionStorage.setItem(PROMO_PENDING_SESSION_KEY, "invalid_stored_value")
      expect(getPendingPromoToken()).toBeNull()
      expect(window.sessionStorage.getItem(PROMO_PENDING_SESSION_KEY)).toBeNull()
    })

    it("clears token on clearPendingPromoToken call", () => {
      savePendingPromoToken("m7q4n9x2r5kd")
      clearPendingPromoToken()
      expect(getPendingPromoToken()).toBeNull()
    })

    it("uses sessionStorage ONLY and never writes to localStorage", () => {
      const localSetSpy = vi.spyOn(window.localStorage, "setItem")
      savePendingPromoToken("m7q4n9x2r5kd")
      expect(localSetSpy).not.toHaveBeenCalled()
    })
  })

  describe("Consumed Promo Token Marker (localStorage)", () => {
    beforeEach(() => {
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.clear()
      }
    })

    it("roundtrips the consumed marker for the same token only", async () => {
      const { markPromoTokenConsumed, isPromoTokenConsumed } = await import("@/lib/telegram/start-param")
      expect(isPromoTokenConsumed("m7q4n9x2r5kd")).toBe(false)
      markPromoTokenConsumed("m7q4n9x2r5kd")
      expect(isPromoTokenConsumed("m7q4n9x2r5kd")).toBe(true)
      expect(isPromoTokenConsumed("zcvsg8zjzmqb")).toBe(false)
    })

    it("uses localStorage ONLY for the consumed marker and never sessionStorage", async () => {
      const { markPromoTokenConsumed } = await import("@/lib/telegram/start-param")
      const sessionSetSpy = vi.spyOn(window.sessionStorage, "setItem")
      markPromoTokenConsumed("m7q4n9x2r5kd")
      expect(sessionSetSpy).not.toHaveBeenCalled()
      expect(window.localStorage.getItem("__astro_consumed_promo_token")).toBe("m7q4n9x2r5kd")
    })

    it("ignores empty and non-string tokens without throwing", async () => {
      const { markPromoTokenConsumed, isPromoTokenConsumed } = await import("@/lib/telegram/start-param")
      markPromoTokenConsumed("")
      markPromoTokenConsumed(undefined as unknown as string)
      expect(isPromoTokenConsumed("")).toBe(false)
      expect(window.localStorage.getItem("__astro_consumed_promo_token")).toBeNull()
    })
  })

  describe("cleanStartParamFromUrl", () => {
    it("removes tgWebAppStartParam query parameter from visible location while preserving path, hash, and other params", () => {
      const replaceStateSpy = vi.spyOn(window.history, "replaceState")

      delete (window as any).location
      ;(window as any).location = new URL("https://example.com/readings/election?tgWebAppStartParam=m7q4n9x2r5kd&tab=active#section-1")

      cleanStartParamFromUrl()

      expect(replaceStateSpy).toHaveBeenCalledWith(
        window.history.state,
        "",
        "/readings/election?tab=active#section-1"
      )
    })
  })
})
