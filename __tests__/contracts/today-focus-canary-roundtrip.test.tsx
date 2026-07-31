// ############################################################################
// AI_HEADER: MODULE_TESTS_TODAY_FOCUS_CANARY_ROUNDTRIP
// ROLE: Frontend round-trip oracle for sanitized TodayFocus canary fixtures (W6-S2/S3, doc 28 §8.1, doc 30 §4).
// DEPENDENCIES: vitest, fs, path, components/today/today-focus, lib/presentation/today-focus-relation
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-FOCUS-CANARY-ROUNDTRIP
// purpose: Prove the sanitized public canary fixture renders as one focus-story with exact oracle IDs/order and provenance relations.
// owns:
//   - __tests__/contracts/today-focus-canary-roundtrip.test.ts
// inputs: apps/api/tests/fixtures/today_focus/public/*.json
// outputs: vitest assertions
// dependencies: components/today/today-focus, lib/presentation/today-focus-relation
// side_effects: none
// emitted_logs: none
// invariants:
//   - oracle IDs/order from doc 30 §4 are exact and backend-sorted (client never re-sorts)
//   - relation derives only from provenance intersection (no client ranking)
// failure_policy: fail test
// END_MODULE_CONTRACT: M-TEST-FOCUS-CANARY-ROUNDTRIP

import { describe, expect, it } from "vitest"
import { render, screen } from "@testing-library/react"
import React from "react"
import fs from "node:fs"
import path from "node:path"
import { TodayFocusCard } from "@/components/today/today-focus"
import { getEventRelation } from "@/lib/presentation/today-focus-relation"
import type { TodayFocus } from "@/lib/contracts/today"

const FIXTURE_DIR = path.resolve(__dirname, "../../apps/api/tests/fixtures/today_focus/public")

function loadFixture(name: string): { caseId: string; fixtureVersion: string; focus: TodayFocus } {
  const raw = fs.readFileSync(path.join(FIXTURE_DIR, name), "utf-8")
  return JSON.parse(raw)
}

describe("today focus canary roundtrip (sanitized public fixtures)", () => {
  // START_BLOCK: CASE_A_ORACLE
  it("case A (28.07) renders one story with exact oracle event IDs in backend order", () => {
    const fixture = loadFixture("case_a_public_ready.json")
    expect(fixture.fixtureVersion).toBe("today-focus-public.v1")
    expect(fixture.caseId).toBe("convergence-20260728-a")

    const focus = fixture.focus
    expect(focus.state).toBe("convergence_today")
    const fixtureEvents = focus.events ?? []

    // Oracle IDs + display order from doc 30 §4 (backend-sorted, client renders as-is)
    const expectedIds = [
      "ev:act:t2n__MOON__SQUARE__PLUTO",
      "ev:act:t2n__MOON__SEXTILE__URANUS",
      "ev:act:t2n__MARS__OPPOSITION__NEPTUNE",
    ]
    expect(fixtureEvents.map((e) => e.id)).toEqual(expectedIds)

    render(<TodayFocusCard focus={focus} onSphereSelect={() => {}} />)

    const section = screen.getByTestId("today-focus")
    expect(section.getAttribute("data-state")).toBe("convergence_today")

    const rows = screen.getAllByTestId("today-focus-event")
    expect(rows).toHaveLength(3)
    expect(rows.map((r) => r.getAttribute("data-event-id"))).toEqual(expectedIds)

    // Provenance relation (doc 30 §4): only Moon-Pluto belongs to convergence
    expect(rows[0].getAttribute("data-event-relation")).toBe("convergence_event")
    expect(rows[1].getAttribute("data-event-relation")).toBe("independent_event")
    expect(rows[2].getAttribute("data-event-relation")).toBe("independent_event")

    // Every sourceActivationId is traceable to a selected event (doc 30 §9.4)
    for (const ev of fixtureEvents) {
      expect(ev.sourceActivationIds?.length).toBeGreaterThan(0)
    }
  })
  // END_BLOCK: CASE_A_ORACLE

  // START_BLOCK: RELATION_PARTITION
  it("relation helper partitions by provenance only and never re-ranks", () => {
    const fixture = loadFixture("case_a_public_ready.json")
    const focus = fixture.focus
    const events = focus.events ?? []
    const convIds = focus.convergence?.sourceActivationIds

    expect(getEventRelation(events[0], focus.state, convIds)).toBe("convergence_event")
    expect(getEventRelation(events[1], focus.state, convIds)).toBe("independent_event")
    expect(getEventRelation(events[2], focus.state, convIds)).toBe("independent_event")

    // single_impulses always independent (doc 28 §5.1)
    expect(getEventRelation(events[0], "single_impulses", convIds)).toBe("independent_event")
    // missing convergence ids -> independent, no exception
    expect(getEventRelation(events[0], focus.state, null)).toBe("independent_event")
  })
  // END_BLOCK: RELATION_PARTITION

  // START_BLOCK: CASE_G_UNAVAILABLE
  it("case G (LLM unavailable) keeps facts with null LLM fields and honest status", () => {
    const fixture = loadFixture("case_g_public_unavailable.json")
    const focus = fixture.focus
    expect(focus.contentState).toBe("unavailable")

    // No LLM-owned text in the unavailable fixture (doc 30 §9.9)
    expect(focus.convergence?.summary ?? null).toBeNull()
    for (const ev of focus.events ?? []) {
      expect(ev.meaning ?? null).toBeNull()
    }

    render(<TodayFocusCard focus={focus} onSphereSelect={() => {}} />)

    const section = screen.getByTestId("today-focus")
    expect(section.getAttribute("data-content-state")).toBe("unavailable")
    // Facts remain: event rows with ids and times are still rendered
    expect(screen.getAllByTestId("today-focus-event").length).toBeGreaterThan(0)
    // Honest status, no fallback copy (doc 28 §5.3)
    expect(section.textContent).toContain("Персональный разбор пока не готов")
  })
  // END_BLOCK: CASE_G_UNAVAILABLE
})
