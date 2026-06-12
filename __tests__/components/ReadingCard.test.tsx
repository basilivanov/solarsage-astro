
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_READINGCARD_TEST
// ROLE: Unit tests for ReadingCard.test.tsx
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for ReadingCardtsx behavior
// owns:
//   - __tests__/components/ReadingCard.test.tsx
// inputs: Mocks, fixtures
// outputs: Assertion results
// dependencies: local modules
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
// AI_HEADER
// module: M-TEST-READING-CARD
// wave: W-2.5
// purpose: ReadingCard component tests

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ReadingCard } from '@/components/grace/ReadingCard';

describe('ReadingCard', () => {
  const mockEntry = {
    date: '2026-05-29',
    headline: 'День возможностей',
    dayStatus: 'supportive' as const,
    preview: 'Сегодня благоприятный день.',
  };

  it('renders entry data', () => {
    const onClick = vi.fn();
    render(<ReadingCard entry={mockEntry} onClick={onClick} />);

    expect(screen.getByText('2026-05-29')).toBeTruthy();
    expect(screen.getByText('День возможностей')).toBeTruthy();
    expect(screen.getByText('Сегодня благоприятный день.')).toBeTruthy();
  });

  it('calls onClick when clicked', () => {
    const onClick = vi.fn();
    render(<ReadingCard entry={mockEntry} onClick={onClick} />);

    const card = screen.getByTestId('reading-card');
    fireEvent.click(card);

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('shows correct status badge', () => {
    const onClick = vi.fn();
    render(<ReadingCard entry={mockEntry} onClick={onClick} />);

    expect(screen.getByText('Благоприятный')).toBeTruthy();
  });

  it('shows "Напряжённый" badge for tense dayStatus', () => {
    const onClick = vi.fn();
    const tenseEntry = { ...mockEntry, dayStatus: 'tense' as const };
    render(<ReadingCard entry={tenseEntry} onClick={onClick} />);

    expect(screen.getByText('Напряжённый')).toBeTruthy();
  });

  it('shows "Спокойный" badge for calm dayStatus', () => {
    const onClick = vi.fn();
    const calmEntry = { ...mockEntry, dayStatus: 'calm' as any };
    render(<ReadingCard entry={calmEntry} onClick={onClick} />);

    expect(screen.getByText('Спокойный')).toBeTruthy();
  });

  it('defaults to calm when dayStatus is undefined', () => {
    const onClick = vi.fn();
    const noStatusEntry = { ...mockEntry, dayStatus: undefined as any };
    render(<ReadingCard entry={noStatusEntry} onClick={onClick} />);

    expect(screen.getByText('Спокойный')).toBeTruthy();
  });

  it('falls back to calm style for unknown dayStatus', () => {
    const onClick = vi.fn();
    const unknownEntry = { ...mockEntry, dayStatus: 'mysterious' as any };
    render(<ReadingCard entry={unknownEntry} onClick={onClick} />);

    // Unknown dayStatus falls back to calm label
    expect(screen.getByText('Спокойный')).toBeTruthy();
  });

  it('has data-testid="reading-card"', () => {
    const onClick = vi.fn();
    render(<ReadingCard entry={mockEntry} onClick={onClick} />);

    expect(screen.getByTestId('reading-card')).toBeTruthy();
  });

  it('renders without crashing when preview is empty', () => {
    const onClick = vi.fn();
    const emptyPreviewEntry = { ...mockEntry, preview: '' };
    render(<ReadingCard entry={emptyPreviewEntry} onClick={onClick} />);

    expect(screen.getByTestId('reading-card')).toBeTruthy();
    expect(screen.getByText('День возможностей')).toBeTruthy();
  });

  it('renders date text from entry', () => {
    const onClick = vi.fn();
    const entry = { ...mockEntry, date: '2026-12-25' };
    render(<ReadingCard entry={entry} onClick={onClick} />);

    expect(screen.getByText('2026-12-25')).toBeTruthy();
  });

  it('renders headline text from entry', () => {
    const onClick = vi.fn();
    const entry = { ...mockEntry, headline: 'Уникальный заголовок' };
    render(<ReadingCard entry={entry} onClick={onClick} />);

    expect(screen.getByText('Уникальный заголовок')).toBeTruthy();
  });
});
