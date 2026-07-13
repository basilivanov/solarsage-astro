
// ############################################################################
// AI_HEADER: GRACE_LOADING_SPINNER — shared accessible loading indicator.
// ROLE: Stateless accessible loading indicator.
// ############################################################################

// START_MODULE_CONTRACT: M-GRACE-COMPONENT-LOADING-SPINNER
// purpose: Render the shared visual loading state.
// owns:
//   - components/grace/LoadingSpinner.tsx
// inputs: none.
// outputs: role=status loading-spinner with Russian loading text.
// dependencies: React JSX only.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - data-testid="loading-spinner", role=status and aria-label="Загрузка" remain stable.
// failure_policy: No local failure handling; render errors propagate.
// END_MODULE_CONTRACT: M-GRACE-COMPONENT-LOADING-SPINNER

// START_MODULE_MAP: M-GRACE-COMPONENT-LOADING-SPINNER
// public_entrypoints:
//   - LoadingSpinner
// semantic_blocks:
//   - LOADING_STATUS: spinner graphic and accessible status text.
// owned_tests:
//   - none direct.
// END_MODULE_MAP: M-GRACE-COMPONENT-LOADING-SPINNER

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
