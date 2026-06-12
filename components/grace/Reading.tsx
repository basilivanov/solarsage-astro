
// ############################################################################
// AI_HEADER: MODULE_GRACE_READING
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Module: Reading.tsx
// owns:
//   - components/grace/Reading.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
// AI_HEADER
// module: M-WEB-READING
// wave: W-2.2
// purpose: Reading paragraphs display

interface ReadingProps {
  paragraphs: string[];
}

export function Reading({ paragraphs }: ReadingProps) {
  if (paragraphs.length === 0) return null;

  return (
    <section className="px-6" aria-label="Разбор дня" data-testid="reading">
      <div className="mb-4 flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Разбор дня
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>
      <div className="space-y-4 font-serif text-[19px] leading-[1.55] text-foreground">
        {paragraphs.map((p, idx) => {
          const isFirst = idx === 0;
          const isLast = idx === paragraphs.length - 1;
          return (
            <p
              key={idx}
              className={
                isFirst
                  ? "first-letter:float-left first-letter:mr-2 first-letter:mt-1 first-letter:font-serif first-letter:text-[46px] first-letter:leading-[0.9] first-letter:text-primary"
                  : isLast
                    ? "text-muted-foreground"
                    : ""
              }
            >
              {p}
            </p>
          );
        })}
      </div>
    </section>
  );
}
