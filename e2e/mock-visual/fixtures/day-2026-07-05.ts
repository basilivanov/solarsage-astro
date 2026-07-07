// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_FIXTURE_DAY_2026_07_05
// ROLE: Contract-valid TodayPayload fixture for the mock visual e2e test.
//       Matches components["schemas"]["TodayPayload"] from _generated.ts.
//       Uses real-shaped technical sphere keys, not pre-localized labels.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-FIXTURE-DAY
// purpose: Provide a stable, contract-valid TodayPayload for Playwright route
//          interception in mock visual e2e tests. No product path imports this.
// owns:
//   - e2e/mock-visual/fixtures/day-2026-07-05.ts
// inputs: none (static fixture)
// outputs: Named exports: dayPayload, dayPayloadLocked, calendarPayload, dayStatusPayloads
// dependencies: none (pure data)
// side_effects: none
// invariants:
//   - Shape matches components["schemas"]["TodayPayload"] from _generated.ts
//   - dayStatus is a valid literal: "supportive" | "steady" | "tense"
//   - Sphere score keys are technical (e.g. "home_family", not "Дом и семья")
//   - No fabricated astrology — all text is deterministic
// failure_policy: n/a (static data)
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-FIXTURE-DAY

import type { components } from "../../../packages/contracts/_generated";

export const dayPayload: components["schemas"]["TodayPayload"] = {
  meta: {
    schemaVersion: "today/v1",
    contractVersion: 1,
    calculationVersion: 1,
    normalizationVersion: 1,
    scoringVersion: 1,
    promptVersion: 1,
    contentVersion: 1,
    generatedAt: "2026-07-05T06:00:00Z",
    cached: false,
  },
  date: "2026-07-05",
  title: "Воскресенье, 5 июля",
  subtitle: null,
  headline: "День для спокойного отдыха и лёгких прогулок",
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
      hint: {
        whyToday: "Луна в Раке усиливает интуицию и тягу к домашнему теплу",
        howItFeels: "Хочется побыть в знакомой обстановке",
      },
    },
    {
      iconName: "zap",
      title: "Марс трин Юпитер",
      summary: "Энергия для начинаний с оптимизмом",
    },
  ],
  reading: {
    paragraphs: [
      "Сегодня Луна в Раке создаёт мягкую, но глубокую эмоциональную атмосферу. Это хороший день для того, чтобы замедлиться и прислушаться к своим настоящим желаниям.",
      "Марс в гармоничном аспекте с Юпитером даёт прилив уверенности — но без излишней спешки. Используйте это время для планирования, а не для рывков.",
      "Вечером возможна лёгкая смена настроения — обратите внимание на свои границы и не берите лишних обязательств.",
    ],
  },
  notes: "Хороший день для творчества и общения с близкими. Луна в Раке делает интуицию особенно острой.",
  whyThisHappens: {
    sections: [
      {
        id: "lunar-influence",
        title: "Лунное влияние",
        iconName: "moon",
        layer: "main_theme",
        blocks: [
          {
            kind: "paragraph",
            text: "Луна в Раке — это управитель ночного светила в своей обители. Сегодня эмоциональный фон будет особенно глубоким, а интуиция — острой.",
          },
          {
            kind: "bullets",
            items: [
              "Повышенная чувствительность к окружению",
              "Желание уюта и безопасности",
              "Хорошее время для домашних дел",
            ],
          },
        ],
        planets: ["Moon"],
        houses: [4],
        aspects: null,
        techniques: null,
      },
      {
        id: "mars-jupiter",
        title: "Марс и Юпитер",
        iconName: "zap",
        layer: "amplifiers",
        blocks: [
          {
            kind: "paragraph",
            text: "Гармоничный аспект между Марсом и Юпитером добавляет энергии и оптимизма, но без типичной марсианской спешки.",
          },
        ],
        planets: ["Mars", "Jupiter"],
        houses: [1, 9],
        aspects: ["trine"],
        techniques: null,
      },
    ],
  },
  weekStrip: [
    { date: "2026-06-29", dayStatus: "steady", isToday: false },
    { date: "2026-06-30", dayStatus: "tense", isToday: false },
    { date: "2026-07-01", dayStatus: "supportive", isToday: false },
    { date: "2026-07-02", dayStatus: "steady", isToday: false },
    { date: "2026-07-03", dayStatus: "tense", isToday: false },
    { date: "2026-07-04", dayStatus: "steady", isToday: false },
    { date: "2026-07-05", dayStatus: "supportive", isToday: true },
  ],
  microcopy: [
    {
      id: "morning-greeting",
      textShort: "Доброе утро",
      textLong: "Доброе утро! Сегодня отличный день для спокойного старта.",
      tone: ["supportive"],
      scope: "morning",
    },
  ],
  yesterdayEcho: null,
  actions: null,
  dayChart: null,
  planetInfluences: [
    { name: "Луна", score: 8.2, rank: 1 },
    { name: "Марс", score: 6.5, rank: 2 },
    { name: "Юпитер", score: 5.8, rank: 3 },
  ],
  // Canon-shaped backend keys (Wave 4+) — not pre-localized labels
  sphereScores: [
    { key: "thinking_speech_learning", score: 8.5, rank: 1 },
    { key: "money_security_resources", score: 7.2, rank: 2 },
    { key: "home_family_roots", score: 6.0, rank: 3 },
    { key: "work_status_achievement", score: 4.5, rank: 4 },
    { key: "relationships_partnership", score: 3.0, rank: 5 },
    { key: "body_energy_health", score: 2.0, rank: 6 },
  ],
  activationEvidence: null,
  manifestationZones: null,
  periodContext: null,
  importantToday: [],
};

export const referralPayload = {
  inviteUrl: "https://t.me/vi_astro_bot?start=invite_mock",
  totalInvited: 0,
};

export const dayPayloadLocked: components["schemas"]["TodayPayload"] = {
  ...dayPayload,
  access: {
    state: "locked",
    reason: "outside_access_window",
    referralDaysLeft: null,
    subscriptionActive: false,
    accessUntil: null,
  },
};
