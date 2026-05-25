/**
 * Чистые редьюсеры — бизнес-логика без side-effects.
 *
 * Эти модули можно тестировать в Node.js без jsdom, RTL, браузерных API.
 * UI-хуки и компоненты становятся тонкими обёртками, которые конвертируют
 * React-эффекты в события редьюсеров.
 */

export * from "./chat-reducer"
export * from "./onboarding-reducer"
