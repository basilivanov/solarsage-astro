// AI_HEADER
// module: M-WEB-HOOKS-TESTS
// wave: W-2.1
// purpose: Unit tests for useDay hook

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useDay } from '../../lib/grace/hooks/useDay';
import type { components } from '../../packages/contracts/_generated';

type TodayPayload = components['schemas']['TodayPayload'];

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch as any;

describe('useDay', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockReset();
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
      },
      date: '2026-05-30',
      title: 'Test Day',
      subtitle: null,
      headline: 'Test headline',
      dayStatus: 'supportive',
      dayQuality: null,
      topFlags: [],
      reading: {
        paragraphs: [],
      },
      whyThisHappens: {
        sections: [],
      },
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
    };

    (mockFetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockPayload,
    });

    const { result } = renderHook(() => useDay('2026-05-30'));

    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(mockPayload);
    expect(result.current.error).toBeNull();
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/day/2026-05-30',
      expect.objectContaining({
        credentials: 'include',
      })
    );
  });

  it('should handle API errors with error code', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({
        detail: {
          code: 'UNAUTHORIZED',
          message: 'Not authenticated',
        },
      }),
    });

    const { result } = renderHook(() => useDay('2026-05-30'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeTruthy();
    expect(result.current.error?.status).toBe(401);
    expect(result.current.error?.code).toBe('UNAUTHORIZED');
    expect(result.current.error?.message).toBe('Not authenticated');
  });

  it('should handle API errors without error code', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: async () => {
        throw new Error('Not JSON');
      },
    });

    const { result } = renderHook(() => useDay('2026-05-30'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeTruthy();
    expect(result.current.error?.status).toBe(500);
    expect(result.current.error?.message).toBe('Internal Server Error');
  });

  it('should handle network errors', async () => {
    (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useDay('2026-05-30'));

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

    const { result, unmount } = renderHook(() => useDay('2026-05-30'));

    expect(result.current.loading).toBe(true);

    unmount();

    // Resolve after unmount
    resolvePromise!({
      ok: true,
      json: async () => ({ date: '2026-05-30' }),
    });

    await waitFor(() => {
      // State should not update after unmount
      expect(result.current.loading).toBe(true);
    });
  });

  it('should refetch when date changes', async () => {
    const mockPayload1: Partial<TodayPayload> = {
      date: '2026-05-30',
      title: 'Day 1',
    };

    const mockPayload2: Partial<TodayPayload> = {
      date: '2026-05-31',
      title: 'Day 2',
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
      ({ date }) => useDay(date),
      { initialProps: { date: '2026-05-30' } }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data?.date).toBe('2026-05-30');

    // Change date
    rerender({ date: '2026-05-31' });

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data?.date).toBe('2026-05-31');
    expect(global.fetch).toHaveBeenCalledTimes(2);
  });
});
