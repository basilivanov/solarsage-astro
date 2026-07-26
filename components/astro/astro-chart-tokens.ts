// ############################################################################
// AI_HEADER: MODULE_ASTRO_CHART_TOKENS
// ROLE: Shared astrological symbols, glyphs, and color tokens for charts
// DEPENDENCIES: none
// ############################################################################

// START_MODULE_CONTRACT: M-ASTRO-CHART-TOKENS
// purpose: Provide single source of truth for planet glyphs, sign glyphs, planet colors, and aspect tone colors.
// owns:
//   - components/astro/astro-chart-tokens.ts
// inputs: none
// outputs: PLANET_SYMBOLS, SIGN_SYMBOLS, PLANET_COLORS, ASPECT_COLORS_BY_TONE
// dependencies: none
// side_effects: none
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-ASTRO-CHART-TOKENS

// START_MODULE_MAP: M-ASTRO-CHART-TOKENS
// public_entrypoints:
//   - PLANET_SYMBOLS
//   - SIGN_SYMBOLS
//   - PLANET_COLORS
//   - ASPECT_COLORS_BY_TONE
//   - PLANET_RU_NAMES
//   - SIGN_RU_NAMES
// semantic_blocks: none
// owned_tests: none
// END_MODULE_MAP: M-ASTRO-CHART-TOKENS

export const PLANET_SYMBOLS: Record<string, string> = {
  Sun: "☉",
  Moon: "☽",
  Mercury: "☿",
  Venus: "♀",
  Mars: "♂",
  Jupiter: "♃",
  Saturn: "♄",
  Uranus: "♅",
  Neptune: "♆",
  Pluto: "♇",
  Ascendant: "ASC",
  ASC: "ASC",
  Midheaven: "MC",
  MC: "MC",
}

export const SIGN_SYMBOLS: Record<string, string> = {
  Aries: "♈",
  Taurus: "♉",
  Gemini: "♊",
  Cancer: "♋",
  Leo: "♌",
  Virgo: "♍",
  Libra: "♎",
  Scorpio: "♏",
  Sagittarius: "♐",
  Capricorn: "♑",
  Aquarius: "♒",
  Pisces: "♓",
}

export const SIGN_RU_NAMES: Record<string, string> = {
  Aries: "Овен",
  Taurus: "Телец",
  Gemini: "Близнецы",
  Cancer: "Рак",
  Leo: "Лев",
  Virgo: "Дева",
  Libra: "Весы",
  Scorpio: "Скорпион",
  Sagittarius: "Стрелец",
  Capricorn: "Козерог",
  Aquarius: "Водолей",
  Pisces: "Рыбы",
}

export const SIGN_RU_NAMES_PREPOSITIONAL: Record<string, string> = {
  Aries: "Овне",
  Taurus: "Тельце",
  Gemini: "Близнецах",
  Cancer: "Раке",
  Leo: "Льве",
  Virgo: "Деве",
  Libra: "Весах",
  Scorpio: "Скорпионе",
  Sagittarius: "Стрельце",
  Capricorn: "Козероге",
  Aquarius: "Водолее",
  Pisces: "Рыбах",
}

export const PLANET_RU_NAMES: Record<string, string> = {
  Sun: "Солнце",
  Moon: "Луна",
  Mercury: "Меркурий",
  Venus: "Венера",
  Mars: "Марс",
  Jupiter: "Юпитер",
  Saturn: "Сатурн",
  Uranus: "Уран",
  Neptune: "Нептун",
  Pluto: "Плутон",
  Ascendant: "Асцендент",
  ASC: "Асцендент",
  Midheaven: "MC",
  MC: "MC",
}

export const PLANET_MEANINGS: Record<string, string> = {
  Sun: "Ядро личности, самовыражение и сознательные жизненные цели.",
  Moon: "Подсознание, эмоции, базовая безопасность и повседневные привычки.",
  Mercury: "Мышление, стиль общения, обработка информации и логика.",
  Venus: "Отношения, привязанность, романтические ценности и понятие о красоте.",
  Mars: "Энергия, воля, запуск действий и отстаивание своих границ.",
  Jupiter: "Расширение возможностей, мировоззрение, щедрость и оптимизм.",
  Saturn: "Дисциплина, границы, ответственность и уроки на прочность.",
  Uranus: "Свобода, озарения, нестандартность и внезапные перемены.",
  Neptune: "Вдохновение, эмпатия, мечты и тонкая чувствительность.",
  Pluto: "Глубокая трансформация, сила притяжения и эмоциональная интенсивность.",
  Ascendant: "Первое впечатление, стиль проявления в мире и личные границы.",
  ASC: "Первое впечатление, стиль проявления в мире и личные границы.",
}

export const PLANET_COLORS: Record<string, string> = {
  Sun: "#d49a4f",
  Moon: "#795a86",
  Mercury: "#4b7bec",
  Venus: "#43806d",
  Mars: "#a64d59",
  Jupiter: "#b07b36",
  Saturn: "#57606f",
  Uranus: "#00a8ff",
  Neptune: "#3867d6",
  Pluto: "#8854d0",
  Ascendant: "#795a86",
  ASC: "#795a86",
}

export const ASPECT_COLORS_BY_TONE: Record<string, string> = {
  good: "#43806d",
  supportive: "#43806d",
  harmony: "#43806d",
  mid: "#b07b36",
  mixed: "#b07b36",
  neutral: "#b07b36",
  bad: "#a64d59",
  tense: "#a64d59",
  tension: "#a64d59",
}
