import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'
import { MessageBubble } from '@/components/chat/message-bubble'

function makeMessage(role: 'user' | 'assistant', content: string) {
  return { id: '1', role, content, createdAt: Date.now() }
}

describe('MessageBubble', () => {
  it('user message is right-aligned with bg-primary styling', () => {
    const { container } = render(
      <MessageBubble message={makeMessage('user', 'Hello')} />,
    )
    const li = container.querySelector('li')
    expect(li?.className).toContain('justify-end')
    const inner = li?.querySelector('div')
    expect(inner?.className).toContain('bg-primary')
    expect(inner?.className).toContain('text-primary-foreground')
  })

  it('assistant message is left-aligned with border styling', () => {
    const { container } = render(
      <MessageBubble message={makeMessage('assistant', 'Hi there')} />,
    )
    const li = container.querySelector('li')
    expect(li?.className).toContain('justify-start')
    const inner = li?.querySelector('div')
    expect(inner?.className).toContain('border')
    expect(inner?.className).toContain('border-border')
  })

  it('streaming=true shows a blinking caret cursor', () => {
    const { container } = render(
      <MessageBubble
        message={makeMessage('assistant', 'Loading...')}
        streaming
      />,
    )
    const caret = container.querySelector('span[aria-hidden]')
    expect(caret).toBeTruthy()
    expect(caret?.getAttribute('style')).toContain('lumen-caret')
  })

  it('streaming=false does not show a caret', () => {
    const { container } = render(
      <MessageBubble
        message={makeMessage('assistant', 'Done')}
        streaming={false}
      />,
    )
    const caret = container.querySelector('span[aria-hidden]')
    expect(caret).toBeNull()
  })

  it('renders very long message text', () => {
    const longText = 'А'.repeat(5000)
    render(
      <MessageBubble message={makeMessage('user', longText)} />,
    )
    expect(screen.getByText(longText)).toBeTruthy()
  })

  it('preserves whitespace via whitespace-pre-wrap', () => {
    const whitespaceText = 'line1\n  line2  \nline3'
    const { container } = render(
      <MessageBubble message={makeMessage('assistant', whitespaceText)} />,
    )
    const p = container.querySelector('p')
    expect(p?.className).toContain('whitespace-pre-wrap')
    expect(p?.textContent).toBe(whitespaceText)
  })
})
