
// ############################################################################
// AI_HEADER: MODULE_LIB_ADAPT_PAYLOAD_TEST
// ROLE: Unit tests for adapt-payload.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Unit tests for adapt-payload.test.ts — __tests__/lib/adapt-payload.test.ts
// owns:
//   - __tests__/lib/adapt-payload.test.ts
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

// AI_HEADER
// module: M-TEST-ADAPT-PAYLOAD
// purpose: Unit tests for adaptPayload — verifies API data → component props mapping

import { describe, it, expect } from 'vitest';

// Inline adaptPayload for testing (copied from page.tsx)
import type { AccessInfo } from '../../lib/access';

function adaptPayload(api: any, selectedDate: Date): { payload: any; access: AccessInfo } {
  const notes: any[] = api.notes
    ? [{ id: 'daily-note', iconName: 'compass', title: 'Заметка дня', description: api.notes, hint: { meaning: api.notes, whyImportant: '', howForMe: '' } }]
    : [{ id: 'no-data', iconName: 'compass', title: 'Данные временно недоступны', description: 'Пожалуйста, попробуйте позже.', hint: { meaning: 'Данные временно недоступны', whyImportant: '', howForMe: '' } }];

  const reading = api.reading || { paragraphs: [] };

  const why: any[] = (api.whyThisHappens?.sections || []).map(
    (s: any) => ({
      id: s.title || String(Math.random()),
      iconName: 'telescope',
      title: s.title || '',
      paragraphs: s.blocks?.filter((b: any) => b.kind === 'paragraph')?.map((b: any) => b.text) || [],
      bullets: s.blocks?.filter((b: any) => b.kind === 'bullets')?.flatMap((b: any) => b.items) || [],
    })
  );

  const keyInsight = api.whyThisHappens?.sections?.[0]?.title || '';

  const access: AccessInfo = {
    state: (api.access?.state === 'full' || api.access?.state === 'trial') 
      ? 'trial' 
      : api.access?.state === 'locked' 
        ? 'none' 
        : (api.access?.state === 'preview' ? 'expired' : 'none') as AccessInfo['state'],
    hasAccess: api.access?.state === 'full' || api.access?.state === 'trial',
    accessStart: null,
    accessEnd: null,
    daysLeft: api.access?.referralDaysLeft ?? api.access?.daysLeft ?? 0,
  };

  return {
    payload: { date: api.date || selectedDate.toISOString().split('T')[0], notes, reading, why, keyInsight },
    access,
  };
}

import { isDayAccessible } from '../../lib/access';
import { TODAY } from '../../lib/today';

describe('adaptPayload', () => {
  const baseApi = {
    date: '2026-06-01',
    headline: 'Test day',
    notes: null,
    reading: { paragraphs: ['Test paragraph'] },
    whyThisHappens: { sections: [] },
  };

  it('full access → hasAccess=true, isDayAccessible=true', () => {
    const api = { ...baseApi, access: { state: 'full', referralDaysLeft: 13 } };
    const { access } = adaptPayload(api, TODAY);

    expect(access.hasAccess).toBe(true);
    expect(access.state).toBe('trial');
    expect(isDayAccessible(TODAY, access)).toBe(true);
  });

  it('trial access → hasAccess=true', () => {
    const api = { ...baseApi, access: { state: 'trial', referralDaysLeft: 5 } };
    const { access } = adaptPayload(api, TODAY);

    expect(access.hasAccess).toBe(true);
    expect(access.daysLeft).toBe(5);
    expect(isDayAccessible(TODAY, access)).toBe(true);
  });

  it('preview → hasAccess=false, isDayAccessible=false', () => {
    const api = { ...baseApi, access: { state: 'preview' } };
    const { access } = adaptPayload(api, TODAY);

    expect(access.hasAccess).toBe(false);
    expect(isDayAccessible(TODAY, access)).toBe(false);
  });

  it('locked → hasAccess=false', () => {
    const api = { ...baseApi, access: { state: 'locked' } };
    const { access } = adaptPayload(api, TODAY);

    expect(access.hasAccess).toBe(false);
    expect(access.state).toBe('none');
  });

  it('missing access → hasAccess=false', () => {
    const api = { ...baseApi };
    const { access } = adaptPayload(api, TODAY);

    expect(access.hasAccess).toBe(false);
  });

  it('preserves referralDaysLeft', () => {
    const api = { ...baseApi, access: { state: 'full', referralDaysLeft: 7 } };
    const { access } = adaptPayload(api, TODAY);

    expect(access.daysLeft).toBe(7);
  });

  it('falls back to daysLeft', () => {
    const api = { ...baseApi, access: { state: 'full', daysLeft: 3 } };
    const { access } = adaptPayload(api, TODAY);

    expect(access.daysLeft).toBe(3);
  });

  // ── Placeholder tests — blocks must be visible even when data is missing ──

  it('null notes → placeholder card (not empty)', () => {
    const api = { ...baseApi, notes: null };
    const { payload } = adaptPayload(api, TODAY);

    expect(payload.notes.length).toBeGreaterThan(0);
    expect(payload.notes[0].title).toBe('Данные временно недоступны');
    expect(payload.notes[0].description).toBe('Пожалуйста, попробуйте позже.');
  });

  it('real notes → real card (not placeholder)', () => {
    const api = { ...baseApi, notes: 'Сегодня отличный день для общения' };
    const { payload } = adaptPayload(api, TODAY);

    expect(payload.notes[0].title).toBe('Заметка дня');
    expect(payload.notes[0].title).not.toBe('Данные временно недоступны');
  });

  it('empty why sections → empty array (WhyExpanded hides itself)', () => {
    const api = { ...baseApi, whyThisHappens: { sections: [] } };
    const { payload } = adaptPayload(api, TODAY);

    expect(payload.why.length).toBe(0);
  });
});
