
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_PAYWALL_TEST
// ROLE: Unit tests for the production Paywall with the REAL subscription
//       flow (catalog price CTA, provider checkout, confirmed-status unlock)
//       and the unchanged test-only monetization stub copy.
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for Paywall behavior.
// owns:
//   - __tests__/components/Paywall.test.tsx
// inputs: Mocks, fixtures
// outputs: Assertion results
// dependencies: local modules
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - The production paywall never shows "скоро появится"; prices come from
//     the mocked catalog only.
// failure_policy: log and raise
// END_MODULE_CONTRACT
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
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

vi.mock('lucide-react', () => ({
  Lock: () => <span data-testid="icon-lock" />,
  Crown: () => <span data-testid="icon-crown" />,
  UserPlus: () => <span data-testid="icon-user-plus" />,
}))

vi.mock('@/lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
}))

const mockGetPaymentProducts = vi.fn()
const mockStartSubscription = vi.fn()
const mockOpenProviderCheckout = vi.fn()
const mockPollSubscriptionStatus = vi.fn()

vi.mock('@/lib/api/payment', () => ({
  PaymentApiError: class PaymentApiError extends Error {
    status: number
    code?: string
    constructor({ status, code, message }: { status: number; code?: string; message: string }) {
      super(message)
      this.status = status
      this.code = code
    }
  },
  getPaymentProducts: (...args: unknown[]) => mockGetPaymentProducts(...args),
  startSubscription: (...args: unknown[]) => mockStartSubscription(...args),
  cancelSubscription: vi.fn(),
}))

vi.mock('@/lib/billing/purchase-flow', () => ({
  PurchasePollTimeoutError: class PurchasePollTimeoutError extends Error {},
  openProviderCheckout: (...args: unknown[]) => mockOpenProviderCheckout(...args),
  pollSubscriptionStatus: (...args: unknown[]) => mockPollSubscriptionStatus(...args),
  pollPurchaseStatus: vi.fn(),
}))

const mockFetch = vi.fn()

import { Paywall } from '@/components/paywall'
import { Paywall as MonetizationPaywall } from '@/components/monetization/paywall'

const PRODUCTS = {
  products: [
    { slug: 'subscription_month', name: 'Подписка на 1 месяц', description: null, productType: 'subscription_recurrent', priceKopecks: 9900, currency: 'RUB', periodDays: 30, horaryQuota: null },
    { slug: 'subscription_year', name: 'Подписка на 1 год', description: null, productType: 'subscription_recurrent', priceKopecks: 99900, currency: 'RUB', periodDays: 365, horaryQuota: null },
  ],
}

describe('Paywall', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    globalThis.fetch = mockFetch
    mockFetch.mockResolvedValue({
      json: () => Promise.resolve({ inviteUrl: 'https://t.me/invite-link' }),
    })
    mockGetPaymentProducts.mockResolvedValue(PRODUCTS)
  })

  it('renders default title', () => {
    render(<Paywall />)
    expect(
      screen.getByText('Твой персональный разбор уже готов'),
    ).toBeTruthy()
  })

  it('renders custom title', () => {
    render(<Paywall title="Custom paywall title" />)
    expect(screen.getByText('Custom paywall title')).toBeTruthy()
  })

  it('shows the real catalog month price on the CTA, never "скоро появится"', async () => {
    render(<Paywall />)
    const cta = await screen.findByTestId('paywall-subscribe-cta')
    await waitFor(() => {
      expect(cta.textContent).toContain('Подписка · 99 ₽/мес')
    })
    expect((cta as HTMLButtonElement).disabled).toBe(false)
    expect(screen.queryByText(/скоро появится/i)).toBeNull()
  })

  it('disables the CTA honestly when billing is unavailable', async () => {
    mockGetPaymentProducts.mockRejectedValue(new Error('503'))
    render(<Paywall />)
    const cta = await screen.findByTestId('paywall-subscribe-cta')
    await waitFor(() => {
      expect(cta.textContent).toContain('Оплата временно недоступна')
    })
    expect((cta as HTMLButtonElement).disabled).toBe(true)
  })

  it('buy flow: start -> provider checkout -> confirmed active -> onUnlocked', async () => {
    const onUnlocked = vi.fn()
    mockStartSubscription.mockResolvedValue({
      subscriptionId: 's-1',
      productSlug: 'subscription_month',
      providerPaymentId: 'prov-1',
      confirmationUrl: 'https://pay.example/c',
      status: 'pending',
    })
    mockPollSubscriptionStatus.mockResolvedValue({ status: 'active', hasAccess: true })

    render(<Paywall onUnlocked={onUnlocked} />)
    const cta = await screen.findByTestId('paywall-subscribe-cta')
    await waitFor(() => expect((cta as HTMLButtonElement).disabled).toBe(false))
    fireEvent.click(cta)

    await waitFor(() => expect(mockStartSubscription).toHaveBeenCalledWith('subscription_month'))
    await waitFor(() => expect(mockOpenProviderCheckout).toHaveBeenCalledWith('https://pay.example/c'))
    await waitFor(() => expect(mockPollSubscriptionStatus).toHaveBeenCalledWith('s-1'))
    await waitFor(() => expect(onUnlocked).toHaveBeenCalledTimes(1))
  })

  it('keeps the test-only monetization stub copy unchanged', () => {
    render(<MonetizationPaywall />)
    expect(screen.queryByRole('button', { name: 'Оформить подписку' })).toBeNull()
    expect(
      (screen.getByRole('button', { name: 'Подписка скоро появится' }) as HTMLButtonElement).disabled,
    ).toBe(true)
  })

  it('renders invite button', () => {
    render(<Paywall />)
    expect(screen.getByText('Пригласить друга · +14 дней')).toBeTruthy()
  })

  it('calls fetch for referral URL on mount', async () => {
    render(<Paywall />)
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/referral',
        { credentials: 'include' },
      )
    })
  })

  it('applies compact padding when compact=true', () => {
    const { container } = render(<Paywall compact />)
    const section = container.querySelector('section')
    expect(section?.className).toContain('p-5')
  })

  it('does not render description <p> when description is empty string', () => {
    const { container } = render(<Paywall description="" />)
    const textCenterDiv = container.querySelector('.text-center')
    const paragraphs = textCenterDiv?.querySelectorAll('p')
    expect(paragraphs?.length).toBe(0)
  })

  it('merges className prop via cn()', () => {
    const { container } = render(<Paywall className="custom-class" />)
    const section = container.querySelector('section')
    expect(section?.className).toContain('custom-class')
  })
})
