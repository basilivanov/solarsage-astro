import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'
import { ContextPill } from '@/components/chat/context-pill'

describe('ContextPill', () => {
  it('renders summary text with "с учётом твоей карты"', () => {
    render(<ContextPill summary="12 марта 1995, 14:30 — Москва" />)
    expect(
      screen.getByText(/с учётом твоей карты · 12 марта 1995, 14:30 — Москва/),
    ).toBeTruthy()
  })

  it('contains a Sparkles icon (SVG element)', () => {
    const { container } = render(<ContextPill summary="test summary" />)
    // lucide-react renders an <svg> element
    const svg = container.querySelector('svg')
    expect(svg).toBeTruthy()
  })

  it('renders even when summary is empty', () => {
    const { container } = render(<ContextPill summary="" />)
    const pill = container.querySelector('div')
    expect(pill).toBeTruthy()
    expect(pill?.textContent).toContain('с учётом твоей карты')
  })
})
