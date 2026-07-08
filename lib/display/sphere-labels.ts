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

/** Maps backend sphere keys to product-facing short labels and icons */
export const SPHERE_PRODUCT_MAP: Record<string, { label: string; icon: string }> = {
  // 1. Работа
  work_status_achievement: { label: "Работа", icon: "💼" },
  career: { label: "Работа", icon: "💼" },
  career_social_status: { label: "Работа", icon: "💼" },
  public_image: { label: "Работа", icon: "💼" },
  technology_innovation: { label: "Работа", icon: "💼" },

  // 2. Деньги
  finance_money: { label: "Деньги", icon: "💰" },
  money_security_resources: { label: "Деньги", icon: "💰" },

  // 3. Документы
  legal_affairs: { label: "Документы", icon: "📝" },
  partnerships_contracts: { label: "Документы", icon: "📝" },

  // 4. Отношения
  relationships_partnership: { label: "Отношения", icon: "💖" },
  relationships: { label: "Отношения", icon: "💖" },

  // 5. Спорт
  body_energy_health: { label: "Спорт", icon: "🏃" },
  daily_routine: { label: "Спорт", icon: "🏃" },
  service_routine: { label: "Спорт", icon: "🏃" },

  // 6. Общение
  communication_learning: { label: "Общение", icon: "💬" },
  thinking_speech_learning: { label: "Общение", icon: "💬" },
  friendship_social: { label: "Общение", icon: "💬" },

  // 7. Здоровье
  spirituality_inner_growth: { label: "Здоровье", icon: "🌿" },
  inner_background_unconscious: { label: "Здоровье", icon: "🌿" },
  healing: { label: "Здоровье", icon: "🌿" },
  philosophy: { label: "Здоровье", icon: "🌿" },
  hidden_matters: { label: "Здоровье", icon: "🌿" },

  // 8. Решения
  career_ambition: { label: "Решения", icon: "🎯" },
  crisis_transformation: { label: "Решения", icon: "🎯" },
  crisis_transformation_control: { label: "Решения", icon: "🎯" },

  // 9. Поездки
  travel_adventure: { label: "Поездки", icon: "✈️" },
  long_distance: { label: "Поездки", icon: "✈️" },
  meaning_expansion_vector: { label: "Поездки", icon: "✈️" },

  // 10. Творчество
  creativity_self_expression: { label: "Творчество", icon: "🎨" },

  // 11. Учёба
  education: { label: "Учёба", icon: "📚" },
  higher_education: { label: "Учёба", icon: "📚" },

  // 12. Покупки
  joint_finance: { label: "Покупки", icon: "🛍️" },
  debts: { label: "Покупки", icon: "🛍️" },
  investment: { label: "Покупки", icon: "🛍️" },
  inheritance: { label: "Покупки", icon: "🛍️" },

  // Семья / Roots (transitional / fallback)
  home_family_roots: { label: "Семья", icon: "🏠" },
  home_family: { label: "Семья", icon: "🏠" },
}
