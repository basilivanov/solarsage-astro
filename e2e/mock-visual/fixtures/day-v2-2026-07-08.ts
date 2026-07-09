import type { components } from "../../../packages/contracts/_generated"

export const dayPayloadV2: components["schemas"]["TodayPayload"] = {
  meta: {
    schemaVersion: "today/v1",
    contractVersion: 3,
    calculationVersion: 1,
    normalizationVersion: 1,
    scoringVersion: 1,
    promptVersion: 2,
    contentVersion: 3,
    generatedAt: "2026-07-08T06:00:00Z",
    cached: false,
    payloadVersion: "today.v2",
    frontendPayloadVersion: 2,
  },
  date: "2026-07-08",
  title: "Среда, 8 июля",
  subtitle: null,
  headline: "День для важных решений и переговоров",
  access: {
    state: "full",
    reason: "active_referral_days",
    referralDaysLeft: 7,
    subscriptionActive: false,
    accessUntil: null,
  },
  dayStatus: "supportive",
  dayQuality: {
    supportScore: 7.5,
    frictionScore: 2.3,
    intensityScore: 3.1,
  },
  topFlags: [
    {
      iconName: "moon",
      title: "Луна в Раке",
      summary: "Эмоциональная глубина и желание уюта",
    },
  ],
  reading: {
    paragraphs: [
      "Сегодня день возможностей. Марс в гармоничном аспекте с Юпитером даёт прилив уверенности.",
    ],
  },
  notes: "Хороший день для творчества и общения с близкими.",
  whyThisHappens: {
    sections: [],
  },
  concreteAdvice: {
    rows: [
      {
        key: "work",
        label: "Работа",
        iconName: "briefcase",
        rank: 1,
        verdict: "good",
        confidence: "high",
        text: "Рекомендация по работе",
        evidence: [
          {
            kind: "activation",
            title: "Transit Mars trine natal Saturn",
            orb: 1.25,
            strength: 0.85,
            technique: "transit_to_natal",
            techniqueFamily: "transit",
            sourceFrame: "transit",
            targetFrame: "natal",
          },
        ],
      },
    ],
    counts: {
      good: 1,
      caution: 0,
      avoid: 0,
      neutral: 0,
    },
  },
  daySummary: {
    statusLabel: "Поддерживающий день",
    statusLine: "фокус на общении и решениях",
    facts: [],
  },
  v2: {
    activationSummary: {
      headline: "Сегодня сходятся 3 независимые техники на теме общения и решений",
      topActivatedTargets: [
        {
          targetType: "planet",
          targetKey: "MERCURY",
          label: "Меркурий",
          familyCount: 3,
          techniques: ["annual_profection", "transit_to_natal", "secondary_progression"],
          spheres: ["communication"],
          activationIds: ["act-1"],
        },
      ],
    },
    activationEvidence: [
      {
        id: "act-1",
        technique: "transit_to_natal",
        techniqueFamily: "transit",
        targetType: "planet",
        targetKey: "MERCURY",
        kind: "aspect",
        active: true,
        strength: 0.8,
        evidence: "Transit Moon opposition natal Mercury, orb 1.05°",
        phase: "background",
        polarity: "neutral",
        debug: {},
      },
    ],
    scoreBreakdown: {},
    whyToday: [
      {
        id: "why-profection-house-3",
        title: "Профекция года активирует 3 дом",
        body: "Эта долгосрочная техника смещает фокус года на сферу коммуникаций, документов и ближнего круга.",
        activationIds: ["act-1"],
        techniques: ["annual_profection"],
      },
    ],
    audit: {
      available: true,
      payloadVersion: "today.v2",
      calculationVersion: "ss-calc-1.1.0",
      scoringVersion: "ss-scoring-2.0",
      activationLayerVersion: "al-1.0",
      canonVersions: {},
      v1V2Diff: {},
    },
  },
  importantToday: [],
  microcopy: [],
  weekStrip: [],
}
