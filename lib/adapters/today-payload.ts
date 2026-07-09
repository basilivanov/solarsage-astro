
// ############################################################################
// AI_HEADER: MODULE_ADAPTERS_TODAY_PAYLOAD
// ROLE: Pure adapter — API TodayPayload → UI AdaptedTodayPayload
// DEPENDENCIES: lib/contracts/today, lib/access, @/packages/contracts
// GRACE_ANCHORS: [TODAY_PAYLOAD_ADAPTER]
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Transform API TodayPayload into UI-ready AdaptedTodayPayload
// owns:
//   - lib/adapters/today-payload.ts
// inputs: TodayPayload (API), selectedDate
// outputs: { payload: AdaptedTodayPayload, access: AccessInfo }
// side_effects: n/a (pure)
// invariants:
//   - No `any` types
//   - Preserves headline, dayStatus, topFlags from API
//   - Maps access.state: full→trial, preview→expired, locked→none
//   - null notes → placeholder card
// END_MODULE_CONTRACT

import type { TodayPayload } from '@/packages/contracts';
import type {
  AdaptedTodayPayload,
  AdaptedTopFlag,
  TodayReading,
  TodayNote,
  TodayWhySection,
} from '@/lib/contracts/today';
import type { AccessInfo } from '@/lib/access';

type ApiWhySection = TodayPayload['whyThisHappens']['sections'][number];
type ApiWhyBlock = ApiWhySection['blocks'][number];

const FALLBACK_UNAVAILABLE_TITLE = 'Данные временно недоступны';
const FALLBACK_UNAVAILABLE_DESCRIPTION = 'Пожалуйста, попробуйте позже.';
const FALLBACK_READING: TodayReading = {
  paragraphs: [FALLBACK_UNAVAILABLE_DESCRIPTION],
};
const FALLBACK_KEY_INSIGHT = FALLBACK_UNAVAILABLE_TITLE;

function nonEmptyOr(value: string | null | undefined, fallback: string): string {
  const trimmed = value?.trim();
  return trimmed && trimmed.length > 0 ? trimmed : fallback;
}

function isParagraphBlock(block: ApiWhyBlock): block is Extract<ApiWhyBlock, { kind: 'paragraph' }> {
  return block.kind === 'paragraph';
}

function isBulletsBlock(block: ApiWhyBlock): block is Extract<ApiWhyBlock, { kind: 'bullets' }> {
  return block.kind === 'bullets';
}

function isNonEmptyString(value: string): boolean {
  return value.trim().length > 0;
}

function buildNotes(apiNotes: string | null | undefined): TodayNote[] {
  if (apiNotes) {
    return [{
      id: 'daily-note',
      iconName: 'compass',
      title: 'Заметка дня',
      description: apiNotes,
      hint: {
        meaning: apiNotes,
        whyImportant: 'Это главный краткий акцент дня из персонального разбора.',
        howForMe: 'Используй это как ориентир для решений и темпа дня.',
      },
    }];
  }
  return [{
    id: 'no-data',
    iconName: 'compass',
    title: FALLBACK_UNAVAILABLE_TITLE,
    description: FALLBACK_UNAVAILABLE_DESCRIPTION,
    hint: {
      meaning: FALLBACK_UNAVAILABLE_TITLE,
      whyImportant: 'Без данных невозможно показать персональный акцент дня.',
      howForMe: 'Попробуй обновить экран позже.',
    },
  }];
}

function buildWhySections(
  sections: readonly ApiWhySection[] | undefined,
): TodayWhySection[] {
  return (sections ?? []).map((s, index) => {
    const blocks = s.blocks || [];
    const paragraphs = blocks
      .filter(isParagraphBlock)
      .map((b) => b.text)
      .filter(isNonEmptyString);
    const bullets = blocks
      .filter(isBulletsBlock)
      .flatMap((b) => b.items)
      .filter(isNonEmptyString);

    return {
      id: nonEmptyOr(s.id, `why-${index + 1}`),
      iconName: nonEmptyOr(s.iconName, 'telescope'),
      title: nonEmptyOr(s.title, `Раздел ${index + 1}`),
      paragraphs: paragraphs.length > 0 || bullets.length > 0
        ? paragraphs
        : [FALLBACK_UNAVAILABLE_DESCRIPTION],
      bullets,
    };
  });
}

function buildTopFlags(apiTopFlags: TodayPayload['topFlags']): AdaptedTopFlag[] {
  return (apiTopFlags || []).map((f) => ({
    iconName: nonEmptyOr(f.iconName, 'compass'),
    title: nonEmptyOr(f.title, 'Сигнал дня'),
    summary: nonEmptyOr(f.summary, 'Подробности временно недоступны.'),
  }));
}

function buildReading(apiReading: TodayPayload['reading'] | undefined | null): TodayReading {
  const paragraphs = apiReading?.paragraphs.filter(isNonEmptyString) ?? [];
  return paragraphs.length > 0 ? { paragraphs } : FALLBACK_READING;
}

function buildAccess(apiAccess: TodayPayload['access'] | undefined | null): AccessInfo {
  const s = apiAccess?.state;
  const isSubscription = apiAccess?.subscriptionActive === true
    || apiAccess?.reason === 'active_subscription';

  let uiState: AccessInfo['state'];
  if (s === 'full' && isSubscription) {
    uiState = 'subscription';
  } else if (s === 'full') {
    uiState = 'trial';
  } else if (s === 'locked') {
    uiState = 'none';
  } else if (s === 'preview') {
    uiState = 'expired';
  } else {
    uiState = 'none';
  }

  return {
    state: uiState,
    hasAccess: s === 'full',
    accessStart: null,
    accessEnd: null,
    daysLeft: Math.max(0, apiAccess?.referralDaysLeft ?? 0),
  };
}

