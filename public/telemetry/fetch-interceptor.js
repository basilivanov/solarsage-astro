// Fetch interceptor for telemetry
// Logs all fetch errors to console for debugging
(function() {
  const originalFetch = window.fetch;

  window.fetch = async function(...args) {
    const [url, options] = args;
    const startTime = Date.now();

    try {
      const response = await originalFetch(...args);
      const duration = Date.now() - startTime;

      // Log failed requests
      if (!response.ok) {
        const errorData = {
          type: 'fetch_error',
          url: typeof url === 'string' ? url : url.toString(),
          status: response.status,
          statusText: response.statusText,
          duration,
          timestamp: new Date().toISOString(),
        };

        console.error('[Telemetry] Fetch failed:', errorData);

        // Try to get response body for more context
        try {
          const text = await response.clone().text();
          console.error('[Telemetry] Response body:', text.substring(0, 500));
        } catch (e) {
          // Ignore if can't read body
        }
      }

      return response;
    } catch (error) {
      const duration = Date.now() - startTime;

      // Log network errors
      const errorData = {
        type: 'fetch_exception',
        url: typeof url === 'string' ? url : url.toString(),
        error: error instanceof Error ? error.message : String(error),
        duration,
        timestamp: new Date().toISOString(),
      };

      console.error('[Telemetry] Fetch exception:', errorData);

      throw error;
    }
  };

  console.log('[Telemetry] Fetch interceptor initialized');
})();
