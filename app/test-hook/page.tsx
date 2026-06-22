
// ############################################################################
// AI_HEADER: MODULE_TEST-HOOK_PAGE
// ROLE: Next.js page
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: UI page — component
// owns:
//   - app/test-hook/page.tsx
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
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
