
// ############################################################################
// AI_HEADER: MODULE_MOCKS_READINGS
// ROLE: Lib — readings.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// #########################################// START_MODULE_CONTRACT
// purpose: Library: readings
// owns:
//   - lib/mocks/readings.ts
// inputs: Function arguments
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
/**
 * Мок-каталог разборов.
 *
 * Используется ИСКЛЮЧИТЕЛЬНО из `lib/api/readings.ts`. Когда подключим
 * бэкенд, каталог приедет с сервера — этот файл просто удалится.
 */

import {
  Sparkles,
  MessageCircleQuestion,
  CalendarRange,
  CalendarClock,
  Users,
  Target,
  Archive,
} from "lucide-react"

import type {
  AvailableReading,
  ComingReading,
  ReadingsCatalog,
} from "@/lib/readings"

const AVAILABLE: AvailableReading[] = [
  {
    key: "natal",
    title: "Натальная карта",
    description:
      "Твоя базовая структура: сильные стороны, внутренние темы и главные акценты карты.",
    icon: Sparkles,
    teaser: "10–15 минут чтения · с примерами из твоей жизни",
  },
  {
    key: "horary",
    title: "Хорар",
    description:
      "Задай точный вопрос и получи персональный астрологический разбор ответа.",
    icon: MessageCircleQuestion,
    teaser: "Ответ на конкретный вопрос · работает здесь и сейчас",
  },
]

const COMING: ComingReading[] = [
  {
    key: "month",
    title: "Месяц",
    description: "Персональный альманах месяца: главные окна, темы и периоды.",
    icon: CalendarRange,
  },
  {
    key: "year",
    title: "Год",
    description: "Большие дуги года, смена периодов и главные развилки.",
    icon: CalendarClock,
  },
  {
    key: "synastry",
    title: "Синастрия",
    description: "Как разворачивается контакт и динамика отношений.",
    icon: Users,
  },
  {
    key: "themes",
    title: "Тематические разборы",
    description: "Отдельные фокусы: работа, деньги, отношения, состояние.",
    icon: Target,
  },
  {
    key: "history",
    title: "История",
    description: "Архив сохранённых разборов и материалов.",
    icon: Archive,
  },
]

export function buildMockReadings(): ReadingsCatalog {
  return { available: AVAILABLE, coming: COMING }
}
