import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import { MoodIcon } from "@/components/calendar/mood-icon"

describe("MoodIcon", () => {
  it("рендерится без ошибок для supportive", () => {
    const { container } = render(<MoodIcon status="supportive" />)
    expect(container.firstChild).not.toBeNull()
  })

  it("рендерится без ошибок для even", () => {
    const { container } = render(<MoodIcon status="even" />)
    expect(container.firstChild).not.toBeNull()
  })

  it("рендерится без ошибок для tense", () => {
    const { container } = render(<MoodIcon status="tense" />)
    expect(container.firstChild).not.toBeNull()
  })

  it("для supportive рендерит звёздочку ⭐", () => {
    const { container } = render(<MoodIcon status="supportive" />)
    expect(container.textContent).toContain("⭐")
  })

  it("для even рендерит полукруг ◐", () => {
    const { container } = render(<MoodIcon status="even" />)
    expect(container.textContent).toContain("◐")
  })

  it("для tense рендерит внимание ⚠️", () => {
    const { container } = render(<MoodIcon status="tense" />)
    expect(container.textContent).toContain("⚠️")
  })

  it("применяет className", () => {
    const { container } = render(<MoodIcon status="supportive" className="h-6 w-6" />)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain("h-6")
    expect(el.className).toContain("w-6")
  })

  it("имеет aria-hidden (не доступен скринридерам)", () => {
    const { container } = render(<MoodIcon status="supportive" />)
    const el = container.firstChild as HTMLElement
    expect(el.getAttribute("aria-hidden")).toBe("true")
  })

  it("применяет фоновый цвет через style", () => {
    const { container } = render(<MoodIcon status="supportive" />)
    const el = container.firstChild as HTMLElement
    expect(el.style.background).toBeTruthy()
  })
})
