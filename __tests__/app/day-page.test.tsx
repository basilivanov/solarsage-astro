import React from 'react';
import { act, render, screen } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';

const { mockUseDay, mockGetMonthCalendar, mockTodayScreen } = vi.hoisted(() => ({
  mockUseDay: vi.fn(),
  mockGetMonthCalendar: vi.fn(),
  mockTodayScreen: vi.fn(() => <div data-testid="today-screen" />),
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ date: '2026-07-05' }),
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({
    replace: vi.fn(),
    push: vi.fn(),
  }),
}));

vi.mock('@/lib/grace/hooks/useDay', () => ({
  useDay: mockUseDay,
}));

vi.mock('@/lib/api/calendar', () => ({
  getMonthCalendar: mockGetMonthCalendar,
}));

vi.mock('@/hooks/use-onboarded', () => ({
  useOnboarded: () => ({ setOnboarded: vi.fn() }),
}));

vi.mock('@/components/shared/cosmic-loader', () => ({
  CosmicLoader: () => <div data-testid="cosmic-loader" />,
}));

vi.mock('@/components/grace/ErrorBoundary', () => ({
  ErrorBoundary: ({ message }: { message: string }) => (
    <div data-testid="day-error">{message}</div>
  ),
}));

vi.mock('@/components/today/today-screen', () => ({
  TodayScreen: mockTodayScreen,
}));

describe('DayPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetMonthCalendar.mockResolvedValue({ days: [] });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders API errors before the local loader state', async () => {
    mockUseDay.mockReturnValue({
      data: null,
      loading: false,
      error: new Error('Service unavailable'),
    });

    const { default: DayPage } = await import(
      '@/app/(grace)/day/[date]/page'
    );
    render(<DayPage />);

    expect(screen.getByTestId('day-error').textContent).toBe(
      'Service unavailable'
    );
    expect(screen.queryByTestId('cosmic-loader')).toBeNull();
  });

  it('loads matching lunar facts from the real calendar payload and passes them to TodayScreen', async () => {
    vi.useFakeTimers();

    mockUseDay.mockReturnValue({
      data: {
        date: '2026-07-05',
        title: 'Today',
        headline: 'Headline',
        dayStatus: 'supportive',
        topFlags: [],
        reading: { paragraphs: ['Paragraph'] },
        notes: null,
        whyThisHappens: { sections: [] },
        meta: {
          schemaVersion: 'today/v1',
          contractVersion: 1,
          calculationVersion: 1,
          normalizationVersion: 1,
          scoringVersion: 1,
          promptVersion: 1,
          contentVersion: 1,
          generatedAt: '2026-07-05T00:00:00Z',
          cached: false,
        },
        access: { state: 'full', referralDaysLeft: 7 },
        weekStrip: [],
        microcopy: [],
        importantToday: [],
        dayChart: null,
        planetInfluences: [],
        sphereScores: [],
      },
      loading: false,
      error: null,
    });

    mockGetMonthCalendar.mockResolvedValue({
      meta: {
        schemaVersion: 'calendar/v1',
        contractVersion: 1,
        generatedAt: '2026-07-01T00:00:00Z',
      },
      month: '2026-07',
      title: 'Июль 2026',
      allowedRange: { from: '2026-06-01', to: '2026-08-31' },
      days: [
        {
          date: '2026-07-05',
          dayNumber: 5,
          isCurrentMonth: true,
          isToday: false,
          disabled: false,
          dayStatus: 'supportive',
          access: { state: 'full' },
          lunar: {
            phase: 'Полнолуние',
            illumination: 98,
            moonSign: 'Aquarius',
            lunarDay: 15,
            voidOfCourse: true,
          },
        },
      ],
    });

    const { default: DayPage } = await import(
      '@/app/(grace)/day/[date]/page'
    );
    render(<DayPage />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(700);
    });

    expect(mockGetMonthCalendar).toHaveBeenCalledWith(2026, 6);
    expect(mockTodayScreen).toHaveBeenCalled();
    const lastCall = mockTodayScreen.mock.calls[mockTodayScreen.mock.calls.length - 1];
    if (!lastCall) {
      throw new Error('TodayScreen was not called');
    }
    const props = (lastCall as unknown as [Record<string, unknown>])[0];
    expect(props.calendarLunar).toMatchObject({
      phase: 'Полнолуние',
      illumination: 98,
      lunarDay: 15,
    });
  });
});
