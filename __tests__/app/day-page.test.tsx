import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

const { mockUseDay } = vi.hoisted(() => ({
  mockUseDay: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ date: '2026-07-05' }),
  useRouter: () => ({
    replace: vi.fn(),
    push: vi.fn(),
  }),
}));

vi.mock('@/lib/grace/hooks/useDay', () => ({
  useDay: mockUseDay,
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
  TodayScreen: () => <div data-testid="today-screen" />,
}));

describe('DayPage', () => {
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
});
