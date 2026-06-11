
// ############################################################################
// AI_HEADER: MODULE_NATAL_PAGE
// ROLE: Next.js page
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// #########################################// START_MODULE_CONTRACT
// purpose: UI page — component
// owns:
//   - app/(grace)/readings/natal/page.tsx
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: React state management
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import { useCallback, useEffect, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { ChevronLeft } from "lucide-react"

import { CalculationDepth } from "@/components/readings/natal-preview/calculation-depth"
import { CtaButton } from "@/components/readings/natal-preview/cta-button"
import { ErrorCard } from "@/components/readings/natal-preview/error-card"
import { HeroSection } from "@/components/readings/natal-preview/hero-section"
import { HighlightsChips } from "@/components/readings/natal-preview/highlights-chips"
import { LoadingSkeleton } from "@/components/readings/natal-preview/loading-skeleton"
import { LockedChapters } from "@/components/readings/natal-preview/locked-chapters"
import { PersonalHook } from "@/components/readings/natal-preview/personal-hook"
import { PlanetsRow } from "@/components/readings/natal-preview/planets-row"
import { ProfileIncompleteCard } from "@/components/readings/natal-preview/profile-incomplete-card"
import { SalesBullets } from "@/components/readings/natal-preview/sales-bullets"
import { SpheresStrip } from "@/components/readings/natal-preview/spheres-strip"
import { fetchNatalPreview } from "@/lib/api/natal"
import type { NatalPreviewRead } from "@/lib/contracts/natal"

type State =
  | { status: "loading" }
  | { status: "profile_incomplete"; missingFields: string[] }
  | { status: "error"; message: string }
  | { status: "ready"; data: NatalPreviewRead }

export default function NatalReadingPage() {
  const [state, setState] = useState<State>({ status: "loading" })
  const router = useRouter()

  const load = useCallback(async () => {
    setState({ status: "loading" })
    const result = await fetchNatalPreview()
    if (!result.ok) {
      if (result.error.type === "profile_incomplete") {
        setState({ status: "profile_incomplete", missingFields: result.error.missingFields || [] })
        return
      }
      setState({ status: "error", message: result.error.message })
      return
    }
    setState({ status: "ready", data: result.data })
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const handleOpenReport = useCallback(() => {
    // Wave 5: Route to generating page, which handles both cases:
    // - If a READY report exists, backend returns it immediately and we redirect
    // - If not, generation starts. Backend idempotency ensures no duplicate work.
    router.push("/readings/natal/generating")
  }, [router])

  return (
    <div className="flex h-full w-full flex-col bg-background overflow-y-auto">
      <header
        className="flex-none px-4 pb-4 border-b border-border/40"
        style={{ paddingTop: "max(env(safe-area-inset-top), 1rem)" }}
      >
        <Link
          href="/readings"
          className="inline-flex items-center gap-1.5 text-[14px] text-muted-foreground hover:text-foreground active:scale-95 transition"
        >
          <ChevronLeft className="h-4 w-4" />
          <span>Разборы</span>
        </Link>
      </header>

      <main className="flex-1 px-5 py-6 space-y-5 max-w-md mx-auto w-full">
        {state.status === "loading" ? <LoadingSkeleton /> : null}
        {state.status === "profile_incomplete" ? <ProfileIncompleteCard missingFields={state.missingFields} /> : null}
        {state.status === "error" ? <ErrorCard message={state.message} onRetry={() => void load()} /> : null}
        {state.status === "ready" ? (
          <>
            {/* 1. Hero */}
            <HeroSection
              name={state.data.meta.name}
              ascSign={state.data.meta.ascSign}
              sunSign={state.data.highlights.find((h) => h.title === "Солнце")?.value ?? null}
              moonSign={state.data.highlights.find((h) => h.title === "Луна")?.value ?? null}
              birthCity={state.data.meta.birthCity}
            />

            {/* 2. «Это про тебя» insight */}
            <PersonalHook text={state.data.personalHook} />

            {/* 3. Compact highlights chips */}
            <HighlightsChips highlights={state.data.highlights} />

            {/* 4. Глубина расчёта */}
            <CalculationDepth stats={state.data.calculationStats} />

            {/* 5. Сферы (топ-3 по умолчанию) */}
            <SpheresStrip spheres={state.data.spheres} />

            {/* 6. Планеты (топ-3 по умолчанию) */}
            <PlanetsRow planets={state.data.planets} />

            {/* 7. Что войдёт в полный отчёт */}
            <LockedChapters chapters={state.data.chapters} />

            {/* 8. Value bullets */}
            <SalesBullets bullets={state.data.salesBullets} />

            {/* 9. CTA */}
            <CtaButton
              priceKopecks={state.data.fullReportPriceKopecks}
              onClick={handleOpenReport}
            />
          </>
        ) : null}
      </main>
    </div>
  )
}
