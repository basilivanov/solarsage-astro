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
