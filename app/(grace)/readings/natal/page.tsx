"use client"

import { useCallback, useEffect, useState } from "react"

import { CalculationDepth } from "@/components/readings/natal-preview/calculation-depth"
import { CtaButton } from "@/components/readings/natal-preview/cta-button"
import { ErrorCard } from "@/components/readings/natal-preview/error-card"
import { HeroSection } from "@/components/readings/natal-preview/hero-section"
import { HighlightsStrip } from "@/components/readings/natal-preview/highlights-strip"
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

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-[480px] flex-col gap-4 px-4 py-5" style={{ paddingTop: "max(env(safe-area-inset-top), 1.25rem)" }}>
      {state.status === "loading" ? <LoadingSkeleton /> : null}
      {state.status === "profile_incomplete" ? <ProfileIncompleteCard missingFields={state.missingFields} /> : null}
      {state.status === "error" ? <ErrorCard message={state.message} onRetry={() => void load()} /> : null}
      {state.status === "ready" ? (
        <>
          <HeroSection
            name={state.data.meta.name}
            ascSign={state.data.meta.ascSign}
            birthCity={state.data.meta.birthCity}
            gender={state.data.meta.gender}
          />
          <HighlightsStrip highlights={state.data.highlights} />
          <PersonalHook text={state.data.personalHook} />
          <CalculationDepth stats={state.data.calculationStats} />
          <SpheresStrip spheres={state.data.spheres} />
          <PlanetsRow planets={state.data.planets} />
          <LockedChapters chapters={state.data.chapters} />
          <SalesBullets bullets={state.data.salesBullets} />
          <CtaButton
            priceKopecks={state.data.fullReportPriceKopecks}
            disabled
            onClick={() => undefined}
          />
        </>
      ) : null}
    </main>
  )
}
