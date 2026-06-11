
// ############################################################################
// AI_HEADER: MODULE_LIB_LOADER_PROGRESS
// ROLE: Library module
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Library module — lib/loader-progress.ts
// owns:
//   - lib/loader-progress.ts
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

/**
 * Чистая логика CosmicLoader — вынесена из компонента, чтобы её можно было
 * тестировать в node-окружении (как остальные pure-функции проекта).
 *
 * Компонент только держит таймеры и React-состояние, а решает «какой
 * следующий процент» и «какую подпись показать» этот модуль.
 */

/** Потолок, до которого ползём, пока не пришёл `done`. */
export const PROGRESS_CEILING = 92
/** Старт прогресса, чтобы бар не был пустым на первом кадре. */
export const PROGRESS_START = 4
/** Шаг тикания прогресса, мс. */
export const PROGRESS_TICK = 90
/** Как часто меняем подпись, мс. */
export const MESSAGE_INTERVAL = 2400
/** Прибавка за тик после получения данных. */
export const DONE_STEP = 6

export const DEFAULT_MESSAGES = [
  "Связываюсь со звёздами…",
  "Сверяюсь с Луной…",
  "Читаю карту неба…",
  "Ловлю положение планет…",
  "Уточняю у Вселенной…",
  "Собираю разбор для тебя…",
  "Почти готово, ещё мгновение…",
]

export const DONE_MESSAGE = "Готово ✦ открываю твой день"

/**
 * Доля «оставшегося пути», которую проходим за один тик.
 * Чем короче durationHint — тем быстрее заполняемся, но не более 0.12 за тик.
 */
export function progressEase(durationHint: number): number {
  if (durationHint <= 0) return 0.12
  return Math.min(0.12, (PROGRESS_TICK / durationHint) * 2.6)
}

/**
 * Следующее значение прогресса.
 *  - done=true  → линейно дожимаем к 100% шагом DONE_STEP;
 *  - done=false → асимптотически приближаемся к потолку, не превышая его.
 */
export function nextProgress(
  current: number,
  done: boolean,
  durationHint: number,
): number {
  if (done) return Math.min(100, current + DONE_STEP)
  if (current >= PROGRESS_CEILING) return PROGRESS_CEILING
  return current + (PROGRESS_CEILING - current) * progressEase(durationHint)
}

/**
 * Подпись для текущего кадра. При done всегда финальная фраза, иначе —
 * элемент по индексу с защитой от пустого/кривого индекса.
 */
export function captionFor(
  done: boolean,
  index: number,
  messages: string[] = DEFAULT_MESSAGES,
): string {
  if (done) return DONE_MESSAGE
  if (messages.length === 0) return ""
  const safe = ((index % messages.length) + messages.length) % messages.length
  return messages[safe]
}

/** Следующий индекс подписи (циклический). */
export function nextMessageIndex(index: number, total: number): number {
  if (total <= 0) return 0
  return (index + 1) % total
}
