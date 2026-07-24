// ############################################################################
// AI_HEADER: FRONTEND_API_READINGS — past-day reading aggregation and static product catalog.
// ROLE: Past-day reading aggregator and static readings catalog provider.
// DEPENDENCIES: readings contracts and catalog types; TodayPayload; TodayPayloadWireSchema; lib/log/instrumented-fetch; lucide icons; Date; Promise.all
// GRACE_ANCHORS: [FRONTEND_API_READINGS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-READINGS
// purpose: Build unlocked reading previews from recent day payloads and expose available or coming reading products.
// owns:
//   - lib/api/readings.ts
// inputs: limit and offset for history; authenticated session.
// outputs: ReadingsList, ReadingsCatalog and async catalog alias.
// dependencies: readings contracts and catalog types; TodayPayload; TodayPayloadWireSchema; lib/log/instrumented-fetch; lucide icons; Date; Promise.all.
// side_effects: parallel credentialed GET /api/day/{date} calls for history via instrumentedFetch.
// emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed, frontend.api_request_failed, frontend.api_response_invalid.
// invariants:
//   - Requested dates remain prior days derived from offset and limit.
//   - Failed or non-ok day fetches and locked payloads are omitted.
//   - Preview remains the first reading paragraph or an empty string.
//   - hasMore remains entries.length equal to limit.
//   - Stable catalog keys, copy, icons and order remain unchanged.
// failure_policy: Per-day transport or non-ok failures return null and are omitted; catalog functions do not throw.
// END_MODULE_CONTRACT: M-FRONTEND-API-READINGS

// START_MODULE_MAP: M-FRONTEND-API-READINGS
// public_entrypoints:
//   - getReadingsList
//   - listReadings
//   - listReadingsAsync
// semantic_blocks:
//   - HISTORY_DATE_PLAN: derive prior dates from offset and limit.
//   - DAY_FETCH_FAIL_SOFT: fetch a day via instrumentedFetch and map request failures to null.
//   - HISTORY_ASSEMBLY: omit locked or missing days and build previews.
//   - PRODUCT_CATALOG: expose the stable available and coming products.
//   - ASYNC_CATALOG_ALIAS: resolve the synchronous catalog asynchronously.
// owned_tests:
//   - __tests__/api/readings.test.ts
//   - __tests__/components/ReadingsScreen.test.tsx
// END_MODULE_MAP: M-FRONTEND-API-READINGS

import type { ReadingsList, ReadingEntry } from "@/lib/contracts/readings"
import type { ReadingsCatalog } from "@/lib/readings"
import type { TodayPayload } from "@/packages/contracts"
import { TodayPayloadWireSchema } from "@/packages/contracts/runtime"
import { instrumentedFetch } from "@/lib/log/instrumented-fetch"

import { Sparkles, Star, CalendarDays, Calendar, Users } from "lucide-react"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

// START_BLOCK: HISTORY_ASSEMBLY
export async function getReadingsList(limit: number = 10, offset: number = 0): Promise<ReadingsList> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-READINGS.getReadingsList
  // purpose: Fetch history of past days concurrently, filtering unlocked readings and forming previews.
  // inputs: limit — max days to fetch, offset — day offset
  // returns: Promise<ReadingsList>
  // side_effects: parallel GET /api/day/{date} requests via fetchDayForReadings
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-READINGS.getReadingsList
  const entries: ReadingEntry[] = []

  const today = new Date()
  const promises: Promise<TodayPayload | null>[] = []
  for (let i = 0; i < limit; i++) {
    const date = new Date(today)
    date.setDate(today.getDate() - offset - i - 1)
    const dateStr = date.toISOString().split("T")[0]
    promises.push(fetchDayForReadings(dateStr))
  }

  const results = await Promise.all(promises)

  for (const payload of results) {
    if (payload && payload.access.state !== "locked") {
      entries.push({
        date: payload.date,
        headline: payload.headline,
        dayStatus: payload.dayStatus,
        preview: payload.reading.paragraphs[0] || "",
      })
    }
  }

  const hasMore = entries.length === limit
  return { entries, hasMore }
}
// END_BLOCK: HISTORY_ASSEMBLY

// START_BLOCK: DAY_FETCH_FAIL_SOFT
async function fetchDayForReadings(date: string): Promise<TodayPayload | null> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-READINGS.fetchDayForReadings
  // purpose: Fetch single past day payload via instrumentedFetch with TodayPayload responseContract, returning null on transport or HTTP failure.
  // inputs: date — YYYY-MM-DD string
  // returns: Promise<TodayPayload | null>
  // side_effects: GET /api/day/{date} via instrumentedFetch
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed, frontend.api_request_failed, frontend.api_response_invalid
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-READINGS.fetchDayForReadings
  try {
    const res = await instrumentedFetch({
      operation: "readings.day_history",
      routeTemplate: "GET /api/day/{date}",
      url: `${API_BASE}/api/day/${date}`,
      init: {
        credentials: "include",
        headers: {
          "Accept": "application/json",
        },
      },
      responseContract: {
        contractName: "TodayPayload",
        contractVersion: "v1",
        validate: (json) => {
          const parsed = TodayPayloadWireSchema.safeParse(json)
          if (parsed.success) return { valid: true }
          const fields = parsed.error.issues.map((i) => String(i.path[0] || "unknown"))
          return { valid: false, missingFields: fields, invalidFieldTypes: fields }
        },
      },
    })

    if (!res.ok) return null

    return res.json()
  } catch {
    return null
  }
}
// END_BLOCK: DAY_FETCH_FAIL_SOFT

// START_BLOCK: PRODUCT_CATALOG
export function listReadings(): ReadingsCatalog {
  return {
    available: [
      {
        key: "horary",
        title: "Хорар",
        description: "Задай точный вопрос и получи ответ карты",
        icon: Sparkles,
        teaser: "Конкретный вопрос — конкретный ответ по моменту вопроса",
      },
      {
        key: "election",
        title: "Подбор даты",
        description: "Лучшие даты для важного события",
        icon: Calendar,
        teaser: "Найди идеальные дни по звёздам для важных событий",
      },
      {
        key: "natal",
        title: "Натальная карта",
        description: "Глубокий разбор карты рождения",
        icon: Star,
        teaser: "Планеты, дома, аспекты — всё о тебе по данным рождения",
      },
    ],
    coming: [
      {
        key: "month",
        title: "Прогноз на месяц",
        description: "Что готовит ближайший месяц",
        icon: CalendarDays,
      },
      {
        key: "year",
        title: "Прогноз на год",
        description: "Главные темы года",
        icon: Calendar,
      },
      {
        key: "synastry",
        title: "Синастрия",
        description: "Совместимость с партнёром",
        icon: Users,
      },
    ],
  }
}
// END_BLOCK: PRODUCT_CATALOG

// START_BLOCK: ASYNC_CATALOG_ALIAS
export async function listReadingsAsync(): Promise<ReadingsCatalog> {
  return listReadings()
}
// END_BLOCK: ASYNC_CATALOG_ALIAS
