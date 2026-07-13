// ############################################################################
// AI_HEADER: APP_CHECKIN_PAGE — timezone-aware check-in route composition.
// ROLE: Client Next.js page called by /checkin; resolves the target date from profile timezone/query state and hosts CheckinScreen navigation.
// ############################################################################

// START_MODULE_CONTRACT: M-APP-CHECKIN-PAGE
// purpose: Render the day check-in route for the canonical target date and navigate back or to the completed day.
// owns:
//   - app/(grace)/checkin/page.tsx
// inputs: target/date query parameters, current time, and profile current/birth timezone.
// outputs: Accessible page shell with back control and CheckinScreen.
// dependencies: React useMemo; next/navigation; lucide-react; CheckinScreen; useProfile; resolveCheckinTargetDate.
// side_effects: Reads profile hook state and performs router.back/router.push navigation.
// emitted_logs: none.
// invariants:
//   - Target date is resolved only by resolveCheckinTargetDate using the best available profile timezone.
//   - Completion navigates to /day/<resolved targetDate>.
//   - Icon-only back button retains aria-label=Назад.
// failure_policy: Resolver/render failures bubble to the route boundary; submission failures remain owned by CheckinScreen.
// END_MODULE_CONTRACT: M-APP-CHECKIN-PAGE

// START_MODULE_MAP: M-APP-CHECKIN-PAGE
// public_entrypoints:
//   - CheckinPage (default).
// semantic_blocks:
//   - TARGET_RESOLUTION: derive timezone, query target and canonical date.
//   - PAGE_NAVIGATION: back and completion navigation.
//   - PAGE_COMPOSITION: render header and CheckinScreen.
// owned_tests:
//   - __tests__/app/checkin-page.test.tsx
// END_MODULE_MAP: M-APP-CHECKIN-PAGE

"use client"

import { useMemo } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { ArrowLeft } from "lucide-react"

import { CheckinScreen } from "@/components/checkin/checkin-screen"
import { useProfile } from "@/hooks/use-profile"
import { resolveCheckinTargetDate } from "@/lib/api/checkin"

export default function CheckinPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { profile } = useProfile()
  const timeZone =
    profile.currentLocation?.timezone || profile.birthLocation?.timezone || null
  const target = searchParams.get("target") || searchParams.get("date")
  const targetDate = useMemo(
    () => resolveCheckinTargetDate(new Date(), timeZone, target),
    [timeZone, target],
  )

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto max-w-md">
        <div className="flex items-center gap-3 px-5 pt-6">
          <button
            type="button"
            aria-label="Назад"
            onClick={() => router.back()}
            className="flex h-9 w-9 items-center justify-center rounded-full border border-border/70 text-foreground"
          >
            <ArrowLeft className="h-4 w-4" strokeWidth={1.75} />
          </button>
          <h1 className="font-serif text-[20px] leading-tight text-foreground">
            Оценка дня
          </h1>
        </div>
        <CheckinScreen
          targetDate={targetDate}
          onComplete={() => router.push(`/day/${targetDate}`)}
        />
      </div>
    </main>
  )
}
