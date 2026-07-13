
// ############################################################################
// AI_HEADER: APP_NATAL_PREVIEW_PAGE — real natal preview route and state renderer.
// ROLE: Client Next.js page called by /readings/natal; loads the real preview contract and composes all preview states and sections.
// ############################################################################

// START_MODULE_CONTRACT: M-APP-NATAL-PREVIEW-PAGE
// purpose: Fetch and render the natal preview, including incomplete-profile, failure and ready states.
// owns:
//   - app/(grace)/readings/natal/page.tsx
// inputs: fetchNatalPreview result and retry action.
// outputs: stable natal-preview screen with loading, profile-incomplete, error or ready content.
// dependencies: React hooks; next/link; natal preview components/chart; fetchNatalPreview; NatalPreviewRead.
// side_effects: Performs preview API requests and updates React state.
// emitted_logs: none.
// invariants:
//   - data-testid=natal-preview-screen exposes data-state for every state.
//   - Ready content uses only the real typed preview response.
//   - Retry reuses the same canonical load callback.
// failure_policy: Profile/API failures become explicit accessible UI; unexpected render errors bubble to the route boundary.
// END_MODULE_CONTRACT: M-APP-NATAL-PREVIEW-PAGE

// START_MODULE_MAP: M-APP-NATAL-PREVIEW-PAGE
// public_entrypoints:
//   - NatalReadingPage (default).
// semantic_blocks:
//   - PREVIEW_LOAD: fetch and classify preview result.
//   - STATE_ATTRIBUTES: expose stable screen state contract.
//   - READY_COMPOSITION: render hero, insights, chart, spheres, planets, locked chapters and CTA.
// owned_tests:
//   - __tests__/natal/natal-component-states.test.tsx
//   - __tests__/natal/natal-no-english.test.tsx
// END_MODULE_MAP: M-APP-NATAL-PREVIEW-PAGE
"use client"

import { useCallback, useEffect, useState } from "react"
import Link from "next/link"
import { ChevronLeft } from "lucide-react"

import { NatalChartWheel } from "@/components/readings/natal-chart-wheel"
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

  const statusAttr = state.status
  const fullReportAvailable = state.status === "ready" ? String(state.data.fullReportAvailable) : undefined

  return (
    <div className="flex h-full w-full flex-col bg-background overflow-y-auto" data-testid="natal-preview-screen" data-state={statusAttr} data-full-report-available={fullReportAvailable}>
      <header
        className="flex-none px-4 pb-4 border-b border-border/40"
        style={{ paddingTop: "max(env(safe-area-inset-top), 1rem)" }}
        data-testid="natal-preview-header"
      >
        <Link
          href="/readings"
          className="inline-flex items-center gap-1.5 text-[14px] text-muted-foreground hover:text-foreground active:scale-95 transition"
          data-testid="natal-preview-back-link"
        >
          <ChevronLeft className="h-4 w-4" />
          <span>Разборы</span>
        </Link>
      </header>

      <main className="flex-1 px-5 py-6 space-y-5 max-w-md mx-auto w-full">
        {state.status === "loading" ? <div data-testid="natal-preview-loading" role="status"><LoadingSkeleton /></div> : null}
        {state.status === "profile_incomplete" ? <div data-testid="natal-profile-incomplete" role="alert"><ProfileIncompleteCard missingFields={state.missingFields} /></div> : null}
        {state.status === "error" ? <div data-testid="natal-preview-error" role="alert"><ErrorCard message={state.message} onRetry={() => void load()} /></div> : null}
        {state.status === "ready" ? (
          <div data-testid="natal-preview-content">
          <>
            {/* 1. Hero */}
            <div data-testid="natal-hero"><HeroSection
              name={state.data.meta.name}
              ascSign={state.data.meta.ascSign}
              sunSign={state.data.highlights.find((h) => h.title === "Солнце")?.value ?? null}
              moonSign={state.data.highlights.find((h) => h.title === "Луна")?.value ?? null}
              birthCity={state.data.meta.birthCity}
            /></div>

            {/* 2. «Это про тебя» insight */}
            <div data-testid="natal-personal-hook"><PersonalHook text={state.data.personalHook} /></div>

            {/* 3. Compact highlights chips */}
            <div data-testid="natal-highlights"><HighlightsChips highlights={state.data.highlights} /></div>

            {/* 4. Глубина расчёта */}
            <div data-testid="natal-calculation-depth"><CalculationDepth stats={state.data.calculationStats} /></div>

            {/* 5. Натальная карта */}
            <NatalChartWheel chart={state.data.chart} birthLabel={state.data.meta.birthDate} />

            {/* 6. Сферы (топ-3 по умолчанию) */}
            <div data-testid="natal-spheres"><SpheresStrip spheres={state.data.spheres} /></div>

            {/* 7. Планеты (топ-3 по умолчанию) */}
            <div data-testid="natal-planets"><PlanetsRow planets={state.data.planets} /></div>

            {/* 8. Что войдёт в полный отчёт */}
            <div data-testid="natal-locked-chapters"><LockedChapters chapters={state.data.chapters} /></div>

            {/* 9. Value bullets */}
            <div data-testid="natal-sales-bullets"><SalesBullets bullets={state.data.salesBullets} /></div>

            {/* 10. CTA */}
            <div data-testid="natal-full-report-cta"><CtaButton
              priceKopecks={state.data.fullReportPriceKopecks}
              disabled
            /></div>
          </>
          </div>
        ) : null}
      </main>
    </div>
  )
}
