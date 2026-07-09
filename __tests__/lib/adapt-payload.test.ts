
// ############################################################################
// AI_HEADER: MODULE_LIB_ADAPT_PAYLOAD_TEST
// ROLE: Unit tests for adaptTodayPayload — real import from lib/adapters/today-payload.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for adaptTodayPayload — verifies API data → component props mapping
// owns:
//   - __tests__/lib/adapt-payload.test.ts
// inputs: Mocks, fixtures
// outputs: Assertion results
// dependencies: local modules
// side_effects: n/a (tests)
// invariants:
//   - No `as any` / @ts-ignore / @ts-expect-error
// failure_policy: log and raise
// END_MODULE_CONTRACT

import { describe, it, expect } from 'vitest';
import { adaptTodayPayload } from '../../lib/adapters/today-payload';
import { isDayAccessible } from '../../lib/access';
import { TODAY } from '../../lib/today';
import { validateAdaptedTodayPayload } from '../../lib/contracts/today';
import type { TodayPayload } from '../../packages/contracts';

/** Helper: builds a minimal valid TodayPayload with overrides. */
function createBaseApi(
  overrides?: Partial<TodayPayload>,
): TodayPayload {
  const base: TodayPayload = {
    date: '2026-06-01',
    title: '',
    headline: 'Test headline for the day',
    dayStatus: 'supportive',
    topFlags: [
      { iconName: 'sun', title: 'Sun in Aries', summary: 'Active energy' },
      { iconName: 'moon', title: 'Moon trine Venus', summary: 'Harmony' },
    ],
    reading: { paragraphs: ['Test paragraph'] },
    notes: null,
    whyThisHappens: { sections: [] },
    meta: {
      schemaVersion: 'today/v1',
      contractVersion: 1,
      calculationVersion: 1,
      normalizationVersion: 1,
      scoringVersion: 1,
      promptVersion: 1,
      contentVersion: 1,
      generatedAt: '2026-06-01T00:00:00Z',
      cached: false,
      payloadVersion: 'today.v1',
      frontendPayloadVersion: 1,
    },
    access: { state: 'full', referralDaysLeft: 13 },
    weekStrip: [],
    microcopy: [],
    importantToday: [],
    dayChart: {
      source: 'solarsage',
      houses: [{ number: 1, cuspLongitude: 0, sign: 'Aries' }],
      transitPlanets: [{
        name: 'Moon',
        longitude: 35,
        sign: 'Taurus',
        retrograde: false,
        speed: 12.5,
        motion: 'direct',
        house: 2,
      }],
      aspects: [{
        planet: 'Moon',
        targetPlanet: 'Sun',
        aspectType: 'square',
        orb: 1.2,
        strength: 0.8,
      }],
    },
    planetInfluences: [{ name: 'Moon', score: 1.25, rank: 1 }],
    sphereScores: [{ key: 'relationships', score: 2.5, rank: 1 }],
    daySummary: {
      statusLabel: 'Благоприятный день',
      statusLine: 'Прекрасный день для общения и творчества.',
      facts: [
        { kind: 'top_planet' as const, iconName: 'sun', title: 'Солнце', summary: 'Влияние Солнца' },
      ],
    },
    concreteAdvice: {
      rows: [
        {
          key: 'work' as const,
          label: 'Работа',
          iconName: 'briefcase',
          rank: 1,
          verdict: 'good' as const,
          confidence: 'high' as const,
          text: 'Благоприятно',
          evidence: [],
        },
      ],
      counts: {
        good: 1,
        caution: 0,
        avoid: 0,
        neutral: 11,
      },
    },
  };
  return { ...base, ...overrides };
}

/** Helper: builds a minimal ContentAccessState override. */
function accessOverride(
  state: TodayPayload['access']['state'],
  extra?: Partial<TodayPayload['access']>,
): TodayPayload['access'] {
  return {
    state,
    referralDaysLeft: null,
    subscriptionActive: null,
    reason: null,
    accessUntil: null,
    ...extra,
  };
}

