
// ############################################################################
// AI_HEADER: MODULE_LIB_CHAT
// ROLE: Lib — chat.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// #########################################// START_MODULE_CONTRACT
// purpose: Library: chat
// owns:
//   - lib/chat.ts
// inputs: Function arguments
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

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

/**
 * Короткое человекочитаемое описание натальной карты — для UI-плашки
 * «с учётом твоей карты» и для будущей подстановки в system prompt.
 */
export function buildContextSummary(profile: Profile): string {
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
  return [
    "Что говорит моя карта про карьеру?",
    "Стоит ли начинать новый проект сейчас?",
    "Какой главный аспект у меня на этой неделе?",
    "Лучшие дни для важного разговора в этом месяце",
  ]
}
