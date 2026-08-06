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

export type ProductSphereKey =
  | "work"
  | "finance"
  | "documents"
  | "relationships"
  | "sport"
  | "communication"
  | "health"
  | "home_family"
  | "travel"
  | "creativity"
  | "study"
  | "friends_goals"

/** Canonical product sphere list and order (TZ 2026-08-06 §3) */
export const CANONICAL_PRODUCT_ORDER: { key: ProductSphereKey; label: string; iconName: string }[] = [
  { key: "work", label: "Работа", iconName: "briefcase" },
  { key: "finance", label: "Финансы", iconName: "coins" },
  { key: "documents", label: "Документы", iconName: "list-checks" },
  { key: "relationships", label: "Отношения", iconName: "sparkle" },
  { key: "sport", label: "Спорт", iconName: "leaf" },
  { key: "communication", label: "Общение", iconName: "telescope" },
  { key: "health", label: "Здоровье", iconName: "compass" },
  { key: "home_family", label: "Дом и семья", iconName: "home" },
  { key: "travel", label: "Поездки", iconName: "hourglass" },
  { key: "creativity", label: "Творчество", iconName: "grid" },
  { key: "study", label: "Учёба", iconName: "layers" },
  { key: "friends_goals", label: "Друзья и планы", iconName: "users" },
]

/**
 * Maps legacy backend sphere keys directly to canonical ProductSphereKey.
 * Prototype-era mapping: the authoritative resolver moves to the backend
 * (product_spheres.v1.yml); this map only keeps old technical keys renderable.
 */
export const BACKEND_TO_PRODUCT_KEY_MAP: Record<string, ProductSphereKey> = {
  // 1. Работа
  work_status_achievement: "work",
  career: "work",
  career_social_status: "work",
  public_image: "work",
  technology_innovation: "work",
  career_ambition: "work",

  // 2. Финансы
  finance_money: "finance",
  money_security_resources: "finance",
  joint_finance: "finance",
  debts: "finance",
  investment: "finance",
  inheritance: "finance",
  crisis_transformation: "finance",
  crisis_transformation_control: "finance",

  // 3. Документы
  legal_affairs: "documents",
  partnerships_contracts: "documents",

  // 4. Отношения
  relationships_partnership: "relationships",
  relationships: "relationships",

  // 5. Спорт
  body_energy_health: "sport",
  daily_routine: "sport",
  service_routine: "sport",

  // 6. Общение
  communication_learning: "communication",
  thinking_speech_learning: "communication",

  // 7. Здоровье
  spirituality_inner_growth: "health",
  inner_background_unconscious: "health",
  healing: "health",
  hidden_matters: "health",

  // 8. Дом и семья
  home_family_roots: "home_family",
  home_family: "home_family",

  // 9. Поездки
  travel_adventure: "travel",
  long_distance: "travel",
  meaning_expansion_vector: "travel",

  // 10. Творчество
  creativity_self_expression: "creativity",

  // 11. Учёба
  education: "study",
  higher_education: "study",
  philosophy: "study",

  // 12. Друзья и планы
  friendship_social: "friends_goals",
}

/** Product key -> label/icon map */
export const PRODUCT_SPHERE_META: Record<ProductSphereKey, { label: string; icon: string }> = {
  work: { label: "Работа", icon: "💼" },
  finance: { label: "Финансы", icon: "💰" },
  documents: { label: "Документы", icon: "📝" },
  relationships: { label: "Отношения", icon: "💖" },
  sport: { label: "Спорт", icon: "🏃" },
  communication: { label: "Общение", icon: "💬" },
  health: { label: "Здоровье", icon: "🌿" },
  home_family: { label: "Дом и семья", icon: "🏠" },
  travel: { label: "Поездки", icon: "✈️" },
  creativity: { label: "Творчество", icon: "🎨" },
  study: { label: "Учёба", icon: "📚" },
  friends_goals: { label: "Друзья и планы", icon: "👥" },
}

const KNOWN_SPHERE_LABELS: Record<string, string> = {
  thinking_speech_learning: "Мышление, речь, обучение",
  money_security_resources: "Деньги, безопасность, ресурсы",
  home_family_roots: "Дом, семья, корни",
  work_status_achievement: "Работа, статус, достижения",
  relationships_partnership: "Отношения и партнёрство",
  body_energy_health: "Энергия и здоровье",
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

/** Legacy map - kept for backward compatibility */
export const SPHERE_PRODUCT_MAP = PRODUCT_SPHERE_META

/**
 * Return a human-readable Russian label for the given sphere score key.
 * Safe Russian fallback generic text, never English or snake_case.
 */
export function getSphereLabel(key: string): string {
  const trimmed = key.trim()
  if (trimmed.length === 0) return "Сфера"
  return KNOWN_SPHERE_LABELS[trimmed] ?? "Другая сфера"
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
