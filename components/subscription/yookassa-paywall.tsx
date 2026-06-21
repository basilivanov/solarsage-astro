// ############################################################################
// AI_HEADER: MODULE_SUBSCRIPTION_YOOKASSA_PAYWALL
// ROLE: UI component — YooKassa payment widget integration
// DEPENDENCIES: react, @/lib/api/subscription, @/lib/log
// GRACE_ANCHORS: [YK_WIDGET_OPEN, YK_STATUS_POLL]
// SLICE: SLICE-SUBSCRIPTION
// WAVE: W-YK-1
// ############################################################################

// START_MODULE_CONTRACT
// purpose: YooKassa payment button component. Loads YooKassa Widget SDK,
//          opens checkout widget in-app (no redirect), polls subscription
//          status until payment confirmed or timeout.
// owns:
//   - components/subscription/yookassa-paywall.tsx
// inputs: Props (onSuccess, onError, productSlug, label, className)
// outputs: TSX render (button)
// dependencies: @/lib/api/subscription, @/lib/log, yookassa.js (external)
// side_effects: Network calls (startSubscription, getSubscriptionStatus)
// emitted_logs: yk_widget_open, yk_status_poll
// invariants:
//   - Widget opens in-app (no external redirect) for Telegram Mini App
//   - Polls every 3s for up to 5 minutes
//   - Disables button during loading/polling
// failure_policy: onError callback with error message
// END_MODULE_CONTRACT

"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import {
  startSubscription,
  getSubscriptionStatus,
  type SubscriptionStatusResult,
} from "@/lib/api/subscription"
import { logger } from "@/lib/log"

type Props = {
  onSuccess?: () => void
  onError?: (error: string) => void
  productSlug?: string
  label?: string
  className?: string
}

/**
 * YooKassa Paywall component.
 *
 * Uses YooKassa Checkout Widget (embedded) — opens payment form directly
 * in the Telegram Mini App without redirecting to external page.
 *
 * Flow:
 * 1. User clicks "Оформить подписку"
 * 2. POST /api/payment/subscription/start → returns confirmation_token
 * 3. Load YooKassa Widget script (yookassa.js)
 * 4. Open widget with confirmation_token
 * 5. User fills card details in widget
 * 6. YooKassa sends webhook → backend activates subscription
 * 7. Frontend polls /api/payment/subscription/status every 3s
 * 8. When hasAccess=true → onSuccess callback
 */
export function YookassaPaywall({
  onSuccess,
  onError,
  productSlug = "subscription_month",
  label = "Оформить подписку · 199 ₽/мес",
  className,
}: Props) {
  const [loading, setLoading] = useState(false)
  const [polling, setPolling] = useState(false)
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Load YooKassa Widget script once
  useEffect(() => {
    if (typeof window === "undefined") return
    if ((window as any).YooKassaCheckout) return

    const script = document.createElement("script")
    script.src = "https://yookassa.ru/checkout/widget/v1/checkout.js"
    script.async = true
    script.onload = () => {
      logger.info("[YooKassa] Widget script loaded")
    }
    script.onerror = () => {
      logger.error("[YooKassa] Failed to load widget script")
    }
    document.head.appendChild(script)

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current)
    }
  }, [])

  const pollStatus = useCallback(async () => {
    try {
      const status: SubscriptionStatusResult = await getSubscriptionStatus()
      if (status.hasAccess) {
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
        if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current)
        setPolling(false)
        setLoading(false)
        onSuccess?.()
        return
      }
      if (status.status === "none" || status.status === "expired") {
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
        if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current)
        setPolling(false)
        setLoading(false)
      }
    } catch {
      // Ignore poll errors
    }
  }, [onSuccess])

  const handleSubscribe = async () => {
    setLoading(true)
    try {
      const result = await startSubscription(productSlug)

      // Try Widget first (best for Telegram Mini App — stays in-app)
      if (result.confirmationToken && (window as any).YooKassaCheckout) {
        const checkout = new (window as any).YooKassaCheckout({
          confirmation_token: result.confirmationToken,
          return_url: window.location.origin + "/profile",
          error_callback: (error: Error) => {
            onError?.(error.message)
            setLoading(false)
          },
        })
        checkout.open()
      } else if (result.confirmationUrl) {
        // Fallback: redirect (less ideal for Mini App, but works)
        window.open(result.confirmationUrl, "_blank")
      } else {
        onError?.("No confirmation method available")
        setLoading(false)
        return
      }

      // Start polling for status (webhook may arrive before user returns)
      setPolling(true)
      pollIntervalRef.current = setInterval(pollStatus, 3000)

      // Timeout after 5 minutes
      pollTimeoutRef.current = setTimeout(() => {
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
        setPolling(false)
        setLoading(false)
        onError?.("Payment timeout — please try again")
      }, 5 * 60 * 1000)
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Ошибка оплаты"
      onError?.(message)
      setLoading(false)
    }
  }

  const buttonLabel = polling
    ? "Проверяем оплату..."
    : loading
      ? "Перенаправляем..."
      : label

  return (
    <button
      type="button"
      onClick={handleSubscribe}
      disabled={loading || polling}
      data-testid="yookassa-paywall-button"
      className={
        className ||
        "inline-flex h-11 items-center justify-center gap-2 rounded-full bg-foreground px-5 text-[13px] font-medium text-background transition active:scale-[0.99] disabled:opacity-50"
      }
    >
      {buttonLabel}
    </button>
  )
}
