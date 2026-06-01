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
