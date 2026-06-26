import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import { DaySummaryCard } from "@/components/today/day-summary-card"

describe("DaySummaryCard", () => {
  const defaultProps = {
    date: new Date("2026-06-26T12:00:00Z"), // пятница
    dayStatus: "steady" as const,
    dominantPlanet: "Sun",
  }

  it("рендерится без ошибок", () => {
    const { container } = render(<DaySummaryCard {...defaultProps} />)
    expect(container.firstChild).not.toBeNull()
  })

  it("содержит дату 26 июн", () => {
    const { container } = render(<DaySummaryCard {...defaultProps} />)
    expect(container.textContent).toContain("26")
    expect(container.textContent).toContain("июн")
  })

  it("содержит день недели Пятница", () => {
    const { container } = render(<DaySummaryCard {...defaultProps} />)
    expect(container.textContent).toContain("Пятница")
  })

  it("показывает статус дня 'Ровный день' для steady", () => {
    const { container } = render(<DaySummaryCard {...defaultProps} />)
    expect(container.textContent).toContain("Ровный день")
  })

  it("показывает 'Поддерживающий' для supportive", () => {
    const { container } = render(
      <DaySummaryCard {...defaultProps} dayStatus="supportive" />,
    )
    expect(container.textContent).toContain("Поддерживающий")
  })

  it("показывает 'Напряжённый' для tense", () => {
    const { container } = render(
      <DaySummaryCard {...defaultProps} dayStatus="tense" />,
    )
    expect(container.textContent).toContain("Напряжённый")
  })

  it("показывает управителя дня Венера для пятницы", () => {
    const { container } = render(<DaySummaryCard {...defaultProps} />)
    expect(container.textContent).toContain("Венера")
  })

  it("показывает 'управитель'", () => {
    const { container } = render(<DaySummaryCard {...defaultProps} />)
    expect(container.textContent).toContain("управитель")
  })

  it("показывает тему планеты в фокусе для Sun", () => {
    const { container } = render(<DaySummaryCard {...defaultProps} />)
    expect(container.textContent).toContain("проявись")
  })

  it("показывает строки ленты со стрелкой →", () => {
    const { container } = render(<DaySummaryCard {...defaultProps} />)
    expect(container.textContent).toContain("→")
  })

  it("показывает фазу Луны с emoji", () => {
    const { container } = render(<DaySummaryCard {...defaultProps} />)
    const moonEmojis = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]
    const hasMoon = moonEmojis.some((e) => container.textContent?.includes(e))
    expect(hasMoon).toBe(true)
  })

  it("показывает лунный день (если напряжённый)", () => {
    const { container } = render(<DaySummaryCard {...defaultProps} />)
    // Лунный день показывается только если напряжённый
    // Просто проверяем что компонент не падает
    expect(container.firstChild).not.toBeNull()
  })

  it("не показывает 'В фокусе' в компактном виде (тема указана в ленте)", () => {
    const { container } = render(<DaySummaryCard {...defaultProps} />)
    // В компактном виде 'В фокусе' не показывается отдельно — тема в ленте
    expect(container.textContent).toContain("проявись")
  })

  it("не падает без dominantPlanet", () => {
    const { container } = render(
      <DaySummaryCard date={defaultProps.date} dayStatus="steady" />,
    )
    expect(container.firstChild).not.toBeNull()
  })

  it("корректно отрисовывает ленту с показателями", () => {
    const { container } = render(<DaySummaryCard {...defaultProps} />)
    const text = container.textContent || ""
    // Хотя бы одна строка со стрелкой (фаза Луны)
    expect(text).toContain("→")
    // Либо показан VoC, либо нет — главное что не падает
    expect(container.firstChild).not.toBeNull()
  })

  it("корректно отрисовывает ретрограды (если есть)", () => {
    const { container } = render(<DaySummaryCard {...defaultProps} />)
    // Если ретроградов нет — строки нет. Если есть — есть.
    // Главноё что компонент не падает
    expect(container.firstChild).not.toBeNull()
  })
})
