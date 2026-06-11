
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_COMPOSER_TEST
// ROLE: Unit tests for Composer.test.tsx
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Unit tests for Composer.test.tsx — __tests__/components/Composer.test.tsx
// owns:
//   - __tests__/components/Composer.test.tsx
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'
import { Composer } from '@/components/chat/composer'

describe('Composer', () => {
  it('disables submit button when input is empty', () => {
    render(<Composer onSend={vi.fn()} />)
    const btn = screen.getByLabelText('Отправить')
    expect((btn as HTMLButtonElement).disabled).toBe(true)
  })

  it('submits on Enter key (without Shift)', () => {
    const onSend = vi.fn()
    render(<Composer onSend={onSend} />)
    const textarea = screen.getByLabelText('Сообщение')

    fireEvent.change(textarea, { target: { value: '  hello  ' } })
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })

    expect(onSend).toHaveBeenCalledWith('hello')
  })

  it('does not submit on Shift+Enter (inserts newline)', () => {
    const onSend = vi.fn()
    render(<Composer onSend={onSend} />)
    const textarea = screen.getByLabelText('Сообщение')

    fireEvent.change(textarea, { target: { value: 'hello' } })
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true })

    expect(onSend).not.toHaveBeenCalled()
  })

  it('shows stop button when streaming=true and onStop provided', () => {
    const onStop = vi.fn()
    render(<Composer onSend={vi.fn()} onStop={onStop} streaming />)

    expect(screen.getByLabelText('Остановить ответ')).toBeTruthy()
    expect(screen.queryByLabelText('Отправить')).toBeNull()
  })

  it('shows submit arrow button when streaming=false', () => {
    render(<Composer onSend={vi.fn()} streaming={false} />)

    expect(screen.getByLabelText('Отправить')).toBeTruthy()
    expect(screen.queryByLabelText('Остановить ответ')).toBeNull()
  })

  it('blocks submit when disabled=true', () => {
    const onSend = vi.fn()
    render(<Composer onSend={onSend} disabled />)

    const textarea = screen.getByLabelText('Сообщение')
    fireEvent.change(textarea, { target: { value: 'hello' } })

    const btn = screen.getByLabelText('Отправить')
    expect((btn as HTMLButtonElement).disabled).toBe(true)

    // Also verify form submit is blocked
    fireEvent.submit(textarea.closest('form')!)
    expect(onSend).not.toHaveBeenCalled()
  })

  it('submit sends value.trim() and clears input', () => {
    const onSend = vi.fn()
    render(<Composer onSend={onSend} />)
    const textarea = screen.getByLabelText('Сообщение')

    fireEvent.change(textarea, { target: { value: '  hello world  ' } })
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })

    expect(onSend).toHaveBeenCalledWith('hello world')
    // Input should be cleared after submit
    expect((textarea as HTMLTextAreaElement).value).toBe('')
  })

  it('has aria-label="Сообщение" on textarea', () => {
    render(<Composer onSend={vi.fn()} />)
    const textarea = screen.getByLabelText('Сообщение')
    expect(textarea.tagName).toBe('TEXTAREA')
  })
})
