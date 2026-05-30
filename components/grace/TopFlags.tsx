// AI_HEADER
// module: M-WEB-TOP-FLAGS
// wave: W-2.2
// purpose: Top flags display

import type { TopFlag } from '@/packages/contracts/_generated';

interface TopFlagsProps {
  flags: TopFlag[];
}

export function TopFlags({ flags }: TopFlagsProps) {
  if (flags.length === 0) return null;

  return (
    <section className="top-flags" data-testid="top-flags">
      {flags.map((flag, idx) => (
        <div key={idx} className="flag-card">
          <div className="flag-icon" data-icon={flag.iconName} />
          <div className="flag-content">
            <h3 className="flag-title">{flag.title}</h3>
            <p className="flag-summary">{flag.summary}</p>
            {flag.hint && <p className="flag-hint">{flag.hint}</p>}
          </div>
        </div>
      ))}
    </section>
  );
}
