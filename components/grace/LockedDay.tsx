// AI_HEADER
// module: M-WEB-LOCKED-DAY
// wave: W-2.7, W-ACCESS.3
// purpose: Locked day with soft lock + CTAs

'use client';

import { useRouter } from 'next/navigation';

export function LockedDay() {
  const router = useRouter();

  return (
    <div className="locked-day" data-testid="locked-day">
      <div className="locked-overlay">
        <div className="locked-content">
          <div className="locked-icon">🔒</div>
          <h2 className="locked-title">Этот день заблокирован</h2>
          <p className="locked-description">
            Подпишитесь или пригласите друга, чтобы получить доступ к полному прогнозу
          </p>

          <div className="locked-ctas">
            <button
              onClick={() => router.push('/paywall')}
              className="cta-primary"
              data-testid="cta-subscribe"
            >
              Оформить подписку
            </button>

            <button
              onClick={() => router.push('/referral')}
              className="cta-secondary"
              data-testid="cta-invite"
            >
              Пригласить друга (+14 дней)
            </button>
          </div>

          <p className="locked-hint">
            Приглашение даёт 14 дней доступа вам и вашему другу
          </p>
        </div>
      </div>
    </div>
  );
}
