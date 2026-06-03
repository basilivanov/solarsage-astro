/**
 * Демо-режим — флаг для v0.app и локальной разработки.
 *
 * Когда NEXT_PUBLIC_DEMO_MODE=true:
 * - Все API-запросы подменяются на моки из lib/demo-data.ts
 * - Telegram auth пропускается (в v0 нет window.Telegram.WebApp)
 * - Все экраны работают без реального бэкенда
 */
export const IS_DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true"
