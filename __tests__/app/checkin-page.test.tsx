import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { mockPush, mockBack, mockSearchParamsGet } = vi.hoisted(() => ({
  mockPush: vi.fn(),
  mockBack: vi.fn(),
  mockSearchParamsGet: vi.fn(),
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    back: mockBack,
  }),
  useSearchParams: () => ({
    get: mockSearchParamsGet,
  }),
}))

vi.mock('@/hooks/use-profile', () => ({
  useProfile: () => ({
    profile: {
      currentLocation: null,
      birthLocation: null,
    },
  }),
}))

vi.mock('@/components/checkin/checkin-screen', () => ({
  CheckinScreen: ({ targetDate, onComplete }: { targetDate: string; onComplete?: (result: unknown) => void }) => (
    <button
      type="button"
      data-testid="complete-checkin"
      onClick={() => onComplete?.({ targetDate })}
    >
      complete {targetDate}
    </button>
  ),
}))

import CheckinPage from '@/app/(grace)/checkin/page'

describe('CheckinPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSearchParamsGet.mockImplementation((key: string) => (
      key === 'target' ? '2026-07-05' : null
    ))
  })

  it('routes to the real day page after successful check-in', () => {
    render(<CheckinPage />)

    fireEvent.click(screen.getByTestId('complete-checkin'))

    expect(mockPush).toHaveBeenCalledWith('/day/2026-07-05')
  })
})
