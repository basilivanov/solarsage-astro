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
  dayChart: {
    source: "solarsage",
    houses: [
      { number: 1, cuspLongitude: 90 },
      { number: 2, cuspLongitude: 120 },
      { number: 3, cuspLongitude: 150 },
      { number: 4, cuspLongitude: 180 },
      { number: 5, cuspLongitude: 210 },
      { number: 6, cuspLongitude: 240 },
      { number: 7, cuspLongitude: 270 },
      { number: 8, cuspLongitude: 300 },
      { number: 9, cuspLongitude: 330 },
      { number: 10, cuspLongitude: 0 },
      { number: 11, cuspLongitude: 30 },
      { number: 12, cuspLongitude: 60 },
    ],
    transitPlanets: [
      { name: "Sun", longitude: 105, sign: "Cancer", house: 1, retrograde: false, speed: 0.98, motion: "direct", interpretation: "Солнце в первом доме усиливает личность." },
      { name: "Moon", longitude: 195, sign: "Libra", house: 4, retrograde: false, speed: 13.2, motion: "direct", interpretation: "Луна в четвертом доме обращает внимание на дом." },
      { name: "Mercury", longitude: 125, sign: "Leo", house: 2, retrograde: false, speed: 1.2, motion: "direct", interpretation: "Меркурий во втором доме активирует финансовые мысли." },
      { name: "Venus", longitude: 85, sign: "Gemini", house: 12, retrograde: false, speed: 1.15, motion: "direct", interpretation: "Венера в двенадцатом доме приносит уединение." },
      { name: "Mars", longitude: 5, sign: "Aries", house: 10, retrograde: false, speed: 0.72, motion: "direct", interpretation: "Марс в десятом доме дает энергию для карьеры." },
      { name: "Jupiter", longitude: 65, sign: "Gemini", house: 11, retrograde: false, speed: 0.18, motion: "direct", interpretation: "Юпитер в одиннадцатом доме приносит удачу с друзьями." },
      { name: "Saturn", longitude: 185, sign: "Libra", house: 4, retrograde: true, speed: -0.05, motion: "retrograde", interpretation: "Сатурн в четвертом доме напоминает об ответственности." },
    ],
    aspects: [
      { planet: "Sun", targetPlanet: "Mars", aspectType: "square", orb: 2.1, strength: 0.8 },
      { planet: "Moon", targetPlanet: "Mercury", aspectType: "sextile", orb: 1.5, strength: 0.9 },
      { planet: "Mars", targetPlanet: "Saturn", aspectType: "opposition", orb: 3.5, strength: 0.75 },
    ],
  },
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
    { key: "crisis_transformation_control", score: 4.0, rank: 7 },
    { key: "inner_background_unconscious", score: 5.5, rank: 8 },
  ],
  concreteAdvice: {
    rows: [
      { key: "work", label: "Работа", iconName: "💼", rank: 1, verdict: "neutral", confidence: "low", text: "Ровный рабочий день — без сюрпризов, без прорывов", evidence: [] },
      { key: "money", label: "Деньги", iconName: "💰", rank: 2, verdict: "good", confidence: "high", text: "Хороший день для вложений в себя и дом", evidence: [] },
      { key: "documents", label: "Документы", iconName: "📝", rank: 3, verdict: "good", confidence: "high", text: "Хорошее время для договоров — читай спокойно, подписывай", evidence: [] },
      { key: "relationships", label: "Отношения", iconName: "💖", rank: 4, verdict: "good", confidence: "high", text: "Свидания пройдут отлично — будь открыт и смел", evidence: [] },
      { key: "sport", label: "Спорт", iconName: "🏃", rank: 5, verdict: "avoid", confidence: "high", text: "Снизь нагрузку — риск травм выше, работай на технику", evidence: [] },
      { key: "communication", label: "Общение", iconName: "💬", rank: 6, verdict: "good", confidence: "high", text: "Переговоры пройдут гладко — проси что хочешь", evidence: [] },
      { key: "health", label: "Здоровье", iconName: "🌿", rank: 7, verdict: "neutral", confidence: "low", text: "Стабильно — поддерживай режим, ничего особого", evidence: [] },
      { key: "decisions", label: "Решения", iconName: "🎯", rank: 8, verdict: "neutral", confidence: "low", text: "Обычная ясность — решения принимаются ровно", evidence: [] },
      { key: "travel", label: "Поездки", iconName: "✈️", rank: 9, verdict: "good", confidence: "medium", text: "Дорога будет лёгкой — хороший день для отправления", evidence: [] },
      { key: "creativity", label: "Творчество", iconName: "🎨", rank: 10, verdict: "good", confidence: "medium", text: "Вдохновение бьёт ключом — садись за работу", evidence: [] },
      { key: "study", label: "Учёба", iconName: "📚", rank: 11, verdict: "good", confidence: "medium", text: "Память цепкая — учи сложное, оно задержится", evidence: [] },
      { key: "shopping", label: "Покупки", iconName: "🛍️", rank: 12, verdict: "good", confidence: "medium", text: "Вкус работает — выберешь правильное, не пожалеешь", evidence: [] },
    ],
    counts: { good: 8, caution: 0, avoid: 1, neutral: 3 }
  },
  daySummary: {
    statusLabel: "Поддерживающий день",
    statusLine: "день на твоей стороне — действуй",
    facts: [
      { kind: "top_planet", iconName: "Moon", title: "Влияние Луны", summary: "тема дня — Луна: фокус на чувствах" },
      { kind: "lunar_phase", iconName: "moon", title: "Убывающая Луна 76%", summary: "подводи итоги" },
      { kind: "top_flag", iconName: "flag", title: "Марс трин Юпитер", summary: "особое влияние дня" }
    ]
  },
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
