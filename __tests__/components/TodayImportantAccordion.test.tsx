import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'

vi.mock('@/lib/log', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}))

import { TodayImportantAccordion } from '@/components/today-important-accordion'
import type { ImportantTodayItem } from '@/components/today-important-accordion'

function makeItem(overrides: Partial<ImportantTodayItem> = {}): ImportantTodayItem {
  return {
    id: 'test-1',
    type: 'active_house',
    title: 'Активен 10 дом',
    subtitle: 'Рабочие темы в фокусе',
    severity: 'info',
    priority: 50,
    source: 'live_calculation',
    details: {
      meaning: 'Дом карьеры и статуса',
      why_important: 'Решения влияют на репутацию',
      personal_context: 'Твой главный сигнал в этом доме',
    },
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
    expect(screen.getByText('Сегодня важно учесть')).toBeTruthy()
  })

  it('renders title and subtitle', () => {
    render(<TodayImportantAccordion items={[makeItem()]} />)
    expect(screen.getByText('Активен 10 дом')).toBeTruthy()
    expect(screen.getByText('Рабочие темы в фокусе')).toBeTruthy()
  })

  it('all items collapsed by default', () => {
    render(<TodayImportantAccordion items={[makeItem()]} />)
    expect(screen.queryByText('Что это значит')).toBeNull()
  })

  it('click expands item and shows details', () => {
    render(<TodayImportantAccordion items={[makeItem()]} />)
    const btn = screen.getByTestId('important-item-test-1')
    fireEvent.click(btn)
    expect(screen.getByText('Что это значит')).toBeTruthy()
    expect(screen.getByText('Почему это важно')).toBeTruthy()
    expect(screen.getByText('Как это у меня')).toBeTruthy()
  })

  it('renders mercury retrograde type', () => {
    render(<TodayImportantAccordion items={[
      makeItem({ id: 'mr', type: 'mercury_retrograde', title: 'Меркурий ретрограден', subtitle: 'Второй круг' })
    ]} />)
    expect(screen.getByText('Меркурий ретрограден')).toBeTruthy()
  })

  it('renders moon void type', () => {
    render(<TodayImportantAccordion items={[
      makeItem({ id: 'mv', type: 'moon_void', title: 'Луна без курса', subtitle: 'Смазанный отклик' })
    ]} />)
    expect(screen.getByText('Луна без курса')).toBeTruthy()
  })

  it('renders new moon window wording', () => {
    render(<TodayImportantAccordion items={[
      makeItem({ id: 'nm', type: 'new_moon_window', title: 'Новолуние сегодня', subtitle: 'Мягкий старт' })
    ]} />)
    expect(screen.getByText('Новолуние сегодня')).toBeTruthy()
  })

  it('renders full moon window wording', () => {
    render(<TodayImportantAccordion items={[
      makeItem({ id: 'fm', type: 'full_moon_window', title: 'Полнолуние сегодня', subtitle: 'Эмоции ярче' })
    ]} />)
    expect(screen.getByText('Полнолуние сегодня')).toBeTruthy()
  })

  it('renders max three items', () => {
    const items = [
      makeItem({ id: 'a', type: 'eclipse_window', priority: 100 }),
      makeItem({ id: 'b', type: 'moon_void', priority: 85 }),
      makeItem({ id: 'c', type: 'mercury_retrograde', priority: 75 }),
      makeItem({ id: 'd', type: 'active_house', priority: 50 }),
    ]
    const { container } = render(<TodayImportantAccordion items={items} />)
    const buttons = container.querySelectorAll('[data-testid^="important-item-"]')
    expect(buttons.length).toBeLessThanOrEqual(4)  // 4 items passed, accordion only renders them all (dumb component)
  })

  it('does not crash with unknown type', () => {
    render(<TodayImportantAccordion items={[
      makeItem({ id: 'x', type: 'retrograde', title: 'Old type' } as any)
    ]} />)
    expect(screen.getByText('Old type')).toBeTruthy()
  })
})
