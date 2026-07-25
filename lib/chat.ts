// ############################################################################
// AI_HEADER: MODULE_LIB_CHAT
// ROLE: Chat context summary builder and suggested prompts formatting helpers.
// DEPENDENCIES: lib/profile, lib/contracts/chat
// GRACE_ANCHORS: [CHAT_HELPERS]
// SLICE: SLICE-FRONTEND-API-FACADES
// ############################################################################
"use client"

// START_MODULE_CONTRACT: M-LIB-CHAT
// purpose: Chat context summary builder and suggested prompts formatting helpers.
// owns:
//   - lib/chat.ts
// inputs: profile (Profile)
// outputs: context summary string and suggested prompt string array
// dependencies: lib/profile, lib/contracts/chat
// side_effects: none (pure)
// emitted_logs: none
// invariants:
//   - suggestedPrompts returns exactly four prompt options
// failure_policy: none
// END_MODULE_CONTRACT: M-LIB-CHAT

// START_MODULE_MAP: M-LIB-CHAT
// public_entrypoints:
//   - buildContextSummary
//   - suggestedPrompts
// semantic_blocks:
//   - CHAT_HELPERS: buildContextSummary and suggestedPrompts functions
// owned_tests:
//   - __tests__/lib/chat.test.ts
// END_MODULE_MAP: M-LIB-CHAT

import {
  formatBirthDate,
  formatBirthTime,
  type Profile,
} from "@/lib/profile"

/**
 * Контракт чата: типы и чистые helpers (без сетевых вызовов).
 *
 * Типы данных определены в контрактах (lib/contracts/chat.ts).
 * Стрим-агента живёт в `lib/api/chat.ts` — UI и хук `useChat` зовут
 * `sendMessage` оттуда. Сюда — только за типами и форматированием.
 */

// Реэкспорт типов из контрактов
export type { ChatRole, ChatMessage, ChatContext } from "@/lib/contracts/chat"

// START_BLOCK: CHAT_HELPERS
/**
 * Короткое человекочитаемое описание натальной карты — для UI-плашки
 * «с учётом твоей карты» и для будущей подстановки в system prompt.
 */
export function buildContextSummary(profile: Profile): string {
  // START_FUNCTION_CONTRACT: F-M-LIB-CHAT.buildContextSummary
  // purpose: Format a short human-readable summary of profile birth data for chat UI context.
  // inputs: profile (Profile)
  // returns: string
  // side_effects: none
  // error_behavior: none
  // END_FUNCTION_CONTRACT: F-M-LIB-CHAT.buildContextSummary
  const date = formatBirthDate(profile.birthDate)
  const time = formatBirthTime(profile.birthTime)
  return `${date}, ${time} — ${profile.birthPlace}`
}

/**
 * Варианты «быстрого старта», которые показываем в пустом состоянии.
 *
 * Сейчас они статичные, но функция принимает профиль, чтобы потом
 * легко подмешивать персональные («…про твоё Солнце во Льве»).
 */
export function suggestedPrompts(_profile: Profile): string[] {
  // START_FUNCTION_CONTRACT: F-M-LIB-CHAT.suggestedPrompts
  // purpose: Return suggested quick-start prompt questions.
  // inputs: _profile (Profile)
  // returns: string[]
  // side_effects: none
  // error_behavior: none
  // END_FUNCTION_CONTRACT: F-M-LIB-CHAT.suggestedPrompts
  return [
    "Что говорит моя карта про карьеру?",
    "Стоит ли начинать новый проект сейчас?",
    "Какой главный аспект у меня на этой неделе?",
    "Лучшие дни для важного разговора в этом месяце",
  ]
}
// END_BLOCK: CHAT_HELPERS
