'use client';

import { useTelegramAuth } from '@/hooks/use-telegram-auth';

export default function TestHookPage() {
  const { isLoading, isAuthenticated, error } = useTelegramAuth();

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h1>Test useTelegramAuth Hook</h1>
      <pre style={{ background: '#f0f0f0', padding: '10px' }}>
        {JSON.stringify({ isLoading, isAuthenticated, error }, null, 2)}
      </pre>
      {isLoading && <p>⏳ Loading...</p>}
      {isAuthenticated && <p>✅ Authenticated!</p>}
      {error && <p style={{ color: 'red' }}>❌ Error: {error}</p>}
    </div>
  );
}
