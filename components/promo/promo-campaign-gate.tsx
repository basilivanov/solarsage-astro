// ############################################################################
// AI_HEADER: MODULE_PROMO_CAMPAIGN_GATE
// ROLE: Authenticated state machine and gate for promo campaign preview and redemption.
// DEPENDENCIES: react, next/navigation, lib/telegram/start-param, lib/api/promo, lib/log, components/promo/promo-confirmation-sheet
// GRACE_ANCHORS: [PROMO_CAMPAIGN_GATE]
// WAVE: W-NAMED-PROMO-CAMPAIGN
// ############################################################################

// START_MODULE_CONTRACT: M-PROMO-CAMPAIGN-GATE
// purpose: Manage authenticated promo state machine (preview, onboarding redirect, redemption, recovery, and single completed reload) without leaking pending tokens.
// owns:
//   - components/promo/promo-campaign-gate.tsx
// inputs: none (reads pathname via usePathname and pending promo token from sessionStorage)
// outputs:
//   - PromoCampaignGate React component
// dependencies:
//   - M-TELEGRAM-START-PARAM (getPendingPromoToken, clearPendingPromoToken)
//   - M-FRONTEND-API-PROMO (previewPromo, redeemPromo, PromoApiError)
//   - M-PROMO-CONFIRMATION-SHEET (PromoConfirmationSheet)
//   - M-LOG-FRONTEND (logEvent, captureFrontendError)
// side_effects:
//   - reads/clears sessionStorage for pending promo token
//   - triggers navigation to /onboarding?requiredFor=...
//   - triggers window.location.reload() on completed redemption
//   - emits promo.offer_viewed log event
// invariants:
//   - raw token is never stored in React state, props, DOM attributes, or error objects
//   - preview and sheet are suppressed while pathname starts with /onboarding
//   - completed refresh executes exactly once without reload loops
//   - storage failures fail closed without crashing app shell
// failure_policy: fail closed on storage or unexpected exceptions, log safe error, and suppress sheet
// END_MODULE_CONTRACT: M-PROMO-CAMPAIGN-GATE

// START_MODULE_MAP: M-PROMO-CAMPAIGN-GATE
// public_entrypoints:
//   - PromoCampaignGate
// semantic_blocks:
//   - GATE_COMPONENT: PromoCampaignGate state machine component
// owned_tests:
//   - __tests__/components/PromoCampaignGate.test.tsx
// END_MODULE_MAP: M-PROMO-CAMPAIGN-GATE

"use client"

import * as React from "react"
import { usePathname, useRouter } from "next/navigation"
import type { PromoOffer } from "@/packages/contracts"
import { getPendingPromoToken, clearPendingPromoToken } from "@/lib/telegram/start-param"
import { previewPromo, redeemPromo, PromoApiError } from "@/lib/api/promo"
import { PromoConfirmationSheet } from "@/components/promo/promo-confirmation-sheet"
import { logEvent } from "@/lib/log"
import { captureFrontendError } from "@/lib/log/capture-error"

