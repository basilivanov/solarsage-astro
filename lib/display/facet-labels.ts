// ############################################################################
// AI_HEADER: MODULE_LIB_DISPLAY_FACET_LABELS
// ROLE: Deterministic mapping from sphere facet keys to human-readable Russian
//       labels. Facet is a nullable refinement of a product sphere signal
//       (TZ 2026-08-06 §4); null/unknown facets never invent a label.
// ############################################################################

// START_MODULE_CONTRACT: M-LIB-DISPLAY-FACET-LABELS
// purpose: Provide human-readable Russian labels for sphere facet keys and a
//          fail-closed reader for the additive `facet` wire field that the
//          generated contracts do not expose yet.
// owns:
//   - lib/display/facet-labels.ts
// inputs: facet key (string | null | undefined) or an unknown wire object.
// outputs: Russian facet label or null when the facet is absent/unknown.
// dependencies: none.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - Known facets always return the same label (deterministic).
//   - facet=null and unknown keys return null; the UI then shows only the sphere label.
// failure_policy: never throws; unknown shapes degrade to null.
// END_MODULE_CONTRACT: M-LIB-DISPLAY-FACET-LABELS

// START_MODULE_MAP: M-LIB-DISPLAY-FACET-LABELS
// public_entrypoints:
//   - FACET_LABELS
//   - getFacetLabel
//   - readSignalFacet
// semantic_blocks:
//   - FACET_LABELS: canonical facet key -> Russian label map (TZ §4).
//   - FACET_READ: fail-closed accessors for the additive wire field.
// owned_tests: none (prototype ahead of generated contracts)
// END_MODULE_MAP: M-LIB-DISPLAY-FACET-LABELS

// START_BLOCK: FACET_LABELS
/** Canonical facet labels (TZ 2026-08-06 §4), grouped by owning sphere. */
export const FACET_LABELS: Record<string, string> = {
  // Работа
  daily_work: "Текущие задачи",
  career_status: "Карьера и статус",

  // Финансы
  personal_money: "Личные деньги",
  shared_money: "Общий бюджет",
  purchases_transactions: "Покупки и сделки",
  financial_obligations: "Финансовые обязательства",

  // Документы
  admin_documents: "Административные документы",
  legal_foreign_education_documents: "Юридические и заграничные документы",
  contracts: "Договоры",
  financial_documents: "Финансовые документы",
  property_documents: "Документы на жильё",

  // Отношения
  romance: "Романтика",
  partnership: "Партнёрство",

  // Спорт
  physical_energy: "Физическая энергия",
  training_routine: "Режим тренировок",
  competition_performance: "Соревнования и выступления",

  // Общение
  everyday_contacts: "Повседневные контакты",
  negotiations: "Переговоры",
  groups_audience: "Группы и аудитория",
  public_speech_teaching: "Выступления и преподавание",

  // Здоровье
  general_condition: "Общее состояние",
  symptoms_routine_treatment: "Симптомы и лечение",
  recovery_isolation: "Отдых и восстановление",

  // Дом и семья
  family_roots: "Семья и корни",
  housing_property: "Жильё и недвижимость",
  relocation: "Переезд",

  // Поездки
  local_travel: "Короткие поездки",
  long_distance_foreign_travel: "Дальние поездки",

  // Творчество
  self_expression: "Самовыражение",
  creative_work: "Творческий проект",
  private_inner_creativity: "Творчество в уединении",

  // Учёба
  skills_courses: "Навыки и курсы",
  higher_education_worldview: "Высшее образование и мировоззрение",

  // Друзья и планы
  friends_community: "Друзья и сообщества",
  collective_projects: "Совместные проекты",
  long_term_goals: "Долгосрочные планы",
}
// END_BLOCK: FACET_LABELS

// START_BLOCK: FACET_READ
export function getFacetLabel(facet: string | null | undefined): string | null {
  // START_FUNCTION_CONTRACT: F-M-LIB-DISPLAY-FACET-LABELS.getFacetLabel
  // purpose: Return the approved Russian label for a facet key.
  // inputs: facet — nullable facet key from the wire signal.
  // returns: Russian label, or null for null/unknown facets.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: unknown keys return null so the UI falls back to the sphere label.
  // END_FUNCTION_CONTRACT: F-M-LIB-DISPLAY-FACET-LABELS.getFacetLabel
  if (!facet) return null
  return FACET_LABELS[facet] ?? null
}

export function readSignalFacet(source: unknown): string | null {
  // START_FUNCTION_CONTRACT: F-M-LIB-DISPLAY-FACET-LABELS.readSignalFacet
  // purpose: Extract the additive `facet` field from a wire object whose
  //          generated TypeScript type does not declare it yet.
  // inputs: source — event/impulse/group-shaped unknown value.
  // returns: the facet string, or null when absent or not a string.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: non-object and malformed values degrade to null.
  // END_FUNCTION_CONTRACT: F-M-LIB-DISPLAY-FACET-LABELS.readSignalFacet
  if (!source || typeof source !== "object") return null
  const facet = (source as { facet?: unknown }).facet
  return typeof facet === "string" && facet.length > 0 ? facet : null
}
// END_BLOCK: FACET_READ
