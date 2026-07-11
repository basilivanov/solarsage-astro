// ############################################################################
// AI_HEADER: TEST_LIB_PRESENTATION_TODAY_V2 — unit tests for today-v2 presentation helpers
// ROLE: Tests the time horizon selection, stage/duration labeling, and timing preview bridge.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-LIB-PRESENTATION-TODAY-V2
// purpose: Validate today-v2 presentation logic, duration/stage formatters, and timing preview bridge.
// owns:
//   - __tests__/lib/presentation/today-v2.test.ts
// inputs: mock activation evidence
// outputs: vitest assertions
// dependencies: lib/presentation/today-v2
// side_effects: none
// emitted_logs: none
// invariants:
//   - timing preview bridge returns strings or undefined, never mutates inputs
// failure_policy: fail test
// END_MODULE_CONTRACT: M-TEST-LIB-PRESENTATION-TODAY-V2

// START_MODULE_MAP: M-TEST-LIB-PRESENTATION-TODAY-V2
// public_entrypoints: describe/it blocks
// semantic_blocks:
//   - PRESENTATION_TESTS: validates localization and formatting helpers
//   - TIMING_BRIDGE_TESTS: validates temporary preview timing bridge behavior
// owned_tests:
//   - __tests__/lib/presentation/today-v2.test.ts
// END_MODULE_MAP: M-TEST-LIB-PRESENTATION-TODAY-V2

import { describe, expect, it } from "vitest"
import {
  getTechniqueLabel,
  getPlanetLabelRu,
  getPlanetLabelRuDative,
  normalizePlanetKey,
  getAspectLabelRu,
  getPhaseLabelRu,
  getSphereLabelConcise,
  formatActivationEvidenceTitle,
  formatConcreteAdviceEvidenceTitle,
  containsBannedAstrologyVocabulary,
  dedupeTechniquesPreserveOrder,
  getHumanSphereLabel,
  getSafeWhyTodayItem,
  getVerdictManifestationCopy,
  orderActivationEvidence,
  selectPrimaryEvidence,
  selectWhyTimeHorizons,
  getEvidenceDurationLabel,
  getEvidenceStageLabel,
  getTechnicalEvidenceExplanation,
  TECHNIQUE_LABELS,
  getEvidenceTimingPreview,
} from "@/lib/presentation/today-v2"
import type { ActivationEvidence, TodayV2ActivatedTarget, TodayV2Block } from "@/packages/contracts"
import { adaptTodayPayload } from "@/lib/adapters/today-payload"
import { dayPayloadV2 } from "@/e2e/mock-visual/fixtures/day-v2-2026-07-08"

function v2WithEvidence(evidence: ActivationEvidence[]): TodayV2Block {
  const { payload } = adaptTodayPayload(dayPayloadV2, new Date("2026-07-08T12:00:00Z"))
  const v2 = structuredClone(payload.v2!)
  const ids = evidence.map((item) => item.id)
  v2.activationEvidence = evidence
  v2.activationSummary.topActivatedTargets[0].activationIds = ids
  v2.whyToday = evidence.map((item) => ({
    id: `why-${item.id}`,
    title: "Личная тема периода",
    body: "Безопасная человеческая формулировка без технических терминов.",
    activationIds: [item.id],
    techniques: [item.technique],
  }))
  v2.scoreBreakdown = {}
  return v2
}

function evidenceFromFixture(id: string, overrides: Partial<ActivationEvidence>): ActivationEvidence {
  const { payload } = adaptTodayPayload(dayPayloadV2, new Date("2026-07-08T12:00:00Z"))
  return { ...payload.v2!.activationEvidence[0], id, ...overrides }
}

