
// ############################################################################
// AI_HEADER: MODULE_NATAL-PREVIEW_ERROR_CARD
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/readings/natal-preview/error-card.tsx
// owns:
//   - components/readings/natal-preview/error-card.tsx
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

"use client"

type Props = {
  message: string
  onRetry?: () => void
}

export function ErrorCard({ message, onRetry }: Props) {
  return (
    <div className="rounded-2xl border border-destructive/20 bg-card p-5">
      <h1 className="font-serif text-[24px] leading-tight text-foreground">Не удалось построить натальную карту</h1>
      <p className="mt-3 text-[13px] leading-relaxed text-muted-foreground">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-4 inline-flex rounded-xl bg-primary px-4 py-2 text-[13px] font-medium text-primary-foreground"
      >
        Повторить
      </button>
    </div>
  )
}
