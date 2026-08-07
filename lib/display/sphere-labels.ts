// ############################################################################
// AI_HEADER: MODULE_LIB_DISPLAY_SPHERE_LABELS
// ROLE: Deterministic mapping for the twelve product spheres and their human-readable
//       Russian labels. No fabricated astrology — unknown keys fail closed.
// ############################################################################

// START_MODULE_CONTRACT: M-LIB-DISPLAY-SPHERE-LABELS
// purpose: Provide the canonical twelve product sphere keys, labels, and icons.
//          Unknown or removed technical keys are never promoted into the product UI.
// owns:
//   - lib/display/sphere-labels.ts
// inputs: sphereKey: string — raw backend key
// outputs: string — human-readable label
// dependencies: none
// side_effects: none
// invariants:
//   - The canonical order contains exactly the twelve product sphere keys.
//   - Known keys always return the same label (deterministic).
//   - Unknown and removed keys return a safe generic label.
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
  { key: "friends_goals", label: "Друзья и планы", iconName: "target" },
]

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

/**
 * Return a human-readable Russian label for the given sphere score key.
 * Safe Russian fallback generic text, never English or snake_case.
 */
export function getSphereLabel(key: string): string {
  const trimmed = key.trim()
  if (trimmed.length === 0) return "Сфера"
  return PRODUCT_SPHERE_META[trimmed as ProductSphereKey]?.label ?? "Другая сфера"
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
