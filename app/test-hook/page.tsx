
// ############################################################################
// AI_HEADER: MODULE_TEST-HOOK_PAGE
// ROLE: Next.js page
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Next.js page — app/test-hook/page.tsx
// owns:
//   - app/test-hook/page.tsx
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
