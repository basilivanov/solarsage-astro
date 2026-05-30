// AI_HEADER
// module: M-WEB-LOADING-SPINNER
// wave: W-2.2
// purpose: Loading state component

export function LoadingSpinner() {
  return (
    <div className="loading-spinner" data-testid="loading-spinner">
      <div className="spinner" />
      <p>Загрузка...</p>
    </div>
  );
}
