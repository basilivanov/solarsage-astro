
// ############################################################################
// AI_HEADER: FRONTEND_HOOK_USE_SUBSCRIPTION_PURCHASE — subscription purchase flow.
// ROLE: Shared hook for the subscription UX (profile access card, paywall):
//       loads the catalog (prices only from the API), starts the recurrent
//       payment, opens the provider checkout Telegram-safe and polls the
//       authenticated local status until the subscription is active.
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-HOOK-USE-SUBSCRIPTION-PURCHASE
// purpose: One canonical client flow for buying/canceling a subscription.
//   A return from the provider page is never success: only the authenticated
//   /api/payment/subscription/status poll decides.
// owns:
//   - lib/hooks/use-subscription-purchase.ts
// inputs: onActivated callback (access refresh of the caller).
// outputs: products (month/year), phase, errorMessage, buy/cancel actions,
//   statusRevision (bumps on successful buy/cancel for status re-reads).
// dependencies: lib/api/payment, lib/billing/purchase-flow.
// side_effects: credentialed API calls; opens provider checkout.
// emitted_logs: none.
// invariants:
//   - Prices come only from GET /api/payment/products.
//   - unavailable=true means billing is off (503) or the catalog failed —
//     UI must show an honest disabled state, never a fake price.
//   - The flow never marks success without a confirmed active status.
// failure_policy: phase=error with a Russian message on any failure/timeout.
// END_MODULE_CONTRACT: M-FRONTEND-HOOK-USE-SUBSCRIPTION-PURCHASE

// START_MODULE_MAP: M-FRONTEND-HOOK-USE-SUBSCRIPTION-PURCHASE
// public_entrypoints:
//   - useSubscriptionPurchase
// semantic_blocks:
//   - CATALOG_LOAD: products fetch with unavailable fallback.
//   - BUY: start -> provider checkout -> bounded status poll.
//   - CANCEL: cancel subscription (paid period is kept server-side).
//   - REVISION: statusRevision increments on successful buy/cancel so
//     consumers re-read SubscriptionStatusResponse (flags never go stale).
// owned_tests:
//   - __tests__/billing/use-subscription-purchase.test.tsx
// END_MODULE_MAP: M-FRONTEND-HOOK-USE-SUBSCRIPTION-PURCHASE
"use client"

import { useCallback, useEffect, useRef, useState } from "react"

import {
  cancelSubscription,
  getPaymentProducts,
  paymentErrorMessage,
  startSubscription,
} from "@/lib/api/payment"
import {
  PurchasePollTimeoutError,
  SubscriptionTerminalError,
  openProviderCheckout,
  pollSubscriptionStatus,
} from "@/lib/billing/purchase-flow"
import type { ProductRead } from "@/packages/contracts"

export type SubscriptionPurchasePhase = "idle" | "starting" | "waiting" | "success" | "error"
export type SubscriptionSlug = "subscription_month" | "subscription_year"

// START_BLOCK: CATALOG_LOAD
export function useSubscriptionPurchase(onActivated?: () => void) {
  const [products, setProducts] = useState<ProductRead[] | null>(null)
  const [unavailable, setUnavailable] = useState(false)
  const [phase, setPhase] = useState<SubscriptionPurchasePhase>("idle")
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  // Bumped on every SUCCESSFUL buy/cancel: consumers re-read the subscription
  // status instead of trusting stale renewing/cancelable flags. Failures
  // never bump it.
  const [statusRevision, setStatusRevision] = useState(0)
  const mountedRef = useRef(true)
  const onActivatedRef = useRef(onActivated)
  onActivatedRef.current = onActivated

  useEffect(() => {
    mountedRef.current = true
    getPaymentProducts()
      .then((res) => {
        if (mountedRef.current) setProducts(res.products)
      })
      .catch(() => {
        if (mountedRef.current) setUnavailable(true)
      })
    return () => {
      mountedRef.current = false
    }
  }, [])
  // END_BLOCK: CATALOG_LOAD

  // START_BLOCK: BUY
  const buy = useCallback(async (slug: SubscriptionSlug) => {
    setPhase("starting")
    setErrorMessage(null)
    try {
      const started = await startSubscription(slug)
      if (started.confirmationUrl) {
        openProviderCheckout(started.confirmationUrl)
      }
      setPhase("waiting")
      // STRICT: success only when THIS subscriptionId reaches active.
      await pollSubscriptionStatus(started.subscriptionId)
      if (!mountedRef.current) return
      setPhase("success")
      setStatusRevision((v) => v + 1)
      onActivatedRef.current?.()
    } catch (error) {
      if (!mountedRef.current) return
      setPhase("error")
      if (error instanceof PurchasePollTimeoutError || error instanceof SubscriptionTerminalError) {
        setErrorMessage(error.message)
      } else {
        setErrorMessage(paymentErrorMessage(error))
      }
    }
  }, [])
  // END_BLOCK: BUY

  // START_BLOCK: CANCEL
  const cancel = useCallback(async () => {
    setErrorMessage(null)
    try {
      await cancelSubscription()
      setStatusRevision((v) => v + 1)
      onActivatedRef.current?.()
    } catch (error) {
      if (!mountedRef.current) return
      setErrorMessage(paymentErrorMessage(error))
    }
  }, [])
  // END_BLOCK: CANCEL

  const month = products?.find((p) => p.slug === "subscription_month") ?? null
  const year = products?.find((p) => p.slug === "subscription_year") ?? null
  return { phase, errorMessage, buy, cancel, month, year, unavailable, ready: products !== null, statusRevision }
}

export function formatPriceRubles(kopecks: number): string {
  return String(Math.round(kopecks / 100))
}
