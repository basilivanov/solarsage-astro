
// ############################################################################
// AI_HEADER: MODULE_ADAPTERS_TODAY_PAYLOAD — transforms TodayPayload to AdaptedTodayPayload.
// ROLE: Pure adapter function to map API types into UI presentation structures.
// DEPENDENCIES: lib/contracts/today, lib/access, packages/contracts
// ############################################################################

// START_MODULE_CONTRACT: M-ADAPTERS-TODAY-PAYLOAD
// purpose: Transform API TodayPayload into UI-ready AdaptedTodayPayload.
// owns:
//   - lib/adapters/today-payload.ts
// inputs: TodayPayload (API), selectedDate.
// outputs: { payload: AdaptedTodayPayload, access: AccessInfo }.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - No `any` types.
//   - Preserves headline, dayStatus, topFlags from API.
//   - Maps access.state correctly.
//   - Full access without commercial or referral metadata maps to accessible subscription UI.
//   - Does not validate TodayV2Block schema in production (pure pass-through).
//   - adapter always copies exact payloadVersion/frontendPayloadVersion/contentVersion from api.meta.
//   - No normalization/defaulting and no full-meta spread in wireIdentity construction.
//   - v2 block preserves object identity (same reference).
// failure_policy: none.
// END_MODULE_CONTRACT: M-ADAPTERS-TODAY-PAYLOAD

// START_MODULE_MAP: M-ADAPTERS-TODAY-PAYLOAD
// public_entrypoints:
//   - adaptTodayPayload
// semantic_blocks:
//   - TODAY_PAYLOAD_ADAPTER: pure adaptation logic.
// END_MODULE_MAP: M-ADAPTERS-TODAY-PAYLOAD

import type { TodayPayload, TodayV2Block } from '@/packages/contracts';
import {
  type AdaptedTodayPayload,
  type AdaptedTopFlag,
  type TodayReading,
  type TodayNote,
  type TodayWhySection,
  type TodayWireIdentity,
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
  const isTrial = apiAccess?.reason === 'active_referral_days'
    || apiAccess?.referralDaysLeft != null;

  let uiState: AccessInfo['state'];
  if (s === 'full' && isSubscription) {
    uiState = 'subscription';
  } else if (s === 'full' && isTrial) {
    uiState = 'trial';
  } else if (s === 'full') {
    uiState = 'subscription';
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

function buildV2Block(apiV2: TodayPayload['v2']): TodayV2Block | null {
  return apiV2 ?? null;
}

// START_BLOCK: TODAY_PAYLOAD_ADAPTER
// START_FUNCTION_CONTRACT: F-M-ADAPTERS-TODAY-PAYLOAD.adaptTodayPayload
// purpose: Map TodayPayload to AdaptedTodayPayload structures.
// inputs: api - raw API TodayPayload; selectedDate - Date.
// returns: Adapted payload and access info.
// side_effects: none.
// emitted_logs: none.
// error_behavior: none.
// END_FUNCTION_CONTRACT: F-M-ADAPTERS-TODAY-PAYLOAD.adaptTodayPayload
export function adaptTodayPayload(
  api: TodayPayload,
  selectedDate: Date,
): { payload: AdaptedTodayPayload; access: AccessInfo } {
  const why = buildWhySections(api.whyThisHappens?.sections || []);
  const keyInsight = why[0]?.title || FALLBACK_KEY_INSIGHT;

  const wireIdentity: TodayWireIdentity = {
    payloadVersion: api.meta.payloadVersion,
    frontendPayloadVersion: api.meta.frontendPayloadVersion,
    contentVersion: api.meta.contentVersion,
  }

  return {
    payload: {
      wireIdentity,
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
      relativeStatus: api.relativeStatus ?? null,
      concreteAdvice: api.concreteAdvice,
      daySummary: api.daySummary,
      v2: buildV2Block(api.v2),
    },
    access: buildAccess(api.access),
  };
}
// END_BLOCK: TODAY_PAYLOAD_ADAPTER
