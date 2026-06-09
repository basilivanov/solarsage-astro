import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

vi.mock('@/lib/log', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
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

  it('renders title and summary', () => {
    render(<TodayImportantAccordion items={[makeItem()]} />)
    expect(screen.getByText('Меркурий квадрат Нептун')).toBeTruthy()
    expect(screen.getByText('Осторожнее с резкими решениями, конфликтами и обещаниями.')).toBeTruthy()
  })

  it('renders time label if present', () => {
    render(<TodayImportantAccordion items={[makeItem()]} />)
    expect(screen.getByText('· 03:38–11:33')).toBeTruthy()
  })

  it('renders void moon kind', () => {
    render(<TodayImportantAccordion items={[
      makeItem({ id: 'mv', kind: 'void_moon', title: 'Луна без курса' })
    ]} />)
    expect(screen.getByText('Луна без курса')).toBeTruthy()
  })
})
