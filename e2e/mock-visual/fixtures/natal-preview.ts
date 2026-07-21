// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_FIXTURE_NATAL
// ROLE: Contract-valid NatalPreviewRead fixture for mock visual e2e.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-FIXTURE-NATAL
// purpose: Provide contract-valid NatalPreviewRead for mock visual e2e tests.
// owns:
//   - e2e/mock-visual/fixtures/natal-preview.ts
// outputs: Named exports: natalPreviewPayload
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-FIXTURE-NATAL

import type { NatalPreviewRead } from "../../../lib/contracts/natal";

export const natalPreviewPayload: NatalPreviewRead = {
  meta: {
    name: "Ada",
    birthDate: "1985-12-10",
    birthTime: null,
    birthCity: "Lisbon, Portugal",
    houseSystem: null,
    ascSign: "Рак",
    ascDegree: null,
    gender: "female",
  },
  personalHook: "Твоя карта рождения говорит о сильной эмоциональной глубине и интуиции — Луна в Раке делает тебя особенно чувствительной к окружению.",
  highlights: [
    { id: "sun", title: "Солнце", value: "Стрелец", description: null },
    { id: "moon", title: "Луна", value: "Рак", description: null },
    { id: "asc", title: "Асцендент", value: "Рак", description: null },
  ],
  calculationStats: {
    planetsCount: 10,
    housesCount: 12,
    aspectsCount: 28,
    spheresCount: 6,
    specialPointsCount: 4,
    scoringFactorsCount: 60,
    dignityFactorsCount: 40,
    totalFactorsCount: 100,
    displayLabel: "Полный расчёт",
  },
  chart: {
    houses: [
      { number: 1, sign: "Рак", degree: 0, longitude: 120 },
      { number: 2, sign: "Лев", degree: 0, longitude: 150 },
      { number: 3, sign: "Дева", degree: 0, longitude: 180 },
      { number: 4, sign: "Весы", degree: 0, longitude: 210 },
      { number: 5, sign: "Скорпион", degree: 0, longitude: 240 },
      { number: 6, sign: "Стрелец", degree: 0, longitude: 270 },
      { number: 7, sign: "Козерог", degree: 0, longitude: 300 },
      { number: 8, sign: "Водолей", degree: 0, longitude: 330 },
      { number: 9, sign: "Рыбы", degree: 0, longitude: 360 },
      { number: 10, sign: "Овен", degree: 0, longitude: 30 },
      { number: 11, sign: "Телец", degree: 0, longitude: 60 },
      { number: 12, sign: "Близнецы", degree: 0, longitude: 90 },
    ],
    planets: [
      { name: "Солнце", sign: "Стрелец", degree: 20, longitude: 260, house: 6, retrograde: false },
      { name: "Луна", sign: "Рак", degree: 20, longitude: 140, house: 2, retrograde: false },
      { name: "Меркурий", sign: "Скорпион", degree: 0, longitude: 240, house: 5, retrograde: false },
      { name: "Венера", sign: "Стрелец", degree: 10, longitude: 280, house: 7, retrograde: false },
      { name: "Марс", sign: "Водолей", degree: 0, longitude: 330, house: 9, retrograde: false },
    ],
    aspects: [
      { planetA: "Луна", planetB: "Венера", aspectType: "трин", orb: 2.1, applying: null },
      { planetA: "Солнце", planetB: "Марс", aspectType: "квадрат", orb: 1.5, applying: null },
    ],
    angles: [],
    houseSystem: "placidus",
  },
  spheres: [
    { id: "1", title: "Мышление, речь, обучение", score: 7.5, rank: 1, description: "Коммуникация и интеллект" },
    { id: "2", title: "Дом, семья, корни", score: 6.8, rank: 2, description: "Семейные ценности" },
    { id: "3", title: "Работа, статус, достижения", score: 5.2, rank: 3, description: "Карьера" },
  ],
  planets: [
    { id: "moon", name: "Луна", sign: "Рак", house: 2, score: 8.2, description: "Эмоции и интуиция" },
    { id: "venus", name: "Венера", sign: "Стрелец", house: 7, score: 7.0, description: "Любовь и красота" },
    { id: "mars", name: "Марс", sign: "Водолей", house: 9, score: 6.5, description: "Энергия и действие" },
  ],
  chapters: [
    { id: "personality", eyebrow: "Личность", title: "Личность и характер", locked: true, description: "Твой личностный профиль" },
    { id: "career", eyebrow: "Карьера", title: "Карьера и призвание", locked: true, description: "Профессиональный путь" },
    { id: "relationships", eyebrow: "Отношения", title: "Отношения и партнёрство", locked: true, description: "Совместимость" },
  ],
  salesBullets: [
    "Личностный профиль планет и домов",
    "Сильные и слабые стороны характера",
    "Карьерные предрасположенности",
    "Совместимость с партнёрами",
  ],
  fullReportAvailable: false,
  fullReportPurchasable: false,
  fullReportPriceKopecks: 39900,
};
