
// ############################################################################
// AI_HEADER: MODULE_NATAL-PREVIEW_LOADING_SKELETON
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/readings/natal-preview/loading-skeleton.tsx
// owns:
//   - components/readings/natal-preview/loading-skeleton.tsx
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

export function LoadingSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="rounded-3xl border border-border/70 bg-card p-5">
        <div className="h-3 w-24 rounded bg-muted" />
        <div className="mt-3 h-8 w-3/4 rounded bg-muted" />
        <div className="mt-3 h-4 w-2/3 rounded bg-muted" />
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {[1, 2, 3].map((item) => (
          <div key={item} className="rounded-2xl border border-border/70 bg-card p-4">
            <div className="h-3 w-16 rounded bg-muted" />
            <div className="mt-2 h-6 w-20 rounded bg-muted" />
            <div className="mt-2 h-4 w-full rounded bg-muted" />
          </div>
        ))}
      </div>
      <div className="rounded-2xl border border-border/70 bg-card p-4">
        <div className="h-6 w-full rounded bg-muted" />
        <div className="mt-3 h-6 w-5/6 rounded bg-muted" />
      </div>
      <div className="rounded-2xl border border-border/70 bg-card p-4">
        <div className="h-3 w-24 rounded bg-muted" />
        <div className="mt-3 h-8 w-1/2 rounded bg-muted" />
      </div>
    </div>
  )
}
