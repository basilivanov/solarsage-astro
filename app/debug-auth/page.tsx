
// ############################################################################
// AI_HEADER: MODULE_DEBUG-AUTH_PAGE
// ROLE: Next.js page
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for page.tsx behavior
// owns:
//   - app/debug-auth/page.tsx
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: Network calls to API; React state management
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
'use client';

import { useEffect, useState } from 'react';

export default function DebugAuthPage() {
  const [logs, setLogs] = useState<string[]>([]);
  const [result, setResult] = useState<any>(null);

  const addLog = (msg: string) => {
    console.log(msg);
    setLogs(prev => [...prev, `${new Date().toISOString().split('T')[1].slice(0, -1)} ${msg}`]);
  };

  useEffect(() => {
    addLog('[1] Component mounted');
    addLog('[2] typeof window: ' + typeof window);
    addLog('[3] NODE_ENV: ' + process.env.NODE_ENV);

    const testAuth = async () => {
      addLog('[4] Starting fetch...');

      try {
        const response = await fetch('/api/auth/dev', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include'
        });

        addLog(`[5] Response status: ${response.status}`);

        const data = await response.json();
        addLog(`[6] Response data: ${JSON.stringify(data)}`);
        setResult(data);
      } catch (err) {
        addLog(`[ERROR] ${err instanceof Error ? err.message : String(err)}`);
      }
    };

    testAuth();
  }, []);

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h1>Auth Debug Page</h1>
      <h2>Logs:</h2>
      <pre style={{ background: '#f0f0f0', padding: '10px', fontSize: '12px' }}>
        {logs.join('\n')}
      </pre>
      {result && (
        <>
          <h2>Result:</h2>
          <pre style={{ background: '#e0ffe0', padding: '10px' }}>
            {JSON.stringify(result, null, 2)}
          </pre>
        </>
      )}
    </div>
  );
}
