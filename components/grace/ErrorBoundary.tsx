// AI_HEADER
// module: M-WEB-ERROR-BOUNDARY
// wave: W-2.2
// purpose: Error state component

interface ErrorBoundaryProps {
  error: Error;
  title?: string;
  message?: string;
}

export function ErrorBoundary({ error, title, message }: ErrorBoundaryProps) {
  const displayTitle = title || 'Ошибка';
  const displayMessage = message || error.message || 'Произошла неизвестная ошибка';

  return (
    <div className="error-boundary" data-testid="error-boundary">
      <h2>{displayTitle}</h2>
      <p data-testid="error-message">{displayMessage}</p>
    </div>
  );
}
