import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'

vi.mock('@/lib/log', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}))

vi.mock('lucide-react', () => ({
  Moon: (props: any) => <span data-testid="icon-moon" {...props} />,
  AlertTriangle: (props: any) => <span data-testid="icon-alert-triangle" {...props} />,
  RotateCcw: (props: any) => <span data-testid="icon-rotate-ccw" {...props} />,
  Zap: (props: any) => <span data-testid="icon-zap" {...props} />,
  Star: (props: any) => <span data-testid="icon-star" {...props} />,
  Sparkles: (props: any) => <span data-testid="icon-sparkles" {...props} />,
  ChevronDown: (props: any) => <span data-testid="icon-chevron-down" {...props} />,
}))

import { TodayImportantAccordion } from '@/components/today-important-accordion'
import type { TodayImportantEvent } from '@/packages/contracts'

function makeItem(overrides: Partial<TodayImportantEvent> = {}): TodayImportantEvent {
  return {
    id: 'test-1',
    kind: 'fast_planet_aspect',
    tone: 'caution',
    title: 'Меркурий квадрат Нептун',
    summary: 'Осторожнее с резкими решениями, конфликтами и обещаниями.',
    priority: 70,
    timezone: 'Europe/Moscow',
    localTimeLabel: '03:38–11:33',
    ...overrides,
  }
}

describe('TodayImportantAccordion', () => {
  it('hides when items empty', () => {
    const { container } = render(<TodayImportantAccordion items={[]} />)
    expect(container.innerHTML).toBe('')
  })

  it('hides when important_today is null', () => {
    const { container } = render(<TodayImportantAccordion items={null as any} />)
    expect(container.innerHTML).toBe('')
  })

  it('renders accordion header', () => {
    render(<TodayImportantAccordion items={[makeItem()]} />)
    expect(screen.getByText('Сегодня важно')).toBeTruthy()
  })

  it('renders title', () => {
    render(<TodayImportantAccordion items={[makeItem()]} />)
    expect(screen.getByText('Меркурий квадрат Нептун')).toBeTruthy()
  })

  it('renders time label if present', () => {
    render(<TodayImportantAccordion items={[makeItem()]} />)
    expect(screen.getByText('· 03:38–11:33')).toBeTruthy()
  })

  it('is collapsed by default and shows summary on click', () => {
    render(<TodayImportantAccordion items={[makeItem()]} />)
    // Summary should not be visible initially
    expect(screen.queryByText('Осторожнее с резкими решениями, конфликтами и обещаниями.')).toBeNull()
    
    // Expand it
    const btn = screen.getByTestId('important-item-test-1')
    fireEvent.click(btn)
    
    // Now it should be visible
    expect(screen.getByText('Осторожнее с резкими решениями, конфликтами и обещаниями.')).toBeTruthy()
  })

  it('renders void moon kind', () => {
    render(<TodayImportantAccordion items={[
      makeItem({ id: 'mv', kind: 'void_moon', title: 'Луна без курса' })
    ]} />)
    expect(screen.getByText('Луна без курса')).toBeTruthy()
  })

  it('applies caution tone styling for tone="caution"', () => {
    render(<TodayImportantAccordion items={[
      makeItem({ id: 'caution-1', tone: 'caution', title: 'Caution Item' })
    ]} />)
    const btn = screen.getByTestId('important-item-caution-1')
    // The icon container should have caution (red) styling
    const iconContainer = btn.querySelector('.bg-red-500\\/10')
    expect(iconContainer).toBeTruthy()
  })

  it('applies supportive tone styling for tone="supportive"', () => {
    render(<TodayImportantAccordion items={[
      makeItem({ id: 'supp-1', tone: 'supportive', title: 'Supportive Item' })
    ]} />)
    const btn = screen.getByTestId('important-item-supp-1')
    // The icon container should have supportive (emerald) styling
    const iconContainer = btn.querySelector('.bg-emerald-500\\/10')
    expect(iconContainer).toBeTruthy()
  })

  it('collapses item when clicking the same item again (toggle off)', () => {
    render(<TodayImportantAccordion items={[makeItem()]} />)

    // Expand the item
    const btn = screen.getByTestId('important-item-test-1')
    fireEvent.click(btn)
    expect(screen.getByText('Осторожнее с резкими решениями, конфликтами и обещаниями.')).toBeTruthy()

    // Click again to collapse
    fireEvent.click(btn)
    expect(screen.queryByText('Осторожнее с резкими решениями, конфликтами и обещаниями.')).toBeNull()
  })

  it('sets aria-expanded="true" when item is open', () => {
    render(<TodayImportantAccordion items={[makeItem()]} />)

    const btn = screen.getByTestId('important-item-test-1')
    expect(btn.getAttribute('aria-expanded')).toBe('false')

    // Open the item
    fireEvent.click(btn)
    expect(btn.getAttribute('aria-expanded')).toBe('true')
  })

  it('falls back to Star icon for unknown kind', () => {
    render(<TodayImportantAccordion items={[
      makeItem({ id: 'unknown-1', kind: 'unknown_kind' as any, title: 'Unknown Kind Item' })
    ]} />)

    // The item should still render and use the Star icon (fallback)
    expect(screen.getByText('Unknown Kind Item')).toBeTruthy()
    const btn = screen.getByTestId('important-item-unknown-1')
    // The Star icon should be rendered inside the button
    const starIcons = btn.querySelectorAll('[data-testid="icon-star"]')
    expect(starIcons.length).toBeGreaterThanOrEqual(1)
  })
})
