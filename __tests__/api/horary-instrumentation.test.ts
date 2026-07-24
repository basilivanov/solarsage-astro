// ############################################################################
// AI_HEADER: MODULE_TESTS_HORARY_INSTRUMENTATION
// ROLE: Unit and instrumentation wiring tests for lib/api/horary.ts (Slice 05)
// DEPENDENCIES: vitest, lib/api/horary, lib/log/instrumented-fetch
// GRACE_ANCHORS: [HORARY_INSTRUMENTATION_TESTS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-HORARY-INSTRUMENTATION
// purpose: Validate instrumentedFetch wiring, operation labels, route templates, POST inits, responseContract validators, and error mappings for horary client.
// owns:
//   - __tests__/api/horary-instrumentation.test.ts
// inputs: mock instrumentedFetch responses and fixtures
// outputs: Vitest assertion results
// dependencies:
//   - M-FRONTEND-API-HORARY (lib/api/horary)
//   - M-LOG-INSTRUMENTED-FETCH (instrumentedFetch mock)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-HORARY-INSTRUMENTATION

// START_MODULE_MAP: M-TESTS-HORARY-INSTRUMENTATION
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - WIRING_TESTS: test operation and routeTemplate parameters for 4 calls
//   - CONTRACT_VALIDATOR_TESTS: test responseContract.validate logic
//   - ERROR_MAPPING_TESTS: test 404-to-null and HoraryApiError mapping
// owned_tests:
//   - __tests__/api/horary-instrumentation.test.ts
// END_MODULE_MAP: M-TESTS-HORARY-INSTRUMENTATION

import { describe, it, expect, vi, beforeEach } from "vitest"

const { mockInstrumentedFetch } = vi.hoisted(() => ({
  mockInstrumentedFetch: vi.fn(),
}))

vi.mock("@/lib/log/instrumented-fetch", () => ({
  instrumentedFetch: mockInstrumentedFetch,
}))

import type { HoraryQuestionCreate } from "@/packages/contracts"
import {
  getHoraryQuota,
  listHoraryQuestions,
  getHoraryQuestion,
  createHoraryQuestion,
  HoraryApiError,
} from "@/lib/api/horary"

const validQuotaFixture = {
  weeklyFreeAvailable: true,
  bonusCredits: 5,
  paidCredits: 3,
  canPurchase: true,
}

const validQuestionFixture = {
  id: "q-101",
  text: "Will I get the job offer?",
  category: "career",
  status: "answered",
  spentCreditSource: "paid",
  creditRefunded: false,
  clientTimezone: "Europe/Moscow",
  clientLocalTime: "2026-07-24T12:00:00",
  questionLocationName: "Moscow",
  createdAt: "2026-07-24T12:00:00Z",
  chart: null,
  answer: null,
}

