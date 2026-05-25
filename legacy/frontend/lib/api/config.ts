/**
 * Конфигурация API-слоя.
 *
 * USE_FIXTURES=true включает мок-данные для dev/e2e.
 * В production должно быть false или не установлено.
 *
 * Проверка на этапе сборки:
 *  - В production сборке путь к fixtures недостижим
 *  - Tree-shaking удаляет весь мок-код из бандла
 */

export const USE_FIXTURES =
  process.env.NEXT_PUBLIC_USE_FIXTURES === "true" ||
  process.env.NODE_ENV === "development"

/**
 * Базовый URL для API-запросов.
 * В dev-режиме не используется (идём в fixtures).
 */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "/api"
