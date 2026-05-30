/**
 * Мок-справочник городов.
 *
 * Используется ИСКЛЮЧИТЕЛЬНО из `lib/api/cities.ts`. Когда подключим
 * настоящий поиск (бэкенд / внешний геокодер), этот файл просто удалится,
 * а `lib/api/cities.ts` начнёт ходить по сети.
 */

import type { City } from "@/lib/contracts/city"

const CITIES: City[] = [
  { name: "Москва", country: "Россия" },
  { name: "Санкт-Петербург", country: "Россия" },
  { name: "Казань", country: "Россия" },
  { name: "Екатеринбург", country: "Россия" },
  { name: "Новосибирск", country: "Россия" },
  { name: "Нижний Новгород", country: "Россия" },
  { name: "Краснодар", country: "Россия" },
  { name: "Сочи", country: "Россия" },
  { name: "Владивосток", country: "Россия" },
  { name: "Калининград", country: "Россия" },
  { name: "Минск", country: "Беларусь" },
  { name: "Киев", country: "Украина" },
  { name: "Алматы", country: "Казахстан" },
  { name: "Астана", country: "Казахстан" },
  { name: "Тбилиси", country: "Грузия" },
  { name: "Ереван", country: "Армения" },
  { name: "Баку", country: "Азербайджан" },
  { name: "Ташкент", country: "Узбекистан" },
  { name: "Белград", country: "Сербия" },
  { name: "Берлин", country: "Германия" },
  { name: "Лондон", country: "Великобритания" },
  { name: "Париж", country: "Франция" },
  { name: "Лиссабон", country: "Португалия" },
  { name: "Дубай", country: "ОАЭ" },
  { name: "Стамбул", country: "Турция" },
  { name: "Бангкок", country: "Таиланд" },
  { name: "Нью-Йорк", country: "США" },
]

const POPULAR = ["Москва", "Санкт-Петербург", "Берлин", "Тбилиси"]

const DEFAULT_LIMIT = 6

export function searchMockCities(query: string, limit = DEFAULT_LIMIT): City[] {
  const q = query.trim().toLowerCase()
  if (!q) return []
  return CITIES.filter((c) => c.name.toLowerCase().includes(q)).slice(0, limit)
}

export function getMockPopularCities(): string[] {
  return POPULAR
}