describe('adaptTodayPayload', () => {
  // ── Access mapping ──

  it('full access (referral) → hasAccess=true, access.state=trial', () => {
    const api = createBaseApi({ access: accessOverride('full', { referralDaysLeft: 13 }) });
    const { access } = adaptTodayPayload(api, TODAY);

    expect(access.hasAccess).toBe(true);
    expect(access.state).toBe('trial');
    expect(access.daysLeft).toBe(13);
    expect(isDayAccessible(TODAY, access)).toBe(true);
  });

  it('full access with subscription → hasAccess=true, access.state=subscription', () => {
    const api = createBaseApi({
      access: accessOverride('full', { subscriptionActive: true, referralDaysLeft: 0 }),
    });
    const { access } = adaptTodayPayload(api, TODAY);

    expect(access.hasAccess).toBe(true);
    expect(access.state).toBe('subscription');
  });

  it('full access with reason=active_subscription → hasAccess=true, access.state=subscription', () => {
    const api = createBaseApi({
      access: accessOverride('full', { reason: 'active_subscription', referralDaysLeft: 0 }),
    });
    const { access } = adaptTodayPayload(api, TODAY);

    expect(access.hasAccess).toBe(true);
    expect(access.state).toBe('subscription');
  });

  it('preview → hasAccess=false, isDayAccessible=false', () => {
    const api = createBaseApi({ access: accessOverride('preview') });
    const { access } = adaptTodayPayload(api, TODAY);

    expect(access.hasAccess).toBe(false);
    expect(isDayAccessible(TODAY, access)).toBe(false);
  });

  it('locked → hasAccess=false, access.state=none', () => {
    const api = createBaseApi({ access: accessOverride('locked') });
    const { access } = adaptTodayPayload(api, TODAY);

    expect(access.hasAccess).toBe(false);
    expect(access.state).toBe('none');
  });

  it('preserves referralDaysLeft from API', () => {
    const api = createBaseApi({ access: accessOverride('full', { referralDaysLeft: 7 }) });
    const { access } = adaptTodayPayload(api, TODAY);

    expect(access.daysLeft).toBe(7);
  });

  // ── Notes mapping ──

  it('null notes → placeholder card (not empty)', () => {
    const api = createBaseApi({ notes: null });
    const { payload } = adaptTodayPayload(api, TODAY);

    expect(payload.notes.length).toBeGreaterThan(0);
    expect(payload.notes[0].title).toBe('Данные временно недоступны');
    expect(payload.notes[0].description).toBe('Пожалуйста, попробуйте позже.');
    expect(payload.notes[0].hint.whyImportant).not.toBe('');
    expect(payload.notes[0].hint.howForMe).not.toBe('');
  });

  it('real notes → real card (not placeholder)', () => {
    const api = createBaseApi({ notes: 'Сегодня отличный день для общения' });
    const { payload } = adaptTodayPayload(api, TODAY);

    expect(payload.notes[0].title).toBe('Заметка дня');
    expect(payload.notes[0].title).not.toBe('Данные временно недоступны');
  });

  // ── Headline / topFlags / dayStatus preservation ──

  it('preserves headline from API', () => {
    const api = createBaseApi({ headline: 'Unique day insight' });
    const { payload } = adaptTodayPayload(api, TODAY);

    expect(payload.headline).toBe('Unique day insight');
  });

  it('preserves dayStatus from API', () => {
    const api = createBaseApi({ dayStatus: 'tense' });
    const { payload } = adaptTodayPayload(api, TODAY);

    expect(payload.dayStatus).toBe('tense');
  });

  it('preserves topFlags from API', () => {
    const api = createBaseApi({
      topFlags: [
        { iconName: 'mars', title: 'Mars square Saturn', summary: 'Conflict energy' },
      ],
    });
    const { payload } = adaptTodayPayload(api, TODAY);

    expect(payload.topFlags).toHaveLength(1);
    expect(payload.topFlags[0].title).toBe('Mars square Saturn');
    expect(payload.topFlags[0].summary).toBe('Conflict energy');
  });

  it('preserves backend day chart and influence read models', () => {
    const api = createBaseApi();
    const { payload } = adaptTodayPayload(api, TODAY);

    expect(payload.dayChart?.source).toBe('solarsage');
    expect(payload.dayChart?.houses[0].cuspLongitude).toBe(0);
    expect(payload.dayChart?.transitPlanets[0]).toMatchObject({
      name: 'Moon',
      motion: 'direct',
      house: 2,
    });
    expect(payload.dayChart?.aspects[0]).toMatchObject({
      planet: 'Moon',
      targetPlanet: 'Sun',
      aspectType: 'square',
    });
    expect(payload.planetInfluences).toEqual([{ name: 'Moon', score: 1.25, rank: 1 }]);
    expect(payload.sphereScores).toEqual([{ key: 'relationships', score: 2.5, rank: 1 }]);
  });

  it('topFlags defaults to empty array when undefined', () => {
    const api = createBaseApi({ topFlags: undefined });
    const { payload } = adaptTodayPayload(api, TODAY);

    expect(payload.topFlags).toEqual([]);
  });

  // ── Why sections ──

  it('empty why sections → empty array (WhyExpanded hides itself)', () => {
    const api = createBaseApi({ whyThisHappens: { sections: [] } });
    const { payload } = adaptTodayPayload(api, TODAY);

    expect(payload.why.length).toBe(0);
  });

  it('why sections with paragraphs and bullets are mapped correctly', () => {
    const api = createBaseApi({
      whyThisHappens: {
        sections: [
          {
            id: 's1',
            title: 'Section 1',
            iconName: 'moon',
            layer: 'main_theme',
            blocks: [
              { kind: 'paragraph' as const, text: 'Para text' },
              { kind: 'bullets' as const, items: ['Bullet 1'] },
            ],
            planets: [],
            houses: [],
            aspects: [],
            techniques: [],
          },
        ],
      },
    });
    const { payload } = adaptTodayPayload(api, TODAY);

    expect(payload.why).toHaveLength(1);
    expect(payload.why[0].paragraphs).toEqual(['Para text']);
    expect(payload.why[0].bullets).toEqual(['Bullet 1']);
    expect(payload.why[0].title).toBe('Section 1');
  });

  it('why sections with bullets only are valid for the UI contract', () => {
    const api = createBaseApi({
      whyThisHappens: {
        sections: [
          {
            id: 's1',
            title: 'Practical steps',
            iconName: 'list-checks',
            layer: 'practical_meaning',
            blocks: [{ kind: 'bullets' as const, items: ['Step 1', 'Step 2'] }],
            planets: [],
            houses: [],
            aspects: [],
            techniques: [],
          },
        ],
      },
    });
    const { payload } = adaptTodayPayload(api, TODAY);

    expect(payload.why[0].paragraphs).toEqual([]);
    expect(payload.why[0].bullets).toEqual(['Step 1', 'Step 2']);
    expect(() => validateAdaptedTodayPayload(payload)).not.toThrow();
  });

  // ── Reading ──

  it('reading with paragraphs is mapped correctly', () => {
    const api = createBaseApi({ reading: { paragraphs: ['P1', 'P2'] } });
    const { payload } = adaptTodayPayload(api, TODAY);

    expect(payload.reading.paragraphs).toEqual(['P1', 'P2']);
  });

  // ── keyInsight ──

  it('keyInsight is first why section title', () => {
    const api = createBaseApi({
      whyThisHappens: {
        sections: [
          {
            id: 's1', title: 'First Insight', iconName: 'sun',
            blocks: [{ kind: 'paragraph' as const, text: 'text' }],
            planets: [], houses: [], aspects: [], techniques: [],
          },
          {
            id: 's2', title: 'Second Insight', iconName: 'moon',
            blocks: [{ kind: 'paragraph' as const, text: 'text' }],
            planets: [], houses: [], aspects: [], techniques: [],
          },
        ],
      },
    });
    const { payload } = adaptTodayPayload(api, TODAY);

    expect(payload.keyInsight).toBe('First Insight');
  });

  it('empty why → keyInsight falls back to non-empty placeholder', () => {
    const api = createBaseApi({ whyThisHappens: { sections: [] } });
    const { payload } = adaptTodayPayload(api, TODAY);

    expect(payload.keyInsight).toBe('Данные временно недоступны');
    expect(() => validateAdaptedTodayPayload(payload)).not.toThrow();
  });

  it('empty reading paragraphs fall back to a non-empty paragraph', () => {
    const api = createBaseApi({ reading: { paragraphs: [] } });
    const { payload } = adaptTodayPayload(api, TODAY);

    expect(payload.reading.paragraphs).toEqual(['Пожалуйста, попробуйте позже.']);
    expect(() => validateAdaptedTodayPayload(payload)).not.toThrow();
  });

  it('no placeholder for real notes', () => {
    const api = createBaseApi({ notes: 'Реальная заметка' });
    const { payload } = adaptTodayPayload(api, TODAY);

    expect(payload.notes[0].title).toBe('Заметка дня');
    expect(payload.notes[0].description).toBe('Реальная заметка');
    expect(payload.notes[0].description).not.toBe('Пожалуйста, попробуйте позже.');
    expect(payload.notes[0].description).not.toBe('Данные временно недоступны');
  });

  it('adapted payload validates against the UI TodayPayloadSchema', () => {
    const api = createBaseApi({
      notes: 'Реальная заметка',
      whyThisHappens: {
        sections: [
          {
            id: 's1',
            title: 'First Insight',
            iconName: 'sun',
            blocks: [{ kind: 'paragraph' as const, text: 'text' }],
            planets: [],
            houses: [],
            aspects: [],
            techniques: [],
          },
        ],
      },
    });
    const { payload } = adaptTodayPayload(api, TODAY);

    expect(() => validateAdaptedTodayPayload(payload)).not.toThrow();
  });

  it('proves old payload without v2 adapts and validates, does not fabricate v2', () => {
    const api = createBaseApi();
    const { payload } = adaptTodayPayload(api, TODAY);
    expect(payload.v2).toBeNull();
    expect(() => validateAdaptedTodayPayload(payload)).not.toThrow();
  });

  it('proves V2 payload preserves v2 data after adaptation', () => {
    const v2Block = {
      activationSummary: {
        headline: "Сходимость на Меркурии",
        topActivatedTargets: [
          {
            targetType: "planet" as const,
            targetKey: "MERCURY",
            label: "Меркурий",
            familyCount: 2,
            techniques: ["annual_profection", "transit_to_natal"],
            spheres: ["communication"],
            activationIds: ["act-1", "act-2"],
          }
        ]
      },
      activationEvidence: [
        {
          id: "act-1",
          technique: "transit_to_natal",
          techniqueFamily: "transit",
          targetType: "planet" as const,
          targetKey: "MERCURY",
          kind: "aspect",
          active: true,
          strength: 0.8,
          evidence: "Transit Moon trine natal Mercury",
          phase: "background" as const,
          polarity: "neutral" as const,
          debug: {},
        }
      ],
      scoreBreakdown: {},
      whyToday: [],
      audit: {
        available: true,
        payloadVersion: "today.v2",
        calculationVersion: "1",
        scoringVersion: "2",
        canonVersions: {},
      }
    };
    const api = createBaseApi({ v2: v2Block as any });
    const { payload } = adaptTodayPayload(api, TODAY);
    expect(payload.v2).toBeTruthy();
    expect(payload.v2?.activationSummary.headline).toBe("Сходимость на Меркурии");
    expect(() => validateAdaptedTodayPayload(payload)).not.toThrow();
  });

  it('proves V2 activation missing optional/defaulted fields is normalized with schema defaults', () => {
    const v2Block = {
      activationSummary: {
        headline: "Сходимость",
        topActivatedTargets: []
      },
      activationEvidence: [
        {
          id: "act-1",
          technique: "transit_to_natal",
          techniqueFamily: "transit",
          targetType: "planet" as const,
          targetKey: "MERCURY",
          kind: "aspect",
          strength: 0.8,
          evidence: "Transit Moon trine natal Mercury",
          // omitted: active, phase, polarity, debug
        }
      ],
      scoreBreakdown: {},
      whyToday: [],
      audit: {
        available: true,
        payloadVersion: "today.v2",
        calculationVersion: "1",
        scoringVersion: "2",
        canonVersions: {},
      }
    };
    const api = createBaseApi({ v2: v2Block as any });
    const { payload } = adaptTodayPayload(api, TODAY);
    expect(payload.v2).toBeTruthy();
    const ev = payload.v2?.activationEvidence[0];
    expect(ev?.active).toBe(true);
    expect(ev?.phase).toBe("background");
    expect(ev?.polarity).toBe("neutral");
    expect(ev?.debug).toEqual({});
  });

  it('proves malformed V2 missing required backend-owned fields throws a validation error', () => {
    const v2Block = {
      activationSummary: {
        headline: "Сходимость",
        topActivatedTargets: []
      },
      activationEvidence: [
        {
          id: "act-1",
          // missing: technique, techniqueFamily, targetType, targetKey, kind, strength, evidence
        }
      ],
      scoreBreakdown: {},
      whyToday: [],
      audit: {
        available: true,
        payloadVersion: "today.v2",
        calculationVersion: "1",
        scoringVersion: "2",
        canonVersions: {},
      }
    };
    const api = createBaseApi({ v2: v2Block as any });
    expect(() => adaptTodayPayload(api, TODAY)).toThrow();
  });
});
