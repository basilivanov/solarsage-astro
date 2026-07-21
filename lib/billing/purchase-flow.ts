
// ############################################################################
// AI_HEADER: FRONTEND_BILLING_PURCHASE_FLOW — provider redirect + status polling.
// ROLE: Telegram-safe open of the YooKassa confirmation_url and bounded
//       authenticated polling of local status endpoints after the user
//       returns. A return from the provider page is NEVER treated as success:
//       only the authenticated status endpoints decide.
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-BILLING-PURCHASE-FLOW
// purpose: Shared primitives for all billing UX flows: open the provider
//   checkout in a Telegram-safe way and poll authenticated local status with
//   bounded backoff until a terminal state or timeout.
// owns:
//   - lib/billing/purchase-flow.ts
// inputs: confirmation url, purchase id, poll options.
// outputs: terminal PurchaseStatusResponse / SubscriptionStatusResponse;
//   PurchasePollTimeoutError on timeout.
// dependencies: lib/api/payment typed client; Telegram WebApp (optional).
// side_effects: opens an external URL; credentialed status GETs.
// emitted_logs: none.
// invariants:
//   - openProviderCheckout never navigates the mini-app itself away: it
//     prefers Telegram openLink and falls back to window.open(_blank).
//   - Polling uses ONLY authenticated local endpoints (no provider calls).
//   - Backoff is bounded (start <= interval <= max, total <= timeout).
//   - Polling stops on any terminal status or timeout, never runs forever.
// failure_policy: PurchasePollTimeoutError on timeout; PaymentApiError and
//   network errors propagate to the caller.
// END_MODULE_CONTRACT: M-FRONTEND-BILLING-PURCHASE-FLOW

// START_MODULE_MAP: M-FRONTEND-BILLING-PURCHASE-FLOW
// public_entrypoints:
//   - openProviderCheckout
//   - pollPurchaseStatus
//   - pollSubscriptionStatus
//   - PurchasePollTimeoutError
// semantic_blocks:
//   - PROVIDER_REDIRECT: Telegram-safe external open.
//   - POLL: bounded backoff loops for purchase/subscription status.
// owned_tests:
//   - __tests__/billing/purchase-flow.test.ts
// END_MODULE_MAP: M-FRONTEND-BILLING-PURCHASE-FLOW

import {
  getPurchaseStatus,
  getSubscriptionStatus,
} from "@/lib/api/payment"
import type {
  PurchaseStatusResponse,
  SubscriptionStatusResponse,
} from "@/packages/contracts"

// START_BLOCK: PROVIDER_REDIRECT
export function openProviderCheckout(url: string): void {
  // Mirror of the share-invite fallback chain: Telegram-native open first,
  // plain browser fallback otherwise. The mini-app page must stay loaded so
  // polling can continue when the user comes back.
  try {
    const tg = typeof window !== "undefined" ? window.Telegram?.WebApp : undefined
    if (tg?.openLink) {
      tg.openLink(url)
      return
    }
  } catch {
    // fall through to the browser fallback
  }
  if (typeof window !== "undefined") {
    window.open(url, "_blank", "noopener,noreferrer")
  }
}
// END_BLOCK: PROVIDER_REDIRECT

// START_BLOCK: POLL
export class PurchasePollTimeoutError extends Error {
  constructor(message: string) {
    super(message)
    this.name = "PurchasePollTimeoutError"
  }
}

export type PollOptions = {
  intervalMs?: number
  maxIntervalMs?: number
  timeoutMs?: number
  sleep?: (ms: number) => Promise<void>
}

const TERMINAL_PURCHASE_STATUSES = new Set(["succeeded", "consumed", "delivered", "canceled", "failed"])

const defaultSleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

async function pollWithBackoff<T>(
  read: () => Promise<T>,
  isTerminal: (value: T) => boolean,
  options: PollOptions,
  timeoutMessage: string
): Promise<T> {
  const intervalMs = options.intervalMs ?? 2000
  const maxIntervalMs = options.maxIntervalMs ?? 5000
  const timeoutMs = options.timeoutMs ?? 5 * 60 * 1000
  const sleep = options.sleep ?? defaultSleep

  const startedAt = Date.now()
  let delay = intervalMs
  for (;;) {
    const value = await read()
    if (isTerminal(value)) {
      return value
    }
    if (Date.now() - startedAt >= timeoutMs) {
      throw new PurchasePollTimeoutError(timeoutMessage)
    }
    await sleep(delay)
    delay = Math.min(maxIntervalMs, Math.round(delay * 1.25))
  }
}

export function pollPurchaseStatus(
  purchaseId: string,
  options: PollOptions = {}
): Promise<PurchaseStatusResponse> {
  return pollWithBackoff(
    () => getPurchaseStatus(purchaseId),
    (status) => TERMINAL_PURCHASE_STATUSES.has(status.status),
    options,
    "Оплата не подтвердилась вовремя. Если деньги списались, статус обновится автоматически."
  )
}

export function pollSubscriptionStatus(
  options: PollOptions = {}
): Promise<SubscriptionStatusResponse> {
  return pollWithBackoff(
    () => getSubscriptionStatus(),
    (status) => status.hasAccess === true || status.status === "active",
    options,
    "Подписка не подтвердилась вовремя. Если деньги списались, статус обновится автоматически."
  )
}
// END_BLOCK: POLL
