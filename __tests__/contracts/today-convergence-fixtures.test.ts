// ############################################################################
// AI_HEADER: TEST_CONTRACTS_TODAY_CONVERGENCE_FIXTURES — validates the canonical 16+3 fixture matrix.
// ROLE: Proves generated wire parsing, reference ledgers, content caps, and state/access projections.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-FIXTURES
// purpose: Validate every Today Convergence and Yesterday fixture against generated Zod roots and normative structural invariants.
// owns:
//   - __tests__/contracts/today-convergence-fixtures.test.ts
// inputs: 16 TodayConvergencePayload JSON fixtures and 3 YesterdayCheckinResponse JSON fixtures.
// outputs: Vitest evidence for generated schema parity and per-fixture state/content invariants.
// dependencies: __tests__/fixtures/today_convergence_v2, packages/contracts/today-convergence.ts, generated Zod artifacts.
// side_effects: none; reads committed fixture data only.
// emitted_logs: none.
// invariants: every referenced selected event is present exactly once in the event ledger; no fixture weakens the wire schema.
// failure_policy: fail with fixture name and generated Zod issues or invariant description.
// END_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-FIXTURES

// START_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-FIXTURES
// public_entrypoints:
//   - generated-schema fixture tests
//   - structural invariant tests
//   - barrel export tests
// semantic_blocks:
//   - GENERATED_SCHEMA: parse all 16 Today and 3 Yesterday fixtures.
//   - EVENT_LEDGER: verify canonical IDs, references, and narrative provenance.
//   - STATE_MATRIX: verify caps, access projections, birth-time modes, and negative guards.
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-FIXTURES

import { describe, expect, it } from "vitest";
import {
  accessLocked,
  accessPreview,
  birthBucket,
  birthUnknown,
  contentPending,
  contentUnavailable,
  heroMixed,
  heroSupportive,
  heroTense,
  heroThreeSpheres,
  quietGeneralBackground,
  quietFacetsNewSpheres,
  quietMainMax,
  quietSteady,
  quietTenseImpulse,
  quietZeroImpulses,
  stateUnavailable,
  spheresFacetsFinance,
  todayConvergenceFixtures,
  yesterdayFixtures,
  yesterdayNoSnapshot,
  yesterdayPostSubmit,
  yesterdayPreSubmit,
} from "../fixtures/today_convergence_v2";
import {
  TodayConvergencePayloadWireSchema,
} from "@/packages/contracts/today-convergence";
import { YesterdayCheckinResponse as YesterdayCheckinResponseWireSchema } from "@/packages/contracts/_generated.zod";
import type { TodayConvergencePayload } from "@/packages/contracts/today-convergence";

type Claim = {
  text: string;
  sourceEventIds: string[];
};

type WireSchema = {
  safeParse: (value: unknown) =>
    | { success: true; data: unknown }
    | { success: false; error: { issues: unknown } };
};

const namedTodayFixtures: readonly [string, TodayConvergencePayload][] = [
  ["01_hero_supportive", heroSupportive],
  ["02_hero_tense", heroTense],
  ["03_hero_mixed", heroMixed],
  ["04_hero_three_spheres", heroThreeSpheres],
  ["05_quiet_steady", quietSteady],
  ["06_quiet_tense_impulse", quietTenseImpulse],
  ["07_quiet_zero_impulses", quietZeroImpulses],
  ["08_quiet_main_max", quietMainMax],
  ["09_quiet_general_background", quietGeneralBackground],
  ["10_content_pending", contentPending],
  ["11_content_unavailable", contentUnavailable],
  ["12_state_unavailable", stateUnavailable],
  ["13_birth_bucket", birthBucket],
  ["14_birth_unknown", birthUnknown],
  ["15_access_preview", accessPreview],
  ["16_access_locked", accessLocked],
];

const namedYesterdayFixtures = [
  ["yesterday_pre_submit", yesterdayPreSubmit],
  ["yesterday_post_submit", yesterdayPostSubmit],
  ["yesterday_no_snapshot", yesterdayNoSnapshot],
] as const;

