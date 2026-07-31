// ############################################################################
// AI_HEADER: FRONTEND_API_READINGS — published day-history client and static product catalog.
// ROLE: Published snapshot history facade and static readings catalog provider.
// DEPENDENCIES: day-history contract types and generated wire schema; catalog types; lib/log/instrumented-fetch; lucide icons
// GRACE_ANCHORS: [FRONTEND_API_READINGS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-READINGS
// purpose: Fetch published Today snapshots for the readings history and expose available or coming reading products.
// owns:
//   - lib/api/readings.ts
// inputs: limit and offset for history; authenticated session.
// outputs: ReadingsList, ReadingsCatalog and async catalog alias.
// dependencies: DayHistoryPayload and DayHistoryItem types; generated DayHistoryPayload zod schema; lib/log/instrumented-fetch; catalog types.
// side_effects: one credentialed GET /api/readings/day-history call for each history request.
// emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed, frontend.api_request_failed, frontend.api_response_invalid.
// invariants:
//   - History contains only published snapshot summaries returned by day-history.
//   - The client never fans out into one cold /api/day calculation per history item.
//   - History entries contain state, dayTone, sphereKeys and impulseCount, not legacy reading paragraphs.
//   - Transport, HTTP and wire-validation failures fail soft to an empty history.
//   - hasMore remains entries.length equal to limit.
//   - Stable catalog keys, copy, icons and order remain unchanged.
// failure_policy: History request failures return an empty list; catalog functions do not throw.
// END_MODULE_CONTRACT: M-FRONTEND-API-READINGS

// START_MODULE_MAP: M-FRONTEND-API-READINGS
// public_entrypoints:
//   - getReadingsList
//   - listReadings
//   - listReadingsAsync
// semantic_blocks:
//   - HISTORY_REQUEST: fetch, validate and map the published day-history payload.
//   - PRODUCT_CATALOG: expose the stable available and coming products.
//   - ASYNC_CATALOG_ALIAS: resolve the synchronous catalog asynchronously.
// owned_tests:
//   - __tests__/api/readings.test.ts
//   - __tests__/components/ReadingsScreen.test.tsx
// END_MODULE_MAP: M-FRONTEND-API-READINGS

import type { ReadingsCatalog } from "@/lib/readings"
import type { DayHistoryItem, DayHistoryPayload } from "@/packages/contracts/day-history"
// The generated DayHistory schema is not re-exported by the frozen runtime barrel yet.
// eslint-disable-next-line grace/contracts-only-import
import { DayHistoryPayload as DayHistoryPayloadWireSchema } from "@/packages/contracts/_generated.zod"
import { instrumentedFetch } from "@/lib/log/instrumented-fetch"

import { Sparkles, Star, CalendarDays, Calendar, Users } from "lucide-react"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

export type ReadingEntry = Pick<
  DayHistoryItem,
  "date" | "snapshotId" | "state" | "dayTone" | "sphereKeys" | "impulseCount"
>

export type ReadingsList = {
  entries: ReadingEntry[]
  hasMore: boolean
  access: DayHistoryPayload["access"] | null
}

function emptyReadingsList(): ReadingsList {
  return { entries: [], hasMore: false, access: null }
}

// START_BLOCK: HISTORY_REQUEST
export async function getReadingsList(limit: number = 10, _offset: number = 0): Promise<ReadingsList> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-READINGS.getReadingsList
  // purpose: Fetch the published day-history snapshot summaries in one request.
  // inputs: limit — max snapshot summaries to request, _offset — retained compatibility argument; day-history is server-paginated by limit.
  // returns: Promise<ReadingsList>
  // side_effects: one GET /api/readings/day-history?limit=N via instrumentedFetch
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-READINGS.getReadingsList
  const requestedLimit = Number.isFinite(limit) ? Math.max(1, Math.floor(limit)) : 10

  try {
    const response = await instrumentedFetch({
      operation: "readings.day_history",
      routeTemplate: "GET /api/readings/day-history",
      url: `${API_BASE}/api/readings/day-history?limit=${requestedLimit}`,
      init: {
        credentials: "include",
        headers: {
          "Accept": "application/json",
        },
      },
      responseContract: {
        contractName: "DayHistoryPayload",
        contractVersion: "v1",
        validate: (json) => {
          const parsed = DayHistoryPayloadWireSchema.safeParse(json)
          if (parsed.success) return { valid: true }
          const fields = parsed.error.issues.map((issue) => String(issue.path[0] || "unknown"))
          return { valid: false, missingFields: fields, invalidFieldTypes: fields }
        },
      },
    })

    if (!response.ok) return emptyReadingsList()

    const parsed = DayHistoryPayloadWireSchema.safeParse(await response.json())
    if (!parsed.success) return emptyReadingsList()

    const payload = parsed.data as DayHistoryPayload
    const entries: ReadingEntry[] = payload.items.map((item) => ({
      date: item.date,
      snapshotId: item.snapshotId,
      state: item.state,
      dayTone: item.dayTone,
      sphereKeys: item.sphereKeys,
      impulseCount: item.impulseCount,
    }))
    return {
      entries,
      hasMore: entries.length === requestedLimit,
      access: payload.access,
    }
  } catch {
    return emptyReadingsList()
  }
}
// END_BLOCK: HISTORY_REQUEST

// START_BLOCK: PRODUCT_CATALOG
export function listReadings(): ReadingsCatalog {
  return {
    available: [
      {
        key: "synastry",
        title: "Совместимость",
        description: "Совместимость с партнёром",
        icon: Users,
        teaser: "Синастрия — анализ совместимости двух натальных карт",
      },
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
    ],
  }
}
// END_BLOCK: PRODUCT_CATALOG

// START_BLOCK: ASYNC_CATALOG_ALIAS
export async function listReadingsAsync(): Promise<ReadingsCatalog> {
  return listReadings()
}
// END_BLOCK: ASYNC_CATALOG_ALIAS
