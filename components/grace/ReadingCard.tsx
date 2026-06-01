// AI_HEADER
// module: M-WEB-READING-CARD
// wave: W-2.5
// purpose: Reading card component

import React from 'react';
import { ReadingEntry } from '@/lib/contracts/readings';
import { cn } from '@/lib/utils';

interface ReadingCardProps {
  entry: ReadingEntry;
  onClick: () => void;
}

const STATUS_STYLES: Record<string, string> = {
  supportive: 'border-green-500/20 bg-green-500/5 text-green-600',
  tense: 'border-red-500/20 bg-red-500/5 text-red-600',
  calm: 'border-border/70 bg-muted/30 text-muted-foreground',
};

const STATUS_LABELS: Record<string, string> = {
  supportive: 'Благоприятный',
  tense: 'Напряжённый',
  calm: 'Спокойный',
};

export function ReadingCard({ entry, onClick }: ReadingCardProps) {
  const statusKey = entry.dayStatus || 'calm';

  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex w-full flex-col items-start gap-3 rounded-2xl border border-border/70 bg-card p-5 text-left transition active:scale-[0.99]"
      data-testid="reading-card"
    >
      <div className="flex w-full items-center justify-between gap-3">
        <span className="text-[12px] text-muted-foreground/80">{entry.date}</span>
        <span
          className={cn(
            "rounded-full border px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.08em]",
            STATUS_STYLES[statusKey] || STATUS_STYLES.calm,
          )}
        >
          {STATUS_LABELS[statusKey] || STATUS_LABELS.calm}
        </span>
      </div>

      <h3 className="font-serif text-[20px] leading-tight tracking-tight text-foreground">
        {entry.headline}
      </h3>
      <p className="text-pretty text-[13.5px] leading-relaxed text-muted-foreground line-clamp-2">
        {entry.preview}
      </p>
    </button>
  );
}
