
// ############################################################################
// AI_HEADER: MODULE_TODAY_DAY_READING
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TODAY-CALENDAR
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/today/day-reading.tsx
// owns:
//   - components/today/day-reading.tsx
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

type Props = {
  /**
   * Абзацы разбора дня в порядке вывода.
   * Первый получает dropcap. В preview-режиме показываются первые 2.
   */
  paragraphs: string[]
  /** Если true — показываем только первые абзацы с мягким fade-out. */
  preview?: boolean
}

const PREVIEW_COUNT = 2

export function DayReading({ paragraphs, preview = false }: Props) {
  if (!paragraphs || paragraphs.length === 0) return null

  const visible = preview ? paragraphs.slice(0, PREVIEW_COUNT) : paragraphs
  const last = visible.length - 1

  return (
    <section className="px-6" aria-label="Разбор дня">
      <div className="mb-4 flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Разбор дня
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <div className="relative">
        <div className="space-y-4 font-serif text-[19px] leading-[1.55] text-foreground">
          {visible.map((p, i) => (
            <p
              key={i}
              className={
                // Первый абзац — dropcap'ом
                i === 0
                  ? "first-letter:float-left first-letter:mr-2 first-letter:mt-1 first-letter:font-serif first-letter:text-[46px] first-letter:leading-[0.9] first-letter:text-primary"
                  : // В preview притушаем второй абзац — визуальный «обрыв»
                  preview && i === last
                  ? "text-foreground/80"
                  : // В полной версии — последний абзац-ключ слегка муть
                  !preview && i === last
                  ? "text-muted-foreground"
                  : ""
              }
            >
              {p}
            </p>
          ))}
        </div>

        {preview ? (
          <div
            aria-hidden
            className="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-b from-transparent to-background"
          />
        ) : null}
      </div>
    </section>
  )
}
