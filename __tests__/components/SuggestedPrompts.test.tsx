
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_SUGGESTEDPROMPTS_TEST
// ROLE: Unit tests for SuggestedPrompts.test.tsx
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for SuggestedPromptstsx behavior
// owns:
//   - __tests__/components/SuggestedPrompts.test.tsx
// inputs: Mocks, fixtures
// outputs: Assertion results
// dependencies: local modules
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'
import { SuggestedPrompts } from '@/components/chat/suggested-prompts'

describe('SuggestedPrompts', () => {
  const prompts = [
    'Что говорит моя карта про карьеру?',
    'Стоит ли начинать новый проект сейчас?',
    'Какой главный аспект у меня на этой неделе?',
  ]

  it('renders list of prompt buttons', () => {
    render(<SuggestedPrompts prompts={prompts} onPick={vi.fn()} />)
    const buttons = screen.getAllByRole('button')
    expect(buttons).toHaveLength(3)
    prompts.forEach((text) => {
      expect(screen.getByText(text)).toBeTruthy()
    })
  })

  it('calls onPick with prompt text on click', () => {
    const onPick = vi.fn()
    render(<SuggestedPrompts prompts={prompts} onPick={onPick} />)

    fireEvent.click(screen.getByText(prompts[1]))
    expect(onPick).toHaveBeenCalledTimes(1)
    expect(onPick).toHaveBeenCalledWith(prompts[1])
  })

  it('renders empty list when prompts array is empty', () => {
    const { container } = render(
      <SuggestedPrompts prompts={[]} onPick={vi.fn()} />,
    )
    const buttons = container.querySelectorAll('button')
    expect(buttons).toHaveLength(0)
  })
})
