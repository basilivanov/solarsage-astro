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
});
