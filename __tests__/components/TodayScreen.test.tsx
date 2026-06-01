// ############################################################################
// AI_HEADER: MODULE_TEST_TODAY_SCREEN
// ROLE: Unit tests for TodayScreen component (W-TEST-2).
// DEPENDENCIES: vitest, @testing-library/react, TodayScreen
// GRACE_ANCHORS: [TEST_TODAY_SCREEN]
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-TODAY-SCREEN
// purpose: Test TodayScreen component rendering and behavior
// owns:
//   - __tests__/components/TodayScreen.test.tsx
// inputs:
//   - TodayPayload mock data
// outputs:
//   - test results (pass/fail)
// dependencies:
//   - components/grace/TodayScreen.tsx
//   - packages/contracts/_generated.ts
// side_effects:
//   - none (tests only)
// invariants:
//   - headline MUST render when payload.headline is present
//   - reading MUST render when payload.reading.paragraphs is non-empty
//   - week-strip MUST render when payload.weekStrip is present
//   - locked state MUST render LockedDay component
// failure_policy:
//   - test failure -> CI fails
// non_goals:
//   - E2E tests, API integration tests
// END_MODULE_CONTRACT: M-TEST-TODAY-SCREEN

// START_MODULE_MAP: M-TEST-TODAY-SCREEN
// public_entrypoints:
//   - test suite (vitest)
// semantic_blocks:
//   - TEST_TODAY_SCREEN
// owned_tests:
//   - this file
// END_MODULE_MAP: M-TEST-TODAY-SCREEN

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TodayScreen } from '@/components/grace/TodayScreen';
import type { components } from '@/packages/contracts/_generated';

type TodayPayload = components['schemas']['TodayPayload'];

// Mock Next.js router
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

// START_BLOCK: TEST_TODAY_SCREEN
describe('TodayScreen', () => {
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
    title: 'Сегодня',
    subtitle: null,
    headline: 'Тестовый заголовок',
    access: { state: 'full' },
    dayStatus: 'supportive',
    dayQuality: null,
    topFlags: [],
    reading: {
      paragraphs: ['Параграф 1', 'Параграф 2'],
    },
    whyThisHappens: {
      sections: [],
    },
    weekStrip: [
      { date: '2026-05-30', dayStatus: 'supportive', isToday: false },
    ],
    microcopy: [],
    yesterdayEcho: null,
    actions: null,
  };

  it('renders headline', () => {
    render(<TodayScreen payload={mockPayload} />);
    const headline = screen.getByTestId('today-headline');
    expect(headline.textContent).toBe('Тестовый заголовок');
  });

  it('renders reading paragraphs', () => {
    render(<TodayScreen payload={mockPayload} />);
    const reading = screen.getByTestId('reading');
    expect(reading).toBeTruthy();
    expect(reading.textContent).toContain('Параграф 1');
    expect(reading.textContent).toContain('Параграф 2');
  });

  it('renders week strip', () => {
    render(<TodayScreen payload={mockPayload} />);
    const weekStrip = screen.getByTestId('week-strip');
    expect(weekStrip).toBeTruthy();
  });

  it('renders subtitle when present', () => {
    const payloadWithSubtitle = {
      ...mockPayload,
      subtitle: 'Тестовый подзаголовок',
    };
    render(<TodayScreen payload={payloadWithSubtitle} />);
    const subtitle = screen.getByText('Тестовый подзаголовок');
    expect(subtitle).toBeTruthy();
  });

  it('renders locked state when access is locked', () => {
    const lockedPayload: TodayPayload = {
      ...mockPayload,
      access: { state: 'locked' },
    };
    render(<TodayScreen payload={lockedPayload} />);
    // Should not render headline when locked
    expect(screen.queryByTestId('today-headline')).toBeNull();
    // Should still render today-screen container
    expect(screen.getByTestId('today-screen')).toBeTruthy();
  });

  it('renders why section when present', () => {
    const payloadWithWhy: TodayPayload = {
      ...mockPayload,
      whyThisHappens: {
        sections: [
          {
            id: 'test-section',
            title: 'Почему раздел',
            aspects: null,
            blocks: [
              { kind: 'paragraph', text: 'Объяснение 1' },
              { kind: 'paragraph', text: 'Объяснение 2' },
            ],
          },
        ],
      },
    };
    render(<TodayScreen payload={payloadWithWhy} />);
    expect(screen.getByText('Почему так у меня')).toBeTruthy();
    expect(screen.getByText('Почему раздел')).toBeTruthy();
    expect(screen.getByText('Объяснение 1')).toBeTruthy();
  });

  it('does not render why section when empty', () => {
    render(<TodayScreen payload={mockPayload} />);
    expect(screen.queryByText('Почему так у меня')).toBeNull();
  });
});
// END_BLOCK: TEST_TODAY_SCREEN
