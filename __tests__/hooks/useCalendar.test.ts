// AI_HEADER
// module: M-WEB-HOOKS-TESTS
// wave: W-2.1
// purpose: Unit tests for useCalendar hook

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useCalendar } from '../../lib/grace/hooks/useCalendar';
import type { components } from '../../packages/contracts/_generated';

type CalendarPayload = components['schemas']['CalendarPayload'];

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch as any;

describe('useCalendar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockReset();
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
      allowedRange: {
        from: '2026-05-01',
        to: '2026-05-31',
      },
      days: [
        {
          date: '2026-05-01',
          dayNumber: 1,
          isCurrentMonth: true,
          isToday: false,
          disabled: false,
          dayStatus: 'supportive',
          access: {
            state: 'full',
            reason: null,
            referralDaysLeft: null,
            subscriptionActive: null,
            accessUntil: null,
          },
        },
      ],
    };

    (mockFetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockPayload,
    });

    const { result } = renderHook(() => useCalendar('2026-05'));

    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(mockPayload);
    expect(result.current.error).toBeNull();
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/calendar?month=2026-05',
      expect.objectContaining({
        credentials: 'include',
      })
    );
  });

  it('should handle API errors with error code', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 403,
      json: async () => ({
        detail: {
          code: 'ACCESS_DENIED',
          message: 'Calendar access denied',
        },
      }),
    });

    const { result } = renderHook(() => useCalendar('2026-05'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeTruthy();
    expect(result.current.error?.status).toBe(403);
    expect(result.current.error?.code).toBe('ACCESS_DENIED');
    expect(result.current.error?.message).toBe('Calendar access denied');
  });

  it('should handle API errors without error code', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: async () => {
        throw new Error('Not JSON');
      },
    });

    const { result } = renderHook(() => useCalendar('2026-05'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeTruthy();
    expect(result.current.error?.status).toBe(404);
    expect(result.current.error?.message).toBe('Not Found');
  });

  it('should handle network errors', async () => {
    (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useCalendar('2026-05'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeTruthy();
    expect(result.current.error?.message).toBe('Unknown error');
    expect(result.current.error?.status).toBe(500);
  });

  it('should cancel request on unmount', async () => {
    let resolvePromise: (value: any) => void;
    const promise = new Promise((resolve) => {
      resolvePromise = resolve;
    });

    (global.fetch as any).mockReturnValueOnce(promise);

    const { result, unmount } = renderHook(() => useCalendar('2026-05'));

    expect(result.current.loading).toBe(true);

    unmount();

    // Resolve after unmount
    resolvePromise!({
      ok: true,
      json: async () => ({ month: '2026-05' }),
    });

    await waitFor(() => {
      // State should not update after unmount
      expect(result.current.loading).toBe(true);
    });
  });

  it('should refetch when month changes', async () => {
    const mockPayload1: Partial<CalendarPayload> = {
      month: '2026-05',
      title: 'May 2026',
    };

    const mockPayload2: Partial<CalendarPayload> = {
      month: '2026-06',
      title: 'June 2026',
    };

    (global.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockPayload1,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockPayload2,
      });

    const { result, rerender } = renderHook(
      ({ month }) => useCalendar(month),
      { initialProps: { month: '2026-05' } }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data?.month).toBe('2026-05');

    // Change month
    rerender({ month: '2026-06' });

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data?.month).toBe('2026-06');
    expect(global.fetch).toHaveBeenCalledTimes(2);
  });
});