// START_BLOCK: GENERATED_SCHEMA
function assertGeneratedSchema(name: string, schema: WireSchema, value: unknown): void {
  // START_FUNCTION_CONTRACT: F-M-TEST-TODAY-CONVERGENCE-FIXTURES.assertGeneratedSchema
  // purpose: Parse one fixture with the generated Zod root and preserve actionable issues on failure.
  // inputs: name — fixture label; schema — generated root; value — imported JSON payload.
  // returns: void when parsing succeeds.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: throws with serialized Zod issues when parsing fails.
  // END_FUNCTION_CONTRACT: F-M-TEST-TODAY-CONVERGENCE-FIXTURES.assertGeneratedSchema
  const result = schema.safeParse(value);
  if (!result.success) {
    throw new Error(`${name} failed generated Zod validation:\n${JSON.stringify(result.error.issues, null, 2)}`);
  }
}
// END_BLOCK: GENERATED_SCHEMA

// START_BLOCK: EVENT_LEDGER
function selectedEventIds(payload: TodayConvergencePayload): string[] {
  // START_FUNCTION_CONTRACT: F-M-TEST-TODAY-CONVERGENCE-FIXTURES.selectedEventIds
  // purpose: Collect every event ID referenced by a selected presentation block.
  // inputs: payload — Today Convergence wire payload.
  // returns: referenced event IDs from groups, main event, impulses, and period context.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: returns an empty list when no presentation block references an event.
  // END_FUNCTION_CONTRACT: F-M-TEST-TODAY-CONVERGENCE-FIXTURES.selectedEventIds
  return [
    ...payload.convergences.flatMap((group) => group.eventIds),
    ...(payload.mainEvent ? [payload.mainEvent.eventId] : []),
    ...payload.impulses.map((impulse) => impulse.eventId),
    ...(payload.periodContext?.eventIds ?? []),
  ];
}

function assertClaim(claim: Claim | null | undefined, ownerEventIds: readonly string[]): void {
  // START_FUNCTION_CONTRACT: F-M-TEST-TODAY-CONVERGENCE-FIXTURES.assertClaim
  // purpose: Verify that a non-null narrative claim is meaningful and grounded in its owning block.
  // inputs: claim — nullable LLM-owned claim; ownerEventIds — selected event IDs of its block.
  // returns: void when the claim is valid.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: Vitest assertions fail for empty, non-Russian, overlong, or ungrounded claims.
  // END_FUNCTION_CONTRACT: F-M-TEST-TODAY-CONVERGENCE-FIXTURES.assertClaim
  if (claim == null) return;

  expect(claim.text.trim().length).toBeGreaterThan(0);
  expect(claim.text.length).toBeLessThanOrEqual(220);
  expect(/[А-Яа-яЁё]/u.test(claim.text)).toBe(true);
  expect(claim.sourceEventIds.length).toBeGreaterThan(0);
  for (const sourceEventId of claim.sourceEventIds) {
    expect(ownerEventIds).toContain(sourceEventId);
  }
}

function assertNarratives(payload: TodayConvergencePayload): void {
  // START_FUNCTION_CONTRACT: F-M-TEST-TODAY-CONVERGENCE-FIXTURES.assertNarratives
  // purpose: Check claim shape and source-event provenance for every selected block.
  // inputs: payload — Today Convergence wire payload.
  // returns: void when all nullable claims are valid.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: Vitest assertions fail on invalid claim text or provenance.
  // END_FUNCTION_CONTRACT: F-M-TEST-TODAY-CONVERGENCE-FIXTURES.assertNarratives
  for (const group of payload.convergences) {
    assertClaim(group.summary, group.eventIds);
    assertClaim(group.meaning, group.eventIds);
    assertClaim(group.action, group.eventIds);
  }
  if (payload.mainEvent) {
    const ownerIds = [payload.mainEvent.eventId];
    assertClaim(payload.mainEvent.summary, ownerIds);
    assertClaim(payload.mainEvent.meaning, ownerIds);
    assertClaim(payload.mainEvent.action, ownerIds);
  }
  for (const impulse of payload.impulses) {
    const ownerIds = [impulse.eventId];
    assertClaim(impulse.summary, ownerIds);
    assertClaim(impulse.meaning, ownerIds);
    assertClaim(impulse.action, ownerIds);
  }
}

