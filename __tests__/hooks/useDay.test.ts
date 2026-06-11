
// ############################################################################
// AI_HEADER: MODULE_HOOKS_USEDAY_TEST
// ROLE: Unit tests for useDay.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// #########################################// START_MODULE_CONTRACT
// purpose: Tests for useDayts behavior
// owns:
//   - __tests__/hooks/useDay.test.ts
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: React state management
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
// AI_HEADER
// module: M-WEB-HOOKS-TESTS
// wave: W-2.1
// purpose: Unit tests for useDay hook

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import type { components } from '../../packages/contracts/_generated';

type TodayPayload = components['schemas']['TodayPayload'];

const { mockFetchDay } = vi.hoisted(() => ({
  mockFetchDay: vi.fn(),
}));

vi.mock('../../lib/grace/api/client', () => ({
  fetchDay: mockFetchDay,
  fetchCalendar: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number;
    code?: string;
    constructor(message: string, status: number, code?: string) {
      super(message);
      this.status = status;
      this.code = code;
    }
  },
}));

// Mock next/navigation — useDay calls useRouter for NOT_ONBOARDED redirect
// IMPORTANT: factory must return STABLE reference, otherwise useEffect re-fires
const mockRouter = { replace: vi.fn(), push: vi.fn(), back: vi.fn(), prefetch: vi.fn() };
vi.mock('next/navigation', () => ({
  useRouter: () => mockRouter,
  useParams: () => ({}),
  usePathname: () => '/',
}));

// Mock useTelegramAuth — skip auth, always return "authenticated"
vi.mock('@/hooks/use-telegram-auth', () => ({
  useTelegramAuth: () => ({
    isLoading: false,
    isAuthenticated: true,
    error: null,
  }),
}));

import { useDay } from '../../lib/grace/hooks/useDay';
import { ApiError } from '../../lib/grace/api/client';

describe('useDay', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch day data successfully', async () => {
    const mockPayload: TodayPayload = {
      meta: {
        schemaVersion: 'today/v1',
        contractVersion: 1,
        calculationVersion: 1,
        normalizationVersion: 1,
        scoringVersion: 1,
        promptVersion: 1,
        contentVersion: 1,
        generatedAt: '2026-05-30T12:00:00Z',
        cached: false,
      },
      date: '2026-05-30',
      title: 'Test Day',
      subtitle: null,
      headline: 'Test headline',
      dayStatus: 'supportive',
      dayQuality: null,
      topFlags: [],
      reading: { paragraphs: [] },
      whyThisHappens: { sections: [] },
      weekStrip: [],
      microcopy: [],
      access: {
        state: 'full',
        reason: null,
        referralDaysLeft: null,
        subscriptionActive: null,
        accessUntil: null,
      },
      actions: null,
      yesterdayEcho: null,
      activationEvidence: null,
      manifestationZones: null,
      periodContext: null,
      importantToday: [],
    };

    mockFetchDay.mockResolvedValueOnce(mockPayload);

    const { result } = renderHook(() => useDay('2026-05-30'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(mockPayload);
    expect(result.current.error).toBeNull();
    expect(mockFetchDay).toHaveBeenCalledWith('2026-05-30');
  });

  it('should handle API errors with error code', async () => {
    mockFetchDay.mockRejectedValueOnce(
      new ApiError('Not authenticated', 401, 'UNAUTHORIZED')
    );

    const { result } = renderHook(() => useDay('2026-05-30'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeTruthy();
    expect(result.current.error?.status).toBe(401);
    expect(result.current.error?.code).toBe('UNAUTHORIZED');
  });

  it('should handle API errors without error code', async () => {
    mockFetchDay.mockRejectedValueOnce(
      new ApiError('Internal Server Error', 500)
    );

    const { result } = renderHook(() => useDay('2026-05-30'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeTruthy();
    expect(result.current.error?.status).toBe(500);
  });

  it('should handle network errors', async () => {
    mockFetchDay.mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useDay('2026-05-30'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeTruthy();
    expect(result.current.error?.status).toBe(500);
  });

  it('should cancel request on unmount', async () => {
    let resolvePromise: (value: any) => void;
    const promise = new Promise((resolve) => {
      resolvePromise = resolve;
    });

    mockFetchDay.mockReturnValueOnce(promise);

    const { result, unmount } = renderHook(() => useDay('2026-05-30'));

    await waitFor(() => {
      expect(result.current.loading).toBe(true);
    });

    unmount();

    resolvePromise!({ date: '2026-05-30' });

    // Loading should stay true after unmount (state not updated)
    expect(result.current.loading).toBe(true);
  });

  it('should refetch when date changes', async () => {
    // Use implementation that returns correct value by date,
    // avoiding StrictMode double-invoke "Once" semantics issues
    mockFetchDay.mockImplementation((date: string) =>
      Promise.resolve({ date, title: `Day for ${date}` })
    );

    const { result, rerender } = renderHook(
      ({ date }) => useDay(date),
      { initialProps: { date: '2026-05-30' } }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.data?.date).toBe('2026-05-30');

    rerender({ date: '2026-05-31' });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.data?.date).toBe('2026-05-31');
    expect(mockFetchDay).toHaveBeenCalledWith('2026-05-31');
  });
});
