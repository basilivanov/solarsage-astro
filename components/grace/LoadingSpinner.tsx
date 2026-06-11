
// ############################################################################
// AI_HEADER: MODULE_GRACE_LOADINGSPINNER
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/grace/LoadingSpinner.tsx
// owns:
//   - components/grace/LoadingSpinner.tsx
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

// AI_HEADER
// module: M-WEB-LOADING-SPINNER
// wave: W-2.2
// purpose: Loading state component

export function LoadingSpinner() {
  return (
    <div
      className="flex flex-col items-center justify-center gap-4 py-16"
      data-testid="loading-spinner"
      role="status"
      aria-label="Загрузка"
    >
      <div className="h-8 w-8 animate-spin rounded-full border-[3px] border-muted-foreground/20 border-t-primary" />
      <p className="text-[13px] text-muted-foreground">Загрузка...</p>
    </div>
  );
}