function assertNoNarratives(payload: TodayConvergencePayload): void {
  // START_FUNCTION_CONTRACT: F-M-TEST-TODAY-CONVERGENCE-FIXTURES.assertNoNarratives
  // purpose: Ensure pending/unavailable and non-personal projections do not invent LLM copy.
  // inputs: payload — Today Convergence wire payload.
  // returns: void when all LLM-owned fields are null or absent.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: Vitest assertions fail when any LLM-owned field contains content.
  // END_FUNCTION_CONTRACT: F-M-TEST-TODAY-CONVERGENCE-FIXTURES.assertNoNarratives
  for (const group of payload.convergences) {
    expect(group.summary ?? null).toBeNull();
    expect(group.meaning ?? null).toBeNull();
    expect(group.action ?? null).toBeNull();
  }
  if (payload.mainEvent) {
    expect(payload.mainEvent.summary ?? null).toBeNull();
    expect(payload.mainEvent.meaning ?? null).toBeNull();
    expect(payload.mainEvent.action ?? null).toBeNull();
  }
  for (const impulse of payload.impulses) {
    expect(impulse.summary ?? null).toBeNull();
    expect(impulse.meaning ?? null).toBeNull();
    expect(impulse.action ?? null).toBeNull();
  }
}

function assertNoExactEventClocks(payload: TodayConvergencePayload): void {
  // START_FUNCTION_CONTRACT: F-M-TEST-TODAY-CONVERGENCE-FIXTURES.assertNoExactEventClocks
  // purpose: Guard that bucket/unknown birth-time projections never expose exact event clocks.
  // inputs: payload — bucket or unknown Today Convergence wire payload.
  // returns: void when every event time has no HH:MM value in exact-time fields.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: Vitest assertions fail when an event leaks an exact clock.
  // END_FUNCTION_CONTRACT: F-M-TEST-TODAY-CONVERGENCE-FIXTURES.assertNoExactEventClocks
  for (const event of payload.events) {
    for (const value of [event.time.peak, event.time.start, event.time.end]) {
      expect(value == null || !/\d{2}:\d{2}/u.test(value)).toBe(true);
    }
  }
}

function assertEventLedger(payload: TodayConvergencePayload): void {
  // START_FUNCTION_CONTRACT: F-M-TEST-TODAY-CONVERGENCE-FIXTURES.assertEventLedger
  // purpose: Verify canonical IDs, unique event evidence, and exact selected-event union.
  // inputs: payload — Today Convergence wire payload.
  // returns: void when all presentation references resolve to the event ledger.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: Vitest assertions fail on malformed IDs, duplicates, or dangling references.
  // END_FUNCTION_CONTRACT: F-M-TEST-TODAY-CONVERGENCE-FIXTURES.assertEventLedger
  const eventIds = payload.events.map((event) => event.id);
  expect(new Set(eventIds).size).toBe(eventIds.length);
  expect(new Set(eventIds)).toEqual(new Set(selectedEventIds(payload)));

  for (const event of payload.events) {
    expect(event.id).toMatch(/^evt_v1_[0-9a-f]{32}$/u);
  }
  for (const group of payload.convergences) {
    expect(group.id).toMatch(/^cvg_v1_[0-9a-f]{32}$/u);
    for (const eventId of group.eventIds) expect(eventIds).toContain(eventId);
  }
  if (payload.mainEvent) {
    expect(payload.mainEvent.id).toMatch(/^mev_v1_evt_v1_[0-9a-f]{32}$/u);
    expect(payload.mainEvent.id).toBe(`mev_v1_${payload.mainEvent.eventId}`);
    expect(eventIds).toContain(payload.mainEvent.eventId);
  }
  for (const impulse of payload.impulses) {
    expect(eventIds).toContain(impulse.eventId);
  }
  for (const eventId of payload.periodContext?.eventIds ?? []) {
    expect(eventIds).toContain(eventId);
  }

  assertNarratives(payload);
}
// END_BLOCK: EVENT_LEDGER

