import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { AspectDrilldownSheet } from "@/components/synastry/aspect-drilldown-sheet"

vi.mock("@/lib/api/synastry", () => ({
  getAspectDrilldown: vi.fn().mockResolvedValue({
    aspectId: "mercury_square_mercury",
    title: "Меркурий квадрат Меркурий",
    tone: "bad",
    techSignature: "Mercury square Mercury (1.0°)",
    aspectSymbol: "□",
    aspectKindLabel: "Квадрат",
    orbText: "орб 1°00′",
    headline: "Два разных способа собирать смысл",
    ownerPlanet: {
      key: "Mercury",
      label: "Меркурий",
      glyph: "☿",
      meaning: "Мышление, речь, логика и вопросы.",
    },
    partnerPlanet: {
      key: "Mercury",
      label: "Меркурий",
      glyph: "☿",
      meaning: "Мышление, речь, логика и вопросы.",
    },
    aspectMechanics: "Динамический вызов и трение.",
    explanation: "Разница в формате мышления.",
    scenes: [
      { title: "В переписке", text: "Смысл искажается." },
      { title: "В споре", text: "Перебиваете друг друга." },
      { title: "После разговора", text: "Разная память о сказанном." },
    ],
    repairs: [
      "1. Переспрашивать услышанное",
      "2. Не решать сложные темы в чате",
      "3. Делать паузу",
    ],
    notMeans: [
      "не значит, что кто-то глупее",
      "не доказывает ложь",
      "не запрещает научиться слышать",
    ],
  }),
}))

describe("AspectDrilldownSheet", () => {
  it("renders structured aspect drilldown sheet with hero, planet cards, scenes, repairs, and not-means", async () => {
    const onClose = vi.fn()
    render(
      <AspectDrilldownSheet
        open={true}
        partnerId="partner-123"
        aspectId="mercury_square_mercury"
        onClose={onClose}
      />
    )

    const sheet = await screen.findByTestId("aspect-drilldown-sheet")
    expect(sheet).toBeDefined()
    expect(sheet.getAttribute("role")).toBe("dialog")

    expect(screen.getByText("Два разных способа собирать смысл")).toBeDefined()
    expect(screen.getByText(/ТВОЯ КАРТА/i)).toBeDefined()
    expect(screen.getByText(/КАРТА ПАРТНЁРА/i)).toBeDefined()
    expect(screen.getByText("В переписке")).toBeDefined()
    expect(screen.getByText("1. Переспрашивать услышанное")).toBeDefined()
    expect(screen.getByText(/не значит, что кто-то глупее/i)).toBeDefined()
  })
})
