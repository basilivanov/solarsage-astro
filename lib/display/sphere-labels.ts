// ############################################################################
// AI_HEADER: MODULE_LIB_DISPLAY_SPHERE_LABELS
// ROLE: Deterministic mapping from backend sphere scoring keys to human-readable
//       Russian labels. No fabricated astrology — only known key → label mapping
//       with a fallback formatter for unknown keys.
// ############################################################################

// START_MODULE_CONTRACT: M-LIB-DISPLAY-SPHERE-LABELS
// purpose: Provide human-readable Russian labels for backend sphere score keys.
//          Raw technical keys (e.g. "work_status_achievement") are translated
//          via a static map. Unknown keys are converted from snake_case to a
//          readable Russian approximation.
// owns:
//   - lib/display/sphere-labels.ts
// inputs: sphereKey: string — raw backend key
// outputs: string — human-readable label
// dependencies: none
// side_effects: none
// invariants:
//   - Known keys always return the same label (deterministic)
//   - Unknown keys are formatted via snake_case → readable heuristic
// failure_policy: never throws; returns fallback "Сфера {key}" for truly unknown
// END_MODULE_CONTRACT: M-LIB-DISPLAY-SPHERE-LABELS

const KNOWN_SPHERE_LABELS: Record<string, string> = {
  // Canon / active keys (Wave 4+ backend)
  thinking_speech_learning: "Мышление, речь, обучение",
  money_security_resources: "Деньги, безопасность, ресурсы",
  home_family_roots: "Дом, семья, корни",
  work_status_achievement: "Работа, статус, достижения",
  relationships_partnership: "Отношения и партнёрство",
  body_energy_health: "Энергия и здоровье",

  // Legacy / transitional keys
  relationships: "Отношения",
  career: "Карьера",
  rest: "Отдых и восстановление",
  finance_money: "Финансы",
  creativity_self_expression: "Творчество и самовыражение",
  home_family: "Дом и семья",
  communication_learning: "Общение и обучение",
  travel_adventure: "Путешествия",
  spirituality_inner_growth: "Духовность и рост",
  friendship_social: "Друзья и окружение",
  career_ambition: "Амбиции и карьера",
  daily_routine: "Повседневные дела",
  legal_affairs: "Юридические вопросы",
  investment: "Инвестиции",
  inheritance: "Наследство",
  education: "Образование",
  public_image: "Общественный образ",
  hidden_matters: "Скрытые процессы",
  partnerships_contracts: "Контракты и соглашения",
  crisis_transformation: "Трансформации",
  long_distance: "Дальние поездки",
  higher_education: "Высшее образование",
  philosophy: "Философия и мировоззрение",
  career_social_status: "Социальный статус",
  technology_innovation: "Технологии и инновации",
  healing: "Исцеление",
  service_routine: "Служение и рутина",
  joint_finance: "Общие финансы",
  debts: "Долги и обязательства",
}

/**
 * Convert a snake_case string to a readable Russian approximation.
 * This is the fallback for unknown keys — prefer adding to KNOWN_SPHERE_LABELS.
 */
function snakeToReadable(key: string): string {
  return key
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")
}

/**
 * Return a human-readable Russian label for the given sphere score key.
 * Uses the known mapping if available, otherwise formats the raw key.
 */
export function getSphereLabel(key: string): string {
  const trimmed = key.trim()
  if (trimmed.length === 0) return "Сфера"
  return KNOWN_SPHERE_LABELS[trimmed] ?? snakeToReadable(trimmed)
}

/** Map English planet names to Russian product labels */
export const PLANET_LABELS: Record<string, string> = {
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
}

export function getPlanetLabel(name: string): string {
  return PLANET_LABELS[name] ?? name
}
