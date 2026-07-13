
// ############################################################################
// AI_HEADER: APP_HOME_PAGE — root-route redirect to the canonical day path.
// ROLE: Client Next.js root page; redirects mounted users to /day/today while rendering a transient spinner.
// ############################################################################

// START_MODULE_CONTRACT: M-APP-HOME-PAGE
// purpose: Keep the root route as a compatibility entry that immediately replaces itself with /day/today.
// owns:
//   - app/(grace)/page.tsx
// inputs: component mount and Next router.
// outputs: transient loading spinner until navigation completes.
// dependencies: React useEffect; next/navigation; legacy frontend logger.
// side_effects: Emits one structured legacy log envelope and performs router.replace.
// emitted_logs: system.request.
// invariants:
//   - Root route always replaces, never pushes, /day/today.
//   - No data/auth API is called by this page.
// failure_policy: Router/render failures are delegated to Next/route boundary.
// END_MODULE_CONTRACT: M-APP-HOME-PAGE

// START_MODULE_MAP: M-APP-HOME-PAGE
// public_entrypoints:
//   - HomePage (default).
// semantic_blocks:
//   - ROOT_REDIRECT: log and replace the root route.
//   - TRANSIENT_RENDER: show spinner during navigation.
// owned_tests:
//   - none direct.
// END_MODULE_MAP: M-APP-HOME-PAGE
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { logger } from '@/lib/log';

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    logger.info('[HomePage] Redirecting to /day/today');
    router.replace('/day/today');
  }, [router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
    </div>
  );
}