describe("presentation/today-v2", () => {
  // START_BLOCK: PRESENTATION_TESTS
  it("maps techniques, planets, aspects, phases, spheres", () => {
    expect(getTechniqueLabel("transit_to_natal")).toBe("Транзит")
    expect(getTechniqueLabel("annual_profection")).toBe("Профекция")
    expect(getTechniqueLabel("firdar_major")).toBe("Фирдар")
    expect(getTechniqueLabel("solar_arc")).toBe("Солнечная дуга")
    expect(getPlanetLabelRu("Moon")).toBe("Луна")
    expect(getPlanetLabelRu("PLUTO")).toBe("Плутон")
    expect(getAspectLabelRu("opposition")).toBe("оппозиция")
    expect(getAspectLabelRu("trine")).toBe("тригон")
    expect(getPhaseLabelRu("separating")).toBe("расходящийся")
    expect(getPhaseLabelRu("exact")).toBe("точный")
    expect(getSphereLabelConcise("work_status_achievement")).toBe("Работа и статус")
    expect(getSphereLabelConcise("money_security_resources")).toBe("Деньги и ресурсы")
    expect(getSphereLabelConcise("inner_background_unconscious")).toBe("Внутренний фон")
    expect(getSphereLabelConcise("crisis_transformation_control")).toBe("Перемены и контроль")
  })

  it("unknown technique is safe human label, not raw snake_case", () => {
    expect(getTechniqueLabel("unknown_custom_cycle")).toBe("Дополнительный цикл")
    expect(getTechniqueLabel("some_snake_case")).not.toMatch(/_/)
  })

  it("strips Transit_/Natal_ prefixes before planet mapping", () => {
    expect(normalizePlanetKey("Transit_Mars")).toBe("Mars")
    expect(normalizePlanetKey("Natal_Pluto")).toBe("Pluto")
    expect(normalizePlanetKey("Transit Moon")).toBe("Moon")
    expect(normalizePlanetKey("Natal Saturn")).toBe("Saturn")
    expect(getPlanetLabelRu("Transit_Mars")).toBe("Марс")
    expect(getPlanetLabelRu("Natal_Pluto")).toBe("Плутон")
  })

  it("uses dative planet forms after «к вашему натальному»", () => {
    expect(getPlanetLabelRuDative("Pluto")).toBe("Плутону")
    expect(getPlanetLabelRuDative("Saturn")).toBe("Сатурну")
    expect(getPlanetLabelRuDative("Moon")).toBe("Луне")
    expect(getPlanetLabelRuDative("Sun")).toBe("Солнцу")
    expect(getPlanetLabelRuDative("Mercury")).toBe("Меркурию")
    expect(getPlanetLabelRuDative("Venus")).toBe("Венере")
    expect(getPlanetLabelRuDative("Mars")).toBe("Марсу")
    expect(getPlanetLabelRuDative("Jupiter")).toBe("Юпитеру")
    expect(getPlanetLabelRuDative("Uranus")).toBe("Урану")
    expect(getPlanetLabelRuDative("Neptune")).toBe("Нептуну")

    const title = formatActivationEvidenceTitle(
      evidenceFromFixture("dative-title", {
        sourcePlanet: "Transit_Moon",
        targetPlanet: "Natal_Pluto",
        aspect: "opposition",
      }),
    )
    expect(title).toBe("Луна — оппозиция к вашему натальному Плутону")
    expect(title).not.toMatch(/натальному Плутон$/)
    expect(title.toLowerCase()).not.toContain("transit")
  })

  it("formats aspect titles in Russian without raw English frames", () => {
    const title = formatActivationEvidenceTitle(
      evidenceFromFixture("aspect-title", {
        sourcePlanet: "Moon",
        targetPlanet: "Pluto",
        aspect: "opposition",
      }),
    )
    expect(title).toContain("Луна")
    expect(title).toContain("оппозиция")
    expect(title).toContain("Плутону")
    expect(title.toLowerCase()).not.toContain("transit")
    expect(title.toLowerCase()).not.toContain("natal")
  })

  it("suppresses English convergence/cap score contribution titles", () => {
    expect(
      formatConcreteAdviceEvidenceTitle({
        kind: "score_contribution",
        title: "Convergence bonus on crisis sphere",
        contributionSourceId: "convergence:crisis_transformation_control",
      }),
    ).toBe("Несколько независимых циклов усиливают эту сферу")

    expect(
      formatConcreteAdviceEvidenceTitle({
        kind: "score_contribution",
        title: "Dominance cap applied",
        contributionSourceId: "cap:money_security_resources",
      }),
    ).toBe("Итоговый акцент сферы ограничен, чтобы один фактор не доминировал")

    expect(
      formatConcreteAdviceEvidenceTitle({
        kind: "score_contribution",
        title: "Activation contribution raw english",
        contributionSourceId: "act-1",
      }),
    ).toBe("Персональный фактор усиливает эту сферу")

    const structured = formatConcreteAdviceEvidenceTitle({
      kind: "activation",
      planet: "Transit_Mars",
      targetPlanet: "Natal_Saturn",
      aspectType: "square",
      title: "Transit Mars square natal Saturn",
    })
    expect(structured).toBe("Марс — квадрат к вашему натальному Сатурну")
  })

  it("dedupes techniques preserving order", () => {
    expect(dedupeTechniquesPreserveOrder(["a", "b", "a", "c"])).toEqual(["a", "b", "c"])
  })

  it("selects at most three evidence items from target activationIds", () => {
    const evidence = [
      { id: "a1", active: true },
      { id: "a2", active: true },
      { id: "a3", active: true },
      { id: "a4", active: true },
    ] as ActivationEvidence[]
    const target = {
      activationIds: ["a1", "a2", "a3", "a4"],
    } as TodayV2ActivatedTarget
    const selected = selectPrimaryEvidence(evidence, target, 3)
    expect(selected.map((e) => e.id)).toEqual(["a1", "a2", "a3"])
  })

  it("maps human navigator labels and deterministic verdict copy", () => {
    expect(getHumanSphereLabel({ key: "work", label: "Работа" })).toBe("Работа и статус")
    expect(getHumanSphereLabel({ key: "unknown", label: "Backend label" })).toBe("Backend label")
    expect(getVerdictManifestationCopy("caution")).toBe(
      "В этой сфере сегодня особенно важны точность и отсутствие спешки.",
    )
  })

  it("sanitizes technical why copy without touching safe human copy", () => {
    for (const technicalForm of [
      "транзит", "транзиты", "профекция", "профекции", "фирдар", "фирдары",
      "орб", "орбис", "натальный", "аспекты", "сходимость", "техника", "техническая основа",
    ]) {
      expect(containsBannedAstrologyVocabulary(technicalForm)).toBe(true)
    }
    expect(containsBannedAstrologyVocabulary("Личная тема заметнее обычного")).toBe(false)
    expect(
      getSafeWhyTodayItem({
        id: "why-1",
        title: "Профекция подтверждает тему",
        body: "Фирдар делает тему заметнее",
        activationIds: [],
        techniques: ["annual_profection", "firdar_major"],
      }),
    ).toEqual({
      title: "Личный фактор дня",
      body: "Тема поддерживается более длинным личным циклом, поэтому ощущается заметнее обычного.",
    })
    expect(
      getSafeWhyTodayItem({
        id: "why-2",
        title: "Безопасный заголовок",
        body: "Безопасная человеческая формулировка.",
        activationIds: [],
        techniques: [],
      }),
    ).toEqual({ title: "Безопасный заголовок", body: "Безопасная человеческая формулировка." })
  })

  it("falls back to active backend order when primary IDs have no usable evidence", () => {
    const evidence = [
      { id: "active-first", active: true },
      { id: "inactive", active: false },
      { id: "active-second", active: true },
    ] as ActivationEvidence[]
    const primary = { activationIds: ["missing", "inactive"] } as TodayV2ActivatedTarget
    expect(orderActivationEvidence(evidence, primary).map((item) => item.id)).toEqual([
      "active-first",
      "active-second",
    ])
  })

  it("splits the representative story into 2 long, 2 medium, and 1 fast evidence", () => {
    const { payload } = adaptTodayPayload(dayPayloadV2, new Date("2026-07-08T12:00:00Z"))
    const horizons = selectWhyTimeHorizons(payload.v2!)
    expect(horizons.map((horizon) => horizon.id)).toEqual(["long", "medium", "fast"])
    expect(horizons.map((horizon) => horizon.evidence.map((item) => item.id))).toEqual([
      ["act-annual-profection", "act-firdar-major"],
      ["act-pluto-trine-saturn", "act-neptune-opp-saturn"],
      ["act-moon-opp-pluto"],
    ])
    expect(new Set(horizons.flatMap((horizon) => horizon.whyItems.map((item) => item.title))).size).toBe(3)
    const mediumWhy = payload.v2!.whyToday.find((item) => item.id === "why-structure-resource")!
    const mediumEvidenceIds = horizons.find((horizon) => horizon.id === "medium")!.evidence.map((item) => item.id)
    expect(mediumWhy.activationIds).toEqual(mediumEvidenceIds)
  })

  it("falls back to related active evidence when primary activation ids are unusable", () => {
    const { payload } = adaptTodayPayload(dayPayloadV2, new Date("2026-07-08T12:00:00Z"))
    const v2 = structuredClone(payload.v2!)
    v2.activationSummary.topActivatedTargets[0].activationIds = ["missing-primary-evidence"]

    expect(selectWhyTimeHorizons(v2).map((horizon) => horizon.evidence.map((item) => item.id))).toEqual([
      ["act-annual-profection", "act-firdar-major"],
      ["act-pluto-trine-saturn", "act-neptune-opp-saturn"],
      ["act-moon-opp-pluto"],
    ])
  })

  it("classifies every supported technique and every fast or slow transit planet", () => {
    const techniqueExamples: Array<[string, Partial<ActivationEvidence>, "long" | "medium" | "fast"]> = [
      ["transit-angle", { technique: "transit_to_angle", kind: "aspect", sourcePlanet: "Saturn", phase: "exact", orb: 1 }, "medium"],
      ["transit-lot", { technique: "transit_to_lot", kind: "aspect", sourcePlanet: "Saturn", phase: "exact", orb: 1 }, "medium"],
      ["transit-house", { technique: "transit_planet_in_house", kind: "aspect", sourcePlanet: "Saturn", phase: "exact", orb: 1 }, "medium"],
      ["annual", { technique: "annual_profection", kind: "period", sourcePlanet: null }, "long"],
      ["firdar-major", { technique: "firdar_major", kind: "period", sourcePlanet: null }, "long"],
      ["firdar-minor", { technique: "firdar_minor", kind: "period", sourcePlanet: null }, "long"],
      ["solar-return", { technique: "solar_return", kind: "period", sourcePlanet: null }, "long"],
      ["monthly", { technique: "monthly_profection", kind: "period", sourcePlanet: null }, "medium"],
      ["lunar-return", { technique: "lunar_return", kind: "period", sourcePlanet: null }, "medium"],
      ["progression", { technique: "secondary_progression", kind: "period", sourcePlanet: null }, "medium"],
      ["solar-arc", { technique: "solar_arc", kind: "period", sourcePlanet: null }, "medium"],
      ["eclipse", { technique: "eclipse_window", kind: "period", sourcePlanet: null }, "medium"],
    ]

    for (const [id, overrides, expected] of techniqueExamples) {
      const horizon = selectWhyTimeHorizons(v2WithEvidence([evidenceFromFixture(id, { strength: 0.8, ...overrides })]))
      expect(horizon.map((item) => item.id)).toEqual([expected])
    }
    for (const planet of ["Moon", "Sun", "Mercury", "Venus", "Mars"]) {
      const horizon = selectWhyTimeHorizons(v2WithEvidence([evidenceFromFixture(`fast-${planet}`, { sourcePlanet: planet, strength: 0.8, phase: "applying", orb: 1 })]))
      expect(horizon.map((item) => item.id)).toEqual(["fast"])
    }
    for (const planet of ["Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]) {
      const horizon = selectWhyTimeHorizons(v2WithEvidence([evidenceFromFixture(`medium-${planet}`, { sourcePlanet: planet, strength: 0.8, phase: "exact", orb: 1 })]))
      expect(horizon.map((item) => item.id)).toEqual(["medium"])
    }
  })

  it.each([
    ["contribution outranks strength", "contribution", { strength: 0.5, phase: "background", orb: 2 }, "stronger", { strength: 0.9, phase: "exact", orb: 0.1 }, "contribution"],
    ["strength outranks phase", "stronger", { strength: 0.9, phase: "separating", orb: 2 }, "exact", { strength: 0.8, phase: "exact", orb: 0.1 }, "stronger"],
    ["exact outranks applying", "exact", { strength: 0.8, phase: "exact", orb: 2 }, "applying", { strength: 0.8, phase: "applying", orb: 0.1 }, "exact"],
    ["smaller orb outranks backend order", "earlier", { strength: 0.8, phase: "exact", orb: 0.8 }, "smaller-orb", { strength: 0.8, phase: "exact", orb: 0.2 }, "smaller-orb"],
    ["backend order is stable on a full tie", "backend-first", { strength: 0.8, phase: "exact", orb: 0.2 }, "backend-second", { strength: 0.8, phase: "exact", orb: 0.2 }, "backend-first"],
  ] as Array<[string, string, Pick<ActivationEvidence, "strength" | "phase" | "orb">, string, Pick<ActivationEvidence, "strength" | "phase" | "orb">, string]>)("ranks pairwise: %s", (_label, firstId, first, secondId, second, expectedFirst) => {
    const v2 = v2WithEvidence([
      evidenceFromFixture(firstId, { sourcePlanet: "Saturn", ...first }),
      evidenceFromFixture(secondId, { sourcePlanet: "Saturn", ...second }),
    ])
    if (expectedFirst === "contribution") {
      v2.scoreBreakdown = {
        test: {
          key: "test", title: "test", baseScore: 0, activationScore: 0, convergenceBonus: 0, rawScore: 0, finalScore: 0, dominanceCapped: false,
          contributions: [{ sphere: "test", source: "activation", sourceId: "contribution", amount: 0.9, evidence: "fixture" }],
        },
      }
    }
    expect(selectWhyTimeHorizons(v2)[0].evidence.map((item) => item.id)).toEqual([expectedFirst, expectedFirst === firstId ? secondId : firstId])
  })

  it("excludes an unrelated Moon, keeps empty horizons absent, and honours 3/2/1 limits", () => {
    const { payload } = adaptTodayPayload(dayPayloadV2, new Date("2026-07-08T12:00:00Z"))
    const unrelated = structuredClone(payload.v2!)
    unrelated.activationSummary.topActivatedTargets[0].activationIds = unrelated.activationSummary.topActivatedTargets[0].activationIds.filter((id) => id !== "act-moon-opp-pluto")
    expect(selectWhyTimeHorizons(unrelated).map((horizon) => horizon.id)).toEqual(["long", "medium"])

    const onlyLong = v2WithEvidence([evidenceFromFixture("long-only", { technique: "annual_profection", kind: "period", sourcePlanet: null })])
    expect(selectWhyTimeHorizons(onlyLong).map((horizon) => horizon.id)).toEqual(["long"])

    const limits = v2WithEvidence([
      ...["l1", "l2", "l3", "l4"].map((id) => evidenceFromFixture(id, { technique: "annual_profection", kind: "period", sourcePlanet: null })),
      ...["m1", "m2", "m3"].map((id) => evidenceFromFixture(id, { sourcePlanet: "Saturn", strength: 0.8, phase: "exact", orb: 0.1 })),
      ...["f1", "f2"].map((id) => evidenceFromFixture(id, { sourcePlanet: "Moon", strength: 0.8, phase: "exact", orb: 0.1 })),
    ])
    expect(selectWhyTimeHorizons(limits).map((horizon) => horizon.evidence.length)).toEqual([3, 2, 1])
  })

  it("maps every supported duration and stage without manufacturing dates", () => {
    const durationCases: Array<[string, string | null, string]> = [
      ["annual_profection", null, "12 месяцев"], ["monthly_profection", null, "около месяца"],
      ["firdar_major", null, "несколько лет"], ["firdar_minor", null, "Вложенный период"],
      ["solar_return", null, "дня рождения"], ["lunar_return", null, "27–28 дней"],
      ["secondary_progression", null, "месяцы вокруг"], ["solar_arc", null, "месяцы вокруг"],
      ["eclipse_window", null, "Несколько недель"], ["transit_to_natal", "Moon", "2 суток"],
      ["transit_to_natal", "Sun", "2 недели"], ["transit_to_natal", "Mercury", "2 недели"],
      ["transit_to_natal", "Venus", "2 недели"], ["transit_to_natal", "Mars", "4 недели"],
      ["transit_to_natal", "Jupiter", "1–4 месяца"], ["transit_to_natal", "Saturn", "3–9 месяцев"],
      ["transit_to_natal", "Uranus", "2–6 месяцев"], ["transit_to_natal", "Neptune", "2–6 месяцев"],
      ["transit_to_natal", "Pluto", "2–6 месяцев"],
    ]
    for (const [technique, sourcePlanet, expected] of durationCases) {
      expect(getEvidenceDurationLabel({ technique, sourcePlanet })).toContain(expected)
    }
    expect(getEvidenceStageLabel("exact")).toBe("Пик — сейчас")
    expect(getEvidenceStageLabel("applying")).toBe("Набирает силу")
    expect(getEvidenceStageLabel("separating")).toBe("Пик уже пройден · влияние ослабевает")
    expect(getEvidenceStageLabel("background")).toBe("Фон уже действует")
    expect(getEvidenceStageLabel("period")).toBe("Фон уже действует")
  })

  it("gives every known technique and planet a non-generic education definition", () => {
    const genericDefinition = "Это один из расчётных способов увидеть, как личная тема проявляется во времени."
    for (const technique of Object.keys(TECHNIQUE_LABELS)) {
      const explanation = getTechnicalEvidenceExplanation(evidenceFromFixture(`definition-${technique}`, { technique }))
      expect(explanation.definition).not.toBe(genericDefinition)
      expect(explanation.definition.length).toBeGreaterThan(40)
    }
    for (const planet of ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]) {
      const explanation = getTechnicalEvidenceExplanation(evidenceFromFixture(`planet-${planet}`, { sourcePlanet: planet, targetPlanet: null, orb: null }))
      expect(explanation.meaning).toContain(getPlanetLabelRu(planet))
    }
  })

  it("describes an annual profection sphere target without leaking its raw backend key", () => {
    const explanation = getTechnicalEvidenceExplanation(evidenceFromFixture("annual-sphere", {
      technique: "annual_profection",
      targetType: "sphere",
      targetKey: "crisis_transformation_control",
      targetPlanet: null,
    }))

    expect(explanation.definition).not.toContain("crisis_transformation_control")
    expect(explanation.definition).toContain("Перемены и контроль")
  })

  it("excludes weak or unrelated fast evidence and preserves empty horizons", () => {
    const { payload } = adaptTodayPayload(dayPayloadV2, new Date("2026-07-08T12:00:00Z"))
    const v2 = structuredClone(payload.v2!)
    v2.activationEvidence = v2.activationEvidence.map((item) => item.id === "act-moon-opp-pluto" ? { ...item, strength: 0.1, orb: 4 } : item)
    const horizons = selectWhyTimeHorizons(v2)
    expect(horizons.map((horizon) => horizon.id)).toEqual(["long", "medium"])
    expect(horizons.every((horizon) => horizon.evidence.length <= ({ long: 3, medium: 2, fast: 1 }[horizon.id]))).toBe(true)
  })
  // END_BLOCK: PRESENTATION_TESTS

  // START_BLOCK: TIMING_BRIDGE_TESTS
  describe("getEvidenceTimingPreview", () => {
    it("returns valid timing preview properties", () => {
      const evidence = dayPayloadV2.v2?.activationEvidence.find(
        (item) => item.id === "act-pluto-trine-saturn",
      )
      expect(evidence).toBeDefined()
      if (!evidence) throw new Error("fixture evidence is missing")

      const timing = getEvidenceTimingPreview(evidence)
      expect(timing.exactAt).toBe("2026-07-10T11:32:00Z")
      expect(timing.activeFrom).toBe("2026-07-03T00:00:00Z")
      expect(timing.activeUntil).toBe("2026-07-18T00:00:00Z")
    })

    it("returns null when fields are null", () => {
      const evidence = dayPayloadV2.v2?.activationEvidence.find(
        (item) => item.id === "act-pluto-trine-saturn",
      )
      expect(evidence).toBeDefined()
      if (!evidence) throw new Error("fixture evidence is missing")

      const mockEvidence = Object.assign(structuredClone(evidence), {
        exactAt: null,
        activeFrom: null,
        activeUntil: null,
      })

      const timing = getEvidenceTimingPreview(mockEvidence)
      expect(timing.exactAt).toBeNull()
      expect(timing.activeFrom).toBeNull()
      expect(timing.activeUntil).toBeNull()
    })

    it("does not mutate the input object", () => {
      const evidence = dayPayloadV2.v2?.activationEvidence.find(
        (item) => item.id === "act-pluto-trine-saturn",
      )
      expect(evidence).toBeDefined()
      if (!evidence) throw new Error("fixture evidence is missing")

      const clone = structuredClone(evidence)
      getEvidenceTimingPreview(evidence)
      expect(evidence).toEqual(clone)
    })
  })
  // END_BLOCK: TIMING_BRIDGE_TESTS
})
