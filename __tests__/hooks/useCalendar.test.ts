// AI_HEADER
// module: M-WEB-HOOKS-TESTS
// wave: W-2.1
// purpose: Unit tests for useCalendar hook

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import type { components } from '../../packages/contracts/_generated';

type CalendarPayload = components['schemas']['CalendarPayload'];

const { mockFetchCalendar } = vi.hoisted(() => ({
  mockFetchCalendar: vi.fn(),
}));

vi.mock('../../lib/grace/api/client', () => ({
  fetchCalendar: mockFetchCalendar,
  fetchDay: vi.fn(),
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

vi.mock('@/hooks/use-telegram-auth', () => ({
  useTelegramAuth: () => ({
    isLoading: false,
    isAuthenticated: true,
    error: null,
  }),
}));

import { useCalendar } from '../../lib/grace/hooks/useCalendar';
import { ApiError } from '../../lib/grace/api/client';

describe('useCalendar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch calendar data successfully', async () => {
    const mockPayload: CalendarPayload = {
      meta: {
        schemaVersion: 'calendar/v1',
        contractVersion: 1,
        generatedAt: '2026-05-30T12:00:00Z',
      },
      month: '2026-05',
      title: 'May 2026',
      allowedRange: { from: '2026-05-01', to: '2026-05-31' },
      days: [{
        date: '2026-05-01', dayNumber: 1,
        isCurrentMonth: true, isToday: false, disabled: false,
        dayStatus: 'supportive',
        access: { state: 'full', reason: null, referralDaysLeft: null, subscriptionActive: null, accessUntil: null },
      }],
    };

    mockFetchCalendar.mockResolvedValueOnce(mockPayload);

    const { result } = renderHook(() => useCalendar('2026-05'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(mockPayload);
    expect(result.current.error).toBeNull();
    expect(mockFetchCalendar).toHaveBeenCalledWith('2026-05');
  });

  it('should handle API errors with error code', async () => {
    mockFetchCalendar.mockRejectedValueOnce(
      new ApiError('Calendar access denied', 403, 'ACCESS_DENIED')
    );

    const { result } = renderHook(() => useCalendar('2026-05'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeTruthy();
    expect(result.current.error?.status).toBe(403);
    expect(result.current.error?.code).toBe('ACCESS_DENIED');
  });

  it('should handle API errors without error code', async () => {
    mockFetchCalendar.mockRejectedValueOnce(
      new ApiError('Not Found', 404)
    );

    const { result } = renderHook(() => useCalendar('2026-05'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeTruthy();
    expect(result.current.error?.status).toBe(404);
  });

  it('should handle network errors', async () => {
    mockFetchCalendar.mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useCalendar('2026-05'));

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

    mockFetchCalendar.mockReturnValueOnce(promise);

    const { result, unmount } = renderHook(() => useCalendar('2026-05'));

    await waitFor(() => {
      expect(result.current.loading).toBe(true);
    });

    unmount();
    resolvePromise!({ month: '2026-05' });
    expect(result.current.loading).toBe(true);
  });

  it('should refetch when month changes', async () => {
    mockFetchCalendar
      .mockResolvedValueOnce({ month: '2026-05', title: 'May 2026' })
      .mockResolvedValueOnce({ month: '2026-06', title: 'June 2026' });

    const { result, rerender } = renderHook(
      ({ month }) => useCalendar(month),
      { initialProps: { month: '2026-05' } }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.data?.month).toBe('2026-05');

    rerender({ month: '2026-06' });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.data?.month).toBe('2026-06');
    expect(mockFetchCalendar).toHaveBeenCalledTimes(2);
  });
});
