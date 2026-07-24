// ############################################################################
// AI_HEADER: MODULE_TESTS_ELECTION_API
// ROLE: Unit and instrumentation wiring tests for lib/api/election.ts (Slice 08)
// DEPENDENCIES: vitest, lib/api/election, lib/log/instrumented-fetch, lib/contracts/election
// GRACE_ANCHORS: [ELECTION_API_TESTS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-ELECTION-API
// purpose: Validate instrumentedFetch wiring, operation labels, route templates, POST inits, responseContract validators, 404-to-null and idempotency key handling for election client.
// owns:
//   - __tests__/lib/election-api.test.ts
// inputs: mock instrumentedFetch responses and raw Zod fixtures
// outputs: Vitest assertion results
// dependencies:
//   - M-FRONTEND-API-ELECTION (lib/api/election)
//   - M-LOG-INSTRUMENTED-FETCH (instrumentedFetch mock)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-ELECTION-API

// START_MODULE_MAP: M-TESTS-ELECTION-API
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - ZOD_V2_TESTS: test ElectionSearchSchema parsing
//   - WIRING_TESTS: test operation and routeTemplate parameters for 4 calls
//   - CONTRACT_VALIDATOR_TESTS: test responseContract.validate logic
//   - REGRESSION_TESTS: test 404-to-null and create POST body / idempotencyKey
// owned_tests:
//   - __tests__/lib/election-api.test.ts
// END_MODULE_MAP: M-TESTS-ELECTION-API

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { ElectionSearchSchema } from "@/lib/contracts/election"

const { mockInstrumentedFetch } = vi.hoisted(() => ({
  mockInstrumentedFetch: vi.fn(),
}))

vi.mock("@/lib/log/instrumented-fetch", () => ({
  instrumentedFetch: mockInstrumentedFetch,
}))

import {
  getElectionQuota,
  listElectionSearches,
  getElectionSearch,
  createElectionSearch,
} from "@/lib/api/election"

const rawV2Payload = {
  id: "34cdf627-7ca2-4864-b3dd-42b96e0515f7",
  eventType: "relations:wedding",
  windowFrom: "2026-08-01",
  windowTo: "2026-08-05",
  status: "done",
  createdAt: "2026-07-24T08:00:00Z",
  result: {
    event: "relations:wedding",
    best_days: [
      {
        date: "2026-08-01",
        score: 85,
        label: "great",
        reasons: ["Луна в Тельце"],
        moon_sign_ru: "Телец",
        phase_pct: 75,
        voc_intervals: ["10:00-14:00"],
      },
    ],
    avoid_days: [],
    days: [
      {
        date: "2026-08-01",
        score: 85,
        label: "great",
        reasons: ["Луна в Тельце"],
      },
    ],
    facts: {
      event: { category: "relations", sub: "wedding", label: "Свадьба" },
      personal: { natal_moon_sign_ru: "Телец", resonates: true },
    },
    narrative: {
      hero_reason: "Идеальный день.",
      hero_personal: "Совпадает с наталом.",
      hero_plain: "Стабильный знак.",
      hero_hours: "До 14:00.",
      day_notes: [{ date: "2026-08-01", note: "Хороший выбор." }],
      avoid_notes: [],
    },
  },
}

const validQuotaFixture = {
  weeklyFreeAvailable: true,
  bonusCredits: 5,
  paidCredits: 3,
  canPurchase: true,
}

describe("Election Zod Contracts v2", () => {
  it("parses valid top-level camelCase search payload with v2 result payload containing facts and narrative", () => {
    const parsed = ElectionSearchSchema.parse(rawV2Payload)
    expect(parsed.eventType).toBe("relations:wedding")
    expect(parsed.result?.facts?.event?.category).toBe("relations")
    expect(parsed.result?.narrative?.hero_reason).toBe("Идеальный день.")
  })
})

describe("Election API Client Instrumentation — Slice 08", () => {
  beforeEach(() => {
    mockInstrumentedFetch.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("getElectionQuota passes correct operation, routeTemplate, and responseContract validator", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(validQuotaFixture), { status: 200 })
    )

    const res = await getElectionQuota()
    expect(res).toEqual(validQuotaFixture)

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "election.quota",
        routeTemplate: "GET /api/election/quota",
        url: "/api/election/quota",
        responseContract: expect.objectContaining({
          contractName: "HoraryQuota",
          contractVersion: "v1",
        }),
      })
    )

    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate(validQuotaFixture)).toEqual({ valid: true })
    expect(contract.validate({})).toEqual(
      expect.objectContaining({ valid: false, missingFields: expect.any(Array) })
    )
  })

  it("listElectionSearches passes correct operation, routeTemplate, and responseContract validator", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(JSON.stringify([rawV2Payload]), { status: 200 })
    )

    const list = await listElectionSearches(10, 0)
    expect(list).toHaveLength(1)

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "election.list_searches",
        routeTemplate: "GET /api/election/searches",
        url: "/api/election/searches?limit=10&offset=0",
        responseContract: expect.objectContaining({
          contractName: "ElectionSearchList",
          contractVersion: "v1",
        }),
      })
    )

    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate([rawV2Payload])).toEqual({ valid: true })
    expect(contract.validate([{}])).toEqual(expect.objectContaining({ valid: false }))
  })

  it("getElectionSearch passes correct operation, routeTemplate, and handles 404-to-null regression", async () => {
    // 200 OK Case
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(rawV2Payload), { status: 200 })
    )

    const detail = await getElectionSearch("34cdf627-7ca2-4864-b3dd-42b96e0515f7")
    expect(detail?.eventType).toBe("relations:wedding")

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "election.get_search",
        routeTemplate: "GET /api/election/searches/{id}",
        url: "/api/election/searches/34cdf627-7ca2-4864-b3dd-42b96e0515f7",
        responseContract: expect.objectContaining({
          contractName: "ElectionSearchDetail",
          contractVersion: "v1",
        }),
      })
    )

    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate(rawV2Payload)).toEqual({ valid: true })
    expect(contract.validate({})).toEqual(expect.objectContaining({ valid: false }))

    // 404 Not Found Case -> returns null
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response("Not found", { status: 404 })
    )

    const nullResult = await getElectionSearch("non-existent-id")
    expect(nullResult).toBeNull()
  })

  it("createElectionSearch calls instrumentedFetch preserving exact POST body and idempotencyKey", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(rawV2Payload), { status: 200 })
    )

    const params = {
      eventType: "relations:wedding",
      windowFrom: "2026-08-01",
      windowTo: "2026-08-05",
      idempotencyKey: "fixed-idemp-uuid-12345",
      clientTimezone: "Europe/Moscow",
    }

    const created = await createElectionSearch(params)
    expect(created.eventType).toBe("relations:wedding")

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "election.create_search",
        routeTemplate: "POST /api/election/searches",
        url: "/api/election/searches",
        init: expect.objectContaining({
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            eventType: "relations:wedding",
            windowFrom: "2026-08-01",
            windowTo: "2026-08-05",
            idempotencyKey: "fixed-idemp-uuid-12345",
            clientTimezone: "Europe/Moscow",
          }),
        }),
        responseContract: expect.objectContaining({
          contractName: "ElectionSearchCreate",
          contractVersion: "v1",
        }),
      })
    )

    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate(rawV2Payload)).toEqual({ valid: true })
    expect(contract.validate({})).toEqual(expect.objectContaining({ valid: false }))
  })
})