export function PromoCampaignGate() {
  // START_FUNCTION_CONTRACT: F-M-PROMO-CAMPAIGN-GATE.PromoCampaignGate
  // purpose: Authenticated promo gate component managing preview, onboarding redirect, redemption, and reload.
  // inputs: none
  // returns: JSX.Element | null
  // side_effects: preview/redeem API calls, navigation, window.location.reload, log events
  // emitted_logs: promo.offer_viewed, frontend.flow_failed
  // error_behavior: catches errors, fails closed on unrecoverable failures
  // END_FUNCTION_CONTRACT: F-M-PROMO-CAMPAIGN-GATE.PromoCampaignGate

  const pathname = usePathname()
  const router = useRouter()

  const [offer, setOffer] = React.useState<PromoOffer | null>(null)
  const [phase, setPhase] = React.useState<"idle" | "resolving" | "ready" | "redeeming" | "error" | "success">("idle")
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null)
  const [isRetryable, setIsRetryable] = React.useState<boolean>(true)

  const hasReloadedRef = React.useRef(false)
  const hasLoggedViewRef = React.useRef<string | null>(null)

  const triggerCompletedRefresh = React.useCallback(() => {
    clearPendingPromoToken()
    setOffer(null)
    setPhase("idle")
    if (hasReloadedRef.current) return
    hasReloadedRef.current = true
    if (typeof window !== "undefined" && window.location) {
      window.location.reload()
    }
  }, [])

  const runPreview = React.useCallback(async () => {
    let token: string | null = null
    try {
      token = getPendingPromoToken()
    } catch (storageErr) {
      captureFrontendError(storageErr, {
        operation: "promo.intent_store",
        reasonCode: "STORAGE_UNAVAILABLE",
      })
      setPhase("idle")
      return
    }

    if (!token) {
      setPhase("idle")
      setOffer(null)
      return
    }

    setPhase("resolving")
    setErrorMessage(null)

    try {
      const res = await previewPromo(token)
      if (!res.profileComplete) {
        // Retain token in sessionStorage, redirect to onboarding
        setPhase("idle")
        setOffer(null)
        const requiredFor = res.offer.unlockNatal ? "promoNatal" : "promoBase"
        router.push(`/onboarding?requiredFor=${requiredFor}`)
        return
      }

      setOffer(res.offer)
      setPhase("ready")

      // Emit promo.offer_viewed once per offer display_name
      if (hasLoggedViewRef.current !== res.offer.displayName) {
        hasLoggedViewRef.current = res.offer.displayName
        logEvent("promo.offer_viewed", {
          slice: "W-NAMED-PROMO-CAMPAIGN",
          module: "M-PROMO-CAMPAIGN-GATE",
          block: "PREVIEW",
          payload: {
            access_days: res.offer.accessDays,
            bonus_credits: res.offer.bonusCredits,
            unlock_natal: res.offer.unlockNatal,
          },
        })
      }
    } catch (err) {
      if (err instanceof PromoApiError) {
        if (err.code === "ALREADY_REDEEMED") {
          triggerCompletedRefresh()
          return
        }
        if (
          err.code === "INVALID_CODE" ||
          err.code === "CAMPAIGN_EXPIRED" ||
          err.code === "CAMPAIGN_FULL"
        ) {
          clearPendingPromoToken()
          setPhase("idle")
          setOffer(null)
          return
        }
        // Network, rate limit, 5xx
        setPhase("error")
        setErrorMessage(err.message)
        setIsRetryable(true)
        return
      }

      // Network exception
      setPhase("error")
      setErrorMessage("Ошибка подключения к сети.")
      setIsRetryable(true)
    }
  }, [router, triggerCompletedRefresh])

  const handleActivate = React.useCallback(async () => {
    let token: string | null = null
    try {
      token = getPendingPromoToken()
    } catch {
      setPhase("idle")
      return
    }

    if (!token) {
      setPhase("idle")
      setOffer(null)
      return
    }

    setPhase("redeeming")
    setErrorMessage(null)

    try {
      await redeemPromo(token)
      triggerCompletedRefresh()
    } catch (err) {
      if (err instanceof PromoApiError) {
        if (err.code === "ALREADY_REDEEMED") {
          triggerCompletedRefresh()
          return
        }
        if (err.code === "PROFILE_INCOMPLETE") {
          // Retain token in sessionStorage, redirect to onboarding
          setPhase("idle")
          setOffer(null)
          const requiredFor = offer?.unlockNatal ? "promoNatal" : "promoBase"
          router.push(`/onboarding?requiredFor=${requiredFor}`)
          return
        }
        if (
          err.code === "INVALID_CODE" ||
          err.code === "CAMPAIGN_EXPIRED" ||
          err.code === "CAMPAIGN_FULL"
        ) {
          clearPendingPromoToken()
          setPhase("error")
          setErrorMessage(err.message)
          setIsRetryable(false)
          return
        }
        // Rate limit, network, 5xx
        setPhase("error")
        setErrorMessage(err.message)
        setIsRetryable(true)
        return
      }

      setPhase("error")
      setErrorMessage("Ошибка подключения к сети.")
      setIsRetryable(true)
    }
  }, [offer, router, triggerCompletedRefresh])

  const handleDismiss = React.useCallback(() => {
    clearPendingPromoToken()
    setOffer(null)
    setPhase("idle")
    setErrorMessage(null)
  }, [])

  const handleRetry = React.useCallback(() => {
    if (offer) {
      handleActivate()
    } else {
      runPreview()
    }
  }, [handleActivate, offer, runPreview])

  // Trigger preview on mount or when pathname changes away from /onboarding
  React.useEffect(() => {
    if (pathname?.startsWith("/onboarding")) {
      return
    }
    runPreview()
  }, [pathname, runPreview])

  if (pathname?.startsWith("/onboarding")) {
    return null
  }

  if (!offer || phase === "idle" || phase === "resolving") {
    return null
  }

  return (
    <PromoConfirmationSheet
      offer={offer}
      phase={phase}
      errorMessage={errorMessage}
      onActivate={handleActivate}
      onDismiss={handleDismiss}
      onRetry={isRetryable ? handleRetry : undefined}
    />
  )
}