// START_BLOCK: STATE_MATRIX
describe("Today Convergence and Yesterday fixture matrix", () => {
  it("parses all 16 Today fixtures through the generated root and prints Zod issues", () => {
    expect(todayConvergenceFixtures).toHaveLength(16);
    for (const [name, fixture] of namedTodayFixtures) {
      assertGeneratedSchema(name, TodayConvergencePayloadWireSchema, fixture);
    }
  });

  it("parses all 3 Yesterday fixtures through the generated check-in root", () => {
    expect(yesterdayFixtures).toHaveLength(3);
    for (const [name, fixture] of namedYesterdayFixtures) {
      assertGeneratedSchema(name, YesterdayCheckinResponseWireSchema, fixture);
    }
  });

  it("keeps the event ledger equal to selected block references for every Today fixture", () => {
    for (const [name, fixture] of namedTodayFixtures) {
      expect(() => assertEventLedger(fixture), name).not.toThrow();
    }
  });

  it("covers the hero tone and three-sphere content cap", () => {
    expect(heroSupportive.state).toBe("convergence_today");
    expect(heroSupportive.dayTone).toBe("supportive");
    expect(heroSupportive.convergences).toHaveLength(1);

    expect(heroTense.dayTone).toBe("tense");
    expect(heroMixed.dayTone).toBe("mixed");
    expect(heroMixed.convergences[0].sphere).toBe("relationships");
    expect(heroMixed.convergences[0].facet).toBeNull();

    expect(heroThreeSpheres.convergences).toHaveLength(3);
    const heroSpheres = new Set(
      heroThreeSpheres.convergences.flatMap((group) => [
        group.sphere,
      ])
    );
    expect(heroSpheres).toEqual(new Set(["work", "documents", "relationships"]));
    for (const group of heroThreeSpheres.convergences) {
      expect(group.summary).not.toBeNull();
      expect(group.meaning).not.toBeNull();
      expect(group.action).not.toBeNull();
    }
  });

  it("covers quiet-day caps, no-accent context, and lookahead", () => {
    expect(quietSteady.state).toBe("quiet_day");
    expect(quietSteady.dayTone).toBe("steady");
    expect(quietSteady.impulses).toHaveLength(3);
    expect(quietSteady.lookahead).toEqual(
      expect.objectContaining({ targetDate: "2026-08-02" })
    );

    expect(quietTenseImpulse.impulses).toHaveLength(1);
    expect(quietTenseImpulse.impulses[0].polarity).toBe("tense");

    expect(quietZeroImpulses.mainEvent).toBeNull();
    expect(quietZeroImpulses.impulses).toHaveLength(0);
    expect(quietZeroImpulses.periodContext?.kind).toBe("no_strong_accent");
    expect(quietZeroImpulses.periodContext?.title).toBe("Без выраженного акцента");

    expect(quietMainMax.mainEvent).not.toBeNull();
    expect(quietMainMax.impulses).toHaveLength(3);
    expect(quietMainMax.lookahead).not.toBeNull();
    expect(quietMainMax.contentState).toBe("ready");
  });

  it("exports the sphere/facet sandbox fixtures without widening the canonical root matrix", () => {
    expect(spheresFacetsFinance.schemaVersion).toBe(2);
    expect(spheresFacetsFinance.convergences.map((group) => [group.sphere, group.facet])).toEqual([
      ["finance", "personal_money"],
      ["finance", "financial_obligations"],
      ["work", "daily_work"],
    ]);
    expect(quietFacetsNewSpheres.schemaVersion).toBe(2);
    expect(quietFacetsNewSpheres.impulses.map((impulse) => [impulse.sphere, impulse.facet])).toEqual([
      ["work", "daily_work"],
      ["finance", "personal_money"],
      ["study", "skills_courses"],
    ]);
  });

  it("keeps pending/unavailable LLM states deterministic", () => {
    expect(contentPending.state).toBe("convergence_today");
    expect(contentPending.contentState).toBe("pending");
    assertNoNarratives(contentPending);

    expect(contentUnavailable.state).toBe("quiet_day");
    expect(contentUnavailable.snapshotId).not.toBeNull();
    expect(contentUnavailable.events.length).toBeGreaterThan(0);
    expect(contentUnavailable.contentState).toBe("unavailable");
    assertNoNarratives(contentUnavailable);

    expect(stateUnavailable.state).toBe("unavailable");
    expect(stateUnavailable.snapshotId).toBeNull();
    expect(stateUnavailable.publishedAt).toBeNull();
    expect(stateUnavailable.dayTone).toBeNull();
    expect(stateUnavailable.personal).toBeNull();
    expect(stateUnavailable.convergences).toHaveLength(0);
    expect(stateUnavailable.mainEvent).toBeNull();
    expect(stateUnavailable.impulses).toHaveLength(0);
    expect(stateUnavailable.periodContext).toBeNull();
    expect(stateUnavailable.lookahead).toBeNull();
    expect(stateUnavailable.events).toHaveLength(0);
  });

  it("preserves bucket and unknown-time event-time restrictions", () => {
    expect(birthBucket.birthTime.mode).toBe("bucket");
    expect(birthBucket.birthTime.bucket).toBe("morning");
    expect(birthBucket.birthTime.capabilities).toEqual({
      houses: false,
      angles: false,
      lots: false,
      exactTiming: false,
    });
    expect(birthBucket.events.every((event) => event.time.mode === "partofday")).toBe(true);
    assertNoExactEventClocks(birthBucket);

    expect(birthUnknown.birthTime.mode).toBe("unknown");
    expect(birthUnknown.birthTime.rangeStart).toBe("00:00");
    expect(birthUnknown.birthTime.rangeEnd).toBe("24:00");
    expect(birthUnknown.events.every((event) => ["partofday", "date"].includes(event.time.mode))).toBe(true);
    assertNoExactEventClocks(birthUnknown);

    expect(quietGeneralBackground.personal).toBe(false);
    expect(quietGeneralBackground.birthTime.mode).toBe("unknown");
    expect(quietGeneralBackground.periodContext?.kind).toBe("active_period");
    expect(quietGeneralBackground.impulses.some((impulse) => impulse.time.mode === "date")).toBe(true);
    expect(quietGeneralBackground.impulses.some((impulse) => impulse.time.mode === "partofday")).toBe(true);
    assertNoNarratives(quietGeneralBackground);
  });

  it("keeps preview and locked projections free of hidden content", () => {
    expect(accessPreview.access.state).toBe("preview");
    expect(accessPreview.state).not.toBeNull();
    expect(accessPreview.dayTone).not.toBeNull();
    expect(accessPreview.personal).not.toBeNull();
    expect(accessPreview.previewTeaser?.spheres).toHaveLength(3);
    expect(accessPreview.convergences).toHaveLength(0);
    expect(accessPreview.mainEvent).toBeNull();
    expect(accessPreview.impulses).toHaveLength(0);
    expect(accessPreview.periodContext).toBeNull();
    expect(accessPreview.lookahead).toBeNull();
    expect(accessPreview.events).toHaveLength(0);
    expect(accessPreview.contentState).toBe("not_needed");

    expect(accessLocked.access.state).toBe("locked");
    expect(accessLocked.snapshotId).toBeNull();
    expect(accessLocked.publishedAt).toBeNull();
    expect(accessLocked.state).toBeNull();
    expect(accessLocked.dayTone).toBeNull();
    expect(accessLocked.personal).toBeNull();
    expect(accessLocked.previewTeaser).toBeNull();
    expect(accessLocked.convergences).toHaveLength(0);
    expect(accessLocked.mainEvent).toBeNull();
    expect(accessLocked.impulses).toHaveLength(0);
    expect(accessLocked.periodContext).toBeNull();
    expect(accessLocked.lookahead).toBeNull();
    expect(accessLocked.events).toHaveLength(0);
    expect(accessLocked.contentState).toBe("not_needed");
  });

  it("exports exactly the 16 Today and 3 Yesterday named fixtures", () => {
    expect(todayConvergenceFixtures).toEqual([
      heroSupportive,
      heroTense,
      heroMixed,
      heroThreeSpheres,
      quietSteady,
      quietTenseImpulse,
      quietZeroImpulses,
      quietMainMax,
      quietGeneralBackground,
      contentPending,
      contentUnavailable,
      stateUnavailable,
      birthBucket,
      birthUnknown,
      accessPreview,
      accessLocked,
    ]);
    expect(yesterdayFixtures).toEqual([
      yesterdayPreSubmit,
      yesterdayPostSubmit,
      yesterdayNoSnapshot,
    ]);
  });

  it("guards Yesterday pre-submit, post-submit lineage, and no-snapshot states", () => {
    expect(yesterdayPreSubmit).toMatchObject({
      hadCheckin: false,
      checkin: null,
      forecastAvailable: true,
      forecastRecap: null,
    });

    expect(yesterdayPostSubmit.hadCheckin).toBe(true);
    expect(yesterdayPostSubmit.checkin).not.toBeNull();
    expect(yesterdayPostSubmit.forecastAvailable).toBe(true);
    expect(yesterdayPostSubmit.forecastRecap?.sphereKeys.length).toBeLessThanOrEqual(3);
    expect(yesterdayPostSubmit.forecastRecap?.snapshotId).toBe(
      yesterdayPostSubmit.checkin?.forecastSnapshotId
    );

    expect(yesterdayNoSnapshot.hadCheckin).toBe(true);
    expect(yesterdayNoSnapshot.checkin).not.toBeNull();
    expect(yesterdayNoSnapshot.forecastAvailable).toBe(false);
    expect(yesterdayNoSnapshot.forecastRecap).toBeNull();
  });
});
// END_BLOCK: STATE_MATRIX
