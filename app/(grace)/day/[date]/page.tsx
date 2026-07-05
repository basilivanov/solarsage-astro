
// ############################################################################
// AI_HEADER: MODULE_[DATE]_PAGE
// ROLE: Next.js page
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for page.tsx behavior
// owns:
//   - app/(grace)/day/[date]/page.tsx
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: React state management
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { TodayScreen } from '@/components/today/today-screen';
import { CosmicLoader } from '@/components/shared/cosmic-loader';
import { ErrorBoundary } from '@/components/grace/ErrorBoundary';
import { useDay } from '@/lib/grace/hooks/useDay';
import { useOnboarded } from '@/hooks/use-onboarded';
import { fromDateParam, toDateParam } from '@/lib/date';
import { TODAY } from '@/lib/today';
import { adaptTodayPayload } from '@/lib/adapters/today-payload';

export default function DayPage() {
  const params = useParams();
  const dateStr = params.date as string;
  const router = useRouter();
  const { setOnboarded } = useOnboarded();

  const selectedDate = useMemo(() => fromDateParam(dateStr) ?? TODAY, [dateStr]);

  useEffect(() => {
    if (!fromDateParam(dateStr)) {
      router.replace(`/day/${toDateParam(TODAY)}`);
    }
  }, [dateStr, router]);

  const { data, loading, error } = useDay(dateStr);

  // Cosmic loader state: show while loading, dismiss with delay when done
  const [showLoader, setShowLoader] = useState(true);
  const dismissTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const ready = !!data && !loading;

  useEffect(() => {
    if (ready) {
      dismissTimer.current = setTimeout(() => setShowLoader(false), 600);
    } else {
      setShowLoader(true);
    }
    return () => {
      if (dismissTimer.current) clearTimeout(dismissTimer.current);
    };
  }, [ready, dateStr]);

  // Sync localStorage when day loads successfully (backend says user is onboarded)
  useEffect(() => {
    if (data) {
      setOnboarded(true);
    }
  }, [data, setOnboarded]);

  const onDateChange = useCallback(
    (d: Date) => router.push(`/day/${toDateParam(d)}`),
    [router]
  );

  if (error) {
    return (
      <ErrorBoundary
        error={error}
        title="Не удалось загрузить день"
        message={error.message}
      />
    );
  }

  if (showLoader || !data) return <CosmicLoader done={ready} />;

  if (!data) return null;

  const { payload, access } = adaptTodayPayload(data, selectedDate);

  return (
    <TodayScreen
      selectedDate={selectedDate}
      access={access}
      payload={payload}
      onDateChange={onDateChange}
      importantToday={data.importantToday || []}
    />
  );
}
