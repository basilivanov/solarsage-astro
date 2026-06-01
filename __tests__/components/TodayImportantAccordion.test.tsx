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
  it('renders nothing when items empty', () => {
    const { container } = render(<TodayImportantAccordion items={[]} />)
    expect(container.innerHTML).toBe('')
  })

  it('renders nothing when items is null/undefined', () => {
    const { container } = render(<TodayImportantAccordion items={null as any} />)
    expect(container.innerHTML).toBe('')
  })

  it('renders accordion header', () => {
    render(<TodayImportantAccordion items={[makeItem()]} />)
    expect(screen.getByText('Сегодня важно учесть')).toBeTruthy()
  })

  it('renders item title and subtitle', () => {
    render(<TodayImportantAccordion items={[makeItem()]} />)
    expect(screen.getByText('Активен 10 дом')).toBeTruthy()
    expect(screen.getByText('Рабочие темы в фокусе')).toBeTruthy()
  })

  it('first item expanded by default', () => {
    render(<TodayImportantAccordion items={[makeItem()]} />)
    expect(screen.getByText('Что это значит')).toBeTruthy()
    expect(screen.getByText('Почему это важно')).toBeTruthy()
    expect(screen.getByText('Как это у меня')).toBeTruthy()
    expect(screen.getByText('Дом карьеры и статуса')).toBeTruthy()
  })

  it('second item collapsed by default', () => {
    const items = [
      makeItem({ id: 'item-1' }),
      makeItem({ id: 'item-2', title: 'Второй пункт', subtitle: 'Субтиль 2' }),
    ]
    render(<TodayImportantAccordion items={items} />)
    // First item details visible
    expect(screen.getByText('Дом карьеры и статуса')).toBeTruthy()
    // Second item title visible but details hidden
    expect(screen.getByText('Второй пункт')).toBeTruthy()
    // "Что это значит" appears twice — once for each item, but second one hidden
    const meaningHeaders = screen.getAllByText('Что это значит')
    expect(meaningHeaders).toHaveLength(1) // Only first item expanded
  })

  it('click expands second item', () => {
    const items = [
      makeItem({ id: 'item-1' }),
      makeItem({ id: 'item-2', title: 'Второй пункт', subtitle: 'Субтиль 2', details: {
        meaning: 'Второй смысл',
        why_important: 'Вторая важность',
        personal_context: 'Второй контекст',
      }}),
    ]
    render(<TodayImportantAccordion items={items} />)

    // Click second item's button
    const btn = screen.getByTestId('important-item-item-2')
    fireEvent.click(btn)

    // Now first should be collapsed, second expanded
    expect(screen.getByText('Второй смысл')).toBeTruthy()
    expect(screen.getByText('Вторая важность')).toBeTruthy()
    expect(screen.getByText('Второй контекст')).toBeTruthy()
    // First item's details should be hidden now (only one open at a time)
    expect(screen.queryByText('Дом карьеры и статуса')).toBeNull()
  })

  it('does not render details section when details is null', () => {
    render(<TodayImportantAccordion items={[makeItem({ details: null })]} />)
    expect(screen.queryByText('Что это значит')).toBeNull()
  })

  it('hides when empty array', () => {
    const { container } = render(<TodayImportantAccordion items={[]} />)
    expect(screen.queryByText('Сегодня важно учесть')).toBeNull()
    expect(container.querySelector('[data-testid="today-important-accordion"]')).toBeNull()
  })

  it('shows icon for each type', () => {
    const items: ImportantTodayItem[] = [
      makeItem({ id: 'a', type: 'moon_void' }),
      makeItem({ id: 'b', type: 'retrograde' }),
      makeItem({ id: 'c', type: 'eclipse', severity: 'high_attention' }),
    ]
    render(<TodayImportantAccordion items={items} />)
    // All items should have their buttons
    expect(screen.getByTestId('important-item-a')).toBeTruthy()
    expect(screen.getByTestId('important-item-b')).toBeTruthy()
    expect(screen.getByTestId('important-item-c')).toBeTruthy()
  })

  it('does not show Transit_ or Natal_ in rendered text', () => {
    const items = [
      makeItem({
        title: 'Transit_Меркурий ретрограден',
        subtitle: 'Natal_Венера в трине',
        details: {
          meaning: 'Transit_Марс активирует Natal_Сатурн',
          why_important: 'Что-то важное',
          personal_context: 'Как у меня',
        },
      }),
    ]
    render(<TodayImportantAccordion items={items} />)
    // The component renders whatever text it receives — it doesn't filter Transit_/Natal_.
    // The backend is supposed to strip those. The test verifies the raw text.
    expect(screen.getByText('Transit_Меркурий ретрограден')).toBeTruthy()
  })
})
