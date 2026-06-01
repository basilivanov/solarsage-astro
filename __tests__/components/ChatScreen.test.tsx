import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

vi.mock('@/lib/log', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn(), back: vi.fn() }),
  usePathname: () => '/',
  useParams: () => ({}),
  useSearchParams: () => new URLSearchParams(),
}))

vi.mock('@/hooks/use-chat', () => ({
  useChat: vi.fn(),
}))

vi.mock('@/lib/chat', () => ({
  buildContextSummary: vi.fn(() => 'Your profile summary'),
  suggestedPrompts: vi.fn(() => ['Prompt 1', 'Prompt 2']),
}))

vi.mock('@/components/chat/chat-empty', () => ({
  ChatEmpty: (props: any) => <div data-testid="chat-empty">{props.children}</div>,
}))
vi.mock('@/components/chat/composer', () => ({
  Composer: () => <div data-testid="composer" />,
}))
vi.mock('@/components/chat/context-pill', () => ({
  ContextPill: (props: any) => (
    <div data-testid="context-pill">{props.summary}</div>
  ),
}))
vi.mock('@/components/chat/message-bubble', () => ({
  MessageBubble: (props: any) => (
    <div data-testid="message-bubble">
      {props.message.content}
      {props.streaming ? ' [streaming]' : ''}
    </div>
  ),
}))
vi.mock('@/components/chat/suggested-prompts', () => ({
  SuggestedPrompts: (props: any) => (
    <div data-testid="suggested-prompts">
      {props.prompts?.join(',')}
    </div>
  ),
}))

vi.mock('lucide-react', () => ({
  Trash2: () => <span data-testid="icon-trash" />,
  Sparkles: () => <span data-testid="icon-sparkles" />,
}))

import { useChat } from '@/hooks/use-chat'
import { ChatScreen } from '@/components/chat/chat-screen'

describe('ChatScreen', () => {
  const profile = { name: 'Test User', id: '123' } as any

  beforeEach(() => {
    vi.clearAllMocks()
    Element.prototype.scrollIntoView = vi.fn()
    Element.prototype.scrollTo = vi.fn()
  })

  it('returns null when not loaded', () => {
    vi.mocked(useChat).mockReturnValue({
      messages: [],
      pending: false,
      streamingId: null,
      send: vi.fn(),
      stop: vi.fn(),
      reset: vi.fn(),
      loaded: false,
    } as any)

    const { container } = render(<ChatScreen profile={profile} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders empty state with chat-empty and suggested prompts', () => {
    vi.mocked(useChat).mockReturnValue({
      messages: [],
      pending: false,
      streamingId: null,
      send: vi.fn(),
      stop: vi.fn(),
      reset: vi.fn(),
      loaded: true,
    } as any)

    render(<ChatScreen profile={profile} />)
    expect(screen.getByTestId('chat-empty')).toBeTruthy()
    expect(screen.getByTestId('suggested-prompts')).toBeTruthy()
    expect(screen.queryByTestId('message-bubble')).toBeNull()
  })

  it('renders messages list', () => {
    vi.mocked(useChat).mockReturnValue({
      messages: [
        { id: '1', content: 'Hello', role: 'user' },
        { id: '2', content: 'Hi there', role: 'assistant' },
      ],
      pending: false,
      streamingId: null,
      send: vi.fn(),
      stop: vi.fn(),
      reset: vi.fn(),
      loaded: true,
    } as any)

    render(<ChatScreen profile={profile} />)
    const bubbles = screen.getAllByTestId('message-bubble')
    expect(bubbles).toHaveLength(2)
    expect(bubbles[0].textContent).toContain('Hello')
    expect(bubbles[1].textContent).toContain('Hi there')
  })

  it('renders typing indicator when pending without streaming', () => {
    vi.mocked(useChat).mockReturnValue({
      messages: [
        { id: '1', content: 'User msg', role: 'user' },
      ],
      pending: true,
      streamingId: null,
      send: vi.fn(),
      stop: vi.fn(),
      reset: vi.fn(),
      loaded: true,
    } as any)

    render(<ChatScreen profile={profile} />)
    expect(screen.getByLabelText('Ассистент печатает')).toBeTruthy()
  })
})
