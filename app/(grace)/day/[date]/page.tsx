'use client';

import { useCallback, useEffect, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { TodayScreen } from '@/components/today/today-screen';
import { LoadingSpinner } from '@/components/grace/LoadingSpinner';
import { ErrorBoundary } from '@/components/grace/ErrorBoundary';
import { useDay } from '@/lib/grace/hooks/useDay';
import { fromDateParam, toDateParam } from '@/lib/date';
import { TODAY } from '@/lib/today';
import type { TodayPayload, TodayNote, TodayWhySection } from '@/lib/contracts/today';
import type { AccessInfo } from '@/lib/access';

function adaptPayload(api: any, selectedDate: Date): {
  payload: TodayPayload;
  access: AccessInfo;
} {
  const notes: TodayNote[] = api.notes
    ? [{
        id: 'daily-note',
        iconName: 'compass',
        title: 'Заметка дня',
        description: api.notes,
        hint: {
          meaning: api.notes,
          whyImportant: '',
          howForMe: '',
        },
      }]
    : [];

  const reading = api.reading || { paragraphs: [] };

  const why: TodayWhySection[] = (api.whyThisHappens?.sections || []).map(
    (s: any) => ({
      id: s.title || String(Math.random()),
      iconName: 'telescope',
      title: s.title || '',
      paragraphs: s.blocks
        ?.filter((b: any) => b.kind === 'paragraph')
        ?.map((b: any) => b.text) || [],
      bullets: s.blocks
        ?.filter((b: any) => b.kind === 'bullets')
        ?.flatMap((b: any) => b.items) || [],
    })
  );

  const keyInsight = api.whyThisHappens?.sections?.[0]?.title || '';

  const access: AccessInfo = {
    state: api.access?.state || 'preview',
    daysLeft: api.access?.referralDaysLeft ?? null,
    referralDaysLeft: api.access?.referralDaysLeft ?? null,
    subscriptionActive: api.access?.subscriptionActive ?? null,
    accessUntil: api.access?.accessUntil ?? null,
  };

  return {
    payload: {
      date: api.date || selectedDate.toISOString().split('T')[0],
      notes,
      reading,
      why,
      keyInsight,
    },
    access,
  };
}

export default function DayPage() {
  const params = useParams();
  const dateStr = params.date as string;
  const router = useRouter();

  const selectedDate = useMemo(() => fromDateParam(dateStr) ?? TODAY, [dateStr]);

  useEffect(() => {
    if (!fromDateParam(dateStr)) {
      router.replace(`/day/${toDateParam(TODAY)}`);
    }
  }, [dateStr, router]);

  const { data, loading, error } = useDay(dateStr);

  const onDateChange = useCallback(
    (d: Date) => router.push(`/day/${toDateParam(d)}`),
    [router]
  );

  if (loading) return <LoadingSpinner />;

  if (error) {
    return (
      <ErrorBoundary
        error={error}
        title="Не удалось загрузить день"
        message={error.message}
      />
    );
  }

  if (!data) return null;

  const { payload, access } = adaptPayload(data, selectedDate);

  return (
    <TodayScreen
      selectedDate={selectedDate}
      access={access}
      payload={payload}
      onDateChange={onDateChange}
    />
  );
}
