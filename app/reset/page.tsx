
// ############################################################################
// AI_HEADER: MODULE_RESET_PAGE
// ROLE: Next.js page
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Next.js page — app/reset/page.tsx
// owns:
//   - app/reset/page.tsx
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

import { useEffect, useState } from 'react';

export default function ResetPage() {
  const [status, setStatus] = useState<'clearing' | 'done' | 'error'>('clearing');
  const [msg, setMsg] = useState('Очистка...');

  useEffect(() => {
    async function reset() {
      try {
        // 1. Clear backend profile FIRST (while session cookie may still exist)
        try {
          const resp = await fetch('/api/profile', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ birth: { birthday: null, birthTime: null, birthCity: null, birthLat: null, birthLon: null, birthTz: null } }),
          });
          setMsg(resp.ok ? 'Профиль, кэш и сессия очищены' : 'Кэш и сессия очищены');
        } catch {
          setMsg('Кэш и сессия очищены');
        }

        // 2. Clear browser
        localStorage.clear();
        sessionStorage.clear();
        document.cookie.split(';').forEach((c) => {
          document.cookie = c.replace(/^ +/, '').replace(/=.*/, '=;expires=' + new Date().toUTCString() + ';path=/');
        });

        setStatus('done');
        // Don't redirect — let user decide when to proceed
      } catch {
        setStatus('error');
        setMsg('Ошибка очистки');
      }
    }
    reset();
  }, []);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-4 px-5 text-center">
        {status === 'clearing' && (
          <>
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            <p className="text-sm text-muted-foreground">{msg}</p>
          </>
        )}
        {status === 'done' && (
          <>
            <div className="h-8 w-8 rounded-full bg-accent" />
            <p className="font-serif text-[22px] text-foreground">Готово</p>
            <p className="font-sans text-[15px] text-muted-foreground">{msg}</p>
            <p className="mt-4 font-sans text-[13px] text-muted-foreground/60">
              Теперь открой @vi_astro_bot — загрузится онбординг
            </p>
          </>
        )}
        {status === 'error' && (
          <>
            <p className="font-serif text-[22px] text-foreground">Ошибка</p>
            <p className="font-sans text-[15px] text-muted-foreground">{msg}</p>
          </>
        )}
      </div>
    </div>
  );
}