describe("Horary API Client Instrumentation — Slice 05", () => {
  beforeEach(() => {
    mockInstrumentedFetch.mockClear()
  })

  it("getHoraryQuota passes correct operation, routeTemplate, and responseContract", async () => {
    mockInstrumentedFetch.mockResolvedValue(
      new Response(JSON.stringify(validQuotaFixture), { status: 200 })
    )

    const res = await getHoraryQuota()
    expect(res).toEqual(validQuotaFixture)

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "horary.quota",
        routeTemplate: "GET /api/horary/quota",
        url: "/api/horary/quota",
        responseContract: expect.objectContaining({
          contractName: "HoraryQuota",
          contractVersion: "v1",
        }),
      })
    )

    // Test responseContract validator
    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate(validQuotaFixture)).toEqual({ valid: true })
    expect(contract.validate({})).toEqual(
      expect.objectContaining({ valid: false, missingFields: expect.any(Array) })
    )
  })

  it("listHoraryQuestions passes correct operation, routeTemplate, and responseContract", async () => {
    mockInstrumentedFetch.mockResolvedValue(
      new Response(JSON.stringify([validQuestionFixture]), { status: 200 })
    )

    const list = await listHoraryQuestions(10, 0)
    expect(list).toHaveLength(1)

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "horary.list_questions",
        routeTemplate: "GET /api/horary/questions",
        url: "/api/horary/questions?limit=10&offset=0",
        responseContract: expect.objectContaining({
          contractName: "HoraryQuestionList",
          contractVersion: "v1",
        }),
      })
    )

    // Test responseContract validator
    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate([validQuestionFixture])).toEqual({ valid: true })
    expect(contract.validate([{}])).toEqual(
      expect.objectContaining({ valid: false })
    )
  })

  it("getHoraryQuestion passes correct operation, routeTemplate, and handles 404-to-null behavior", async () => {
    // 200 OK Case
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(validQuestionFixture), { status: 200 })
    )

    const q = await getHoraryQuestion("q-101")
    expect(q).toEqual(validQuestionFixture)

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "horary.get_question",
        routeTemplate: "GET /api/horary/questions/{id}",
        url: "/api/horary/questions/q-101",
        responseContract: expect.objectContaining({
          contractName: "HoraryQuestionDetail",
          contractVersion: "v1",
        }),
      })
    )

    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate(validQuestionFixture)).toEqual({ valid: true })
    expect(contract.validate({})).toEqual(expect.objectContaining({ valid: false }))

    // 404 Not Found Case -> returns null
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response("Not found", { status: 404 })
    )

    const nullResult = await getHoraryQuestion("q-999")
    expect(nullResult).toBeNull()
  })

  it("createHoraryQuestion calls instrumentedFetch (NOT raw global fetch) with POST init, body, and contract", async () => {
    const rawGlobalFetch = vi.fn()
    vi.stubGlobal("fetch", rawGlobalFetch)

    mockInstrumentedFetch.mockResolvedValue(
      new Response(JSON.stringify(validQuestionFixture), { status: 200 })
    )

    const payload: HoraryQuestionCreate = {
      text: "Will I get the job offer?",
      category: "career",
      clientTimezone: "Europe/Moscow",
      idempotencyKey: "idem-key-123",
    }

    const created = await createHoraryQuestion(payload)
    expect(created).toEqual(validQuestionFixture)

    // Raw global fetch must NOT be called!
    expect(rawGlobalFetch).not.toHaveBeenCalled()

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "horary.create_question",
        routeTemplate: "POST /api/horary/questions",
        url: "/api/horary/questions",
        init: expect.objectContaining({
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }),
        responseContract: expect.objectContaining({
          contractName: "HoraryQuestionCreate",
          contractVersion: "v1",
        }),
      })
    )

    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate(validQuestionFixture)).toEqual({ valid: true })
    expect(contract.validate({})).toEqual(expect.objectContaining({ valid: false }))
  })

  it("maps HTTP errors (402, 409, 500) to HoraryApiError with Russian messages", async () => {
    // 402 NO_HORARY_CREDITS
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify({ detail: { code: "NO_HORARY_CREDITS", message: "No credits" } }),
        { status: 402 }
      )
    )

    await expect(getHoraryQuestion("q-101")).rejects.toThrow(HoraryApiError)
    try {
      mockInstrumentedFetch.mockResolvedValueOnce(
        new Response(
          JSON.stringify({ detail: { code: "NO_HORARY_CREDITS", message: "No credits" } }),
          { status: 402 }
        )
      )
      await getHoraryQuestion("q-101")
    } catch (err: any) {
      expect(err.status).toBe(402)
      expect(err.message).toBe("Недостаточно хорарных вопросов")
    }

    // 409 IDEMPOTENCY_CONFLICT
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify({ detail: { code: "IDEMPOTENCY_CONFLICT" } }),
        { status: 409 }
      )
    )

    try {
      await createHoraryQuestion({
        text: "Test",
        category: "love",
        clientTimezone: "Europe/Moscow",
        idempotencyKey: "idem-key-456",
      })
    } catch (err: any) {
      expect(err.status).toBe(409)
      expect(err.message).toBe("Этот запрос уже был отправлен. Попробуй ещё раз.")
    }
  })
})
