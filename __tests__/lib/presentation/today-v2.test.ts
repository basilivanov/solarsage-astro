import { describe, it, expect } from "vitest"
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
  dedupeTechniquesPreserveOrder,
  selectPrimaryEvidence,
} from "@/lib/presentation/today-v2"
import type { ActivationEvidence, TodayV2ActivatedTarget } from "@/lib/contracts/today"

describe("presentation/today-v2", () => {
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

    const title = formatActivationEvidenceTitle({
      technique: "transit_to_natal",
      sourcePlanet: "Transit_Moon",
      targetPlanet: "Natal_Pluto",
      aspect: "opposition",
      evidence: "Transit Moon opposition natal Pluto",
    })
    expect(title).toBe("Луна — оппозиция к вашему натальному Плутону")
    expect(title).not.toMatch(/натальному Плутон$/)
    expect(title.toLowerCase()).not.toContain("transit")
  })

  it("formats aspect titles in Russian without raw English frames", () => {
    const title = formatActivationEvidenceTitle({
      technique: "transit_to_natal",
      sourcePlanet: "Moon",
      targetPlanet: "Pluto",
      aspect: "opposition",
      evidence: "Transit Moon opposition natal Pluto",
    })
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
})
