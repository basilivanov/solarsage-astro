
// ############################################################################
// AI_HEADER: GRACE_READING — narrative day-reading paragraph renderer.
// ROLE: Stateless renderer for narrative day-reading paragraphs.
// ############################################################################

// START_MODULE_CONTRACT: M-GRACE-COMPONENT-READING
// purpose: Render non-empty reading paragraphs with first/last paragraph styling.
// owns:
//   - components/grace/Reading.tsx
// inputs: paragraphs — ordered array of strings.
// outputs: null for an empty array, otherwise reading section and paragraph list.
// dependencies: React JSX only.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - Empty paragraphs produce no DOM.
//   - aria-label="Разбор дня" and data-testid="reading" remain stable.
//   - Input order and first/last styling decisions remain unchanged.
// failure_policy: Does not validate paragraph content; render errors propagate.
// END_MODULE_CONTRACT: M-GRACE-COMPONENT-READING

// START_MODULE_MAP: M-GRACE-COMPONENT-READING
// public_entrypoints:
//   - Reading
// semantic_blocks:
//   - EMPTY_GUARD: suppress empty reading.
//   - SECTION_HEADING: visible separator and title.
//   - PARAGRAPH_LIST: ordered styled narrative.
// owned_tests:
//   - none direct.
// END_MODULE_MAP: M-GRACE-COMPONENT-READING

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
