// AI_HEADER
// module: M-WEB-DAY-PAGE
// wave: W-2.2
// purpose: Today screen - main day view

'use client';

import { useParams } from 'next/navigation';
import { useDay } from '@/lib/grace/hooks/useDay';
import { TodayScreen } from '@/components/grace/TodayScreen';
import { LoadingSpinner } from '@/components/grace/LoadingSpinner';
import { ErrorBoundary } from '@/components/grace/ErrorBoundary';

export default function DayPage() {
  const params = useParams();
  const date = params.date as string;

  const { data, loading, error } = useDay(date);

  if (loading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return (
      <ErrorBoundary
        error={error}
        title="Не удалось загрузить день"
        message={error.message}
      />
    );
  }

  if (!data) {
    return null;
  }

  return <TodayScreen payload={data} />;
}