function buildV2Block(apiV2: TodayPayload['v2']): AdaptedTodayPayload['v2'] | null {
  if (!apiV2) return null;

  const topActivatedTargets = (apiV2.activationSummary?.topActivatedTargets || []).map((t) => ({
    targetType: t.targetType as "planet" | "house" | "lot" | "angle" | "sphere",
    targetKey: t.targetKey || "",
    label: t.label || "",
    familyCount: t.familyCount ?? 0,
    techniques: t.techniques || [],
    spheres: t.spheres || [],
    activationIds: t.activationIds || [],
  }));

  const activationEvidence = (apiV2.activationEvidence || []).map((e) => ({
    id: e.id || "",
    technique: e.technique || "",
    techniqueFamily: e.techniqueFamily || "",
    targetType: e.targetType as "planet" | "house" | "lot" | "angle" | "sphere",
    targetKey: e.targetKey || "",
    kind: e.kind || "",
    active: e.active ?? true,
    sourcePlanet: e.sourcePlanet ?? null,
    sourceFrame: e.sourceFrame ?? null,
    targetPlanet: e.targetPlanet ?? null,
    targetFrame: e.targetFrame ?? null,
    aspect: e.aspect ?? null,
    orb: e.orb ?? null,
    applying: e.applying ?? null,
    exactAt: e.exactAt ?? null,
    phase: (e.phase || "background") as "applying" | "exact" | "separating" | "background" | "period",
    house: e.house ?? null,
    lot: e.lot ?? null,
    angle: e.angle ?? null,
    strength: e.strength ?? 0,
    polarity: (e.polarity || "neutral") as "supportive" | "tense" | "mixed" | "neutral",
    weightHint: e.weightHint ?? null,
    evidence: e.evidence || "",
    debug: (e.debug as Record<string, any>) || {},
  }));

  const scoreBreakdown: Record<string, any> = {};
  if (apiV2.scoreBreakdown) {
    for (const [key, score] of Object.entries(apiV2.scoreBreakdown)) {
      if (score) {
        scoreBreakdown[key] = {
          key: score.key || key,
          title: score.title || "",
          baseScore: score.baseScore ?? 0,
          activationScore: score.activationScore ?? 0,
          convergenceBonus: score.convergenceBonus ?? 0,
          rawScore: score.rawScore ?? 0,
          finalScore: score.finalScore ?? 0,
          normalizedScore: score.normalizedScore ?? null,
          dominanceCapped: score.dominanceCapped ?? false,
          contributions: (score.contributions || []).map((c) => ({
            sphere: c.sphere || "",
            source: c.source as "base_signal" | "activation" | "convergence" | "cap",
            sourceId: c.sourceId || "",
            amount: c.amount ?? 0,
            before: c.before ?? null,
            after: c.after ?? null,
            evidence: c.evidence || "",
          })),
        };
      }
    }
  }

  const whyToday = (apiV2.whyToday || []).map((w) => ({
    id: w.id || "",
    title: w.title || "",
    body: w.body || "",
    activationIds: w.activationIds || [],
    techniques: w.techniques || [],
  }));

  const audit = {
    traceId: apiV2.audit?.traceId ?? null,
    available: apiV2.audit?.available ?? false,
    payloadVersion: apiV2.audit?.payloadVersion || "today.v2",
    calculationVersion: apiV2.audit?.calculationVersion || "1",
    scoringVersion: apiV2.audit?.scoringVersion || "2",
    activationLayerVersion: apiV2.audit?.activationLayerVersion ?? null,
    canonVersions: apiV2.audit?.canonVersions || {},
    v1V2Diff: apiV2.audit?.v1V2Diff ?? null,
  };

  return {
    activationSummary: {
      headline: apiV2.activationSummary?.headline || "",
      topActivatedTargets,
    },
    activationEvidence,
    scoreBreakdown,
    whyToday,
    audit,
  };
}

/**
 * Transform a raw API TodayPayload into the UI-ready AdaptedTodayPayload
 * and computed AccessInfo. All astrological calculation is done server-side;
 * this adapter only reshapes data for the UI components.
 */
export function adaptTodayPayload(
  api: TodayPayload,
  selectedDate: Date,
): { payload: AdaptedTodayPayload; access: AccessInfo } {
  const why = buildWhySections(api.whyThisHappens?.sections || []);
  const keyInsight = why[0]?.title || FALLBACK_KEY_INSIGHT;

  return {
    payload: {
      date: api.date || selectedDate.toISOString().split('T')[0],
      headline: api.headline || '',
      dayStatus: api.dayStatus,
      topFlags: buildTopFlags(api.topFlags),
      notes: buildNotes(api.notes),
      reading: buildReading(api.reading),
      why,
      keyInsight,
      dayChart: api.dayChart ?? null,
      planetInfluences: api.planetInfluences ?? [],
      sphereScores: api.sphereScores ?? [],
      concreteAdvice: api.concreteAdvice,
      daySummary: api.daySummary,
      v2: buildV2Block(api.v2),
    },
    access: buildAccess(api.access),
  };
}
