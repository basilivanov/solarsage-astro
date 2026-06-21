// ############################################################################
// AI_HEADER: MODULE_API_SUBSCRIPTION
// ROLE: Lib — subscription.ts (API фасад для payment/subscription endpoints)
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-FRONTEND-API-FACADES
// WAVE: W-YK-1
// ############################################################################

// START_MODULE_CONTRACT
// purpose: API client for payment and subscription endpoints.
//          Wraps fetch calls to /api/payment/* with proper error handling.
// owns:
//   - lib/api/subscription.ts
// inputs: Function args (productSlug, reason)
// outputs: Typed responses (SubscriptionStartResult, SubscriptionStatusResult, etc.)
// dependencies: local modules
// side_effects: Network calls to API
// emitted_logs: n/a (pure)
// invariants:
//   - All requests include credentials: "include" for session cookie
//   - Errors thrown as SubscriptionError with code field
// failure_policy: throw SubscriptionError on non-2xx
// END_MODULE_CONTRACT

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

export interface SubscriptionStartResult {
  subscriptionId: string
  productSlug: string
  providerPaymentId: string
  confirmationToken: string | null
  confirmationUrl: string | null
  status: string
}

export interface SubscriptionStatusResult {
  subscriptionId: string | null
  productSlug: string | null
  status: "none" | "pending" | "active" | "past_due" | "canceled" | "expired"
  priceKopecks: number
  currency: string
  currentPeriodStart: string | null
  currentPeriodEnd: string | null
  nextChargeAt: string | null
  hasAccess: boolean
  accessUntil: string | null
}

export interface PurchaseStartResult {
  purchaseId: string | null
  productSlug: string
  providerPaymentId: string
  confirmationToken: string | null
  confirmationUrl: string | null
  status: string
}

export interface ProductRead {
  slug: string
  name: string
  description: string | null
  productType: "subscription_recurrent" | "one_time"
  priceKopecks: number
  currency: string
  periodDays: number | null
  horaryQuota: number | null
}

export class SubscriptionError extends Error {
  constructor(message: string, public code?: string) {
    super(message)
    this.name = "SubscriptionError"
  }
}

export async function startSubscription(productSlug: string = "subscription_month"): Promise<SubscriptionStartResult> {
  const res = await fetch(`${API_BASE}/api/payment/subscription/start`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ productSlug }),
  })
  if (res.status === 409) throw new SubscriptionError("Subscription already active", "ALREADY_ACTIVE")
  if (res.status === 503) throw new SubscriptionError("Payments are not available", "PAYMENTS_DISABLED")
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new SubscriptionError(body.detail || "Failed to start subscription", "START_FAILED")
  }
  return res.json()
}

export async function startPurchase(productSlug: string): Promise<PurchaseStartResult> {
  const res = await fetch(`${API_BASE}/api/payment/purchase/start`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ productSlug }),
  })
  if (res.status === 503) throw new SubscriptionError("Payments are not available", "PAYMENTS_DISABLED")
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new SubscriptionError(body.detail || "Failed to start purchase", "PURCHASE_FAILED")
  }
  return res.json()
}

export async function getSubscriptionStatus(): Promise<SubscriptionStatusResult> {
  const res = await fetch(`${API_BASE}/api/payment/subscription/status`, {
    credentials: "include",
  })
  if (!res.ok) throw new SubscriptionError("Failed to get subscription status", "STATUS_FAILED")
  return res.json()
}

export async function cancelSubscription(reason?: string): Promise<{ subscriptionId: string | null; status: string }> {
  const res = await fetch(`${API_BASE}/api/payment/subscription/cancel`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason: reason || null }),
  })
  if (!res.ok) throw new SubscriptionError("Failed to cancel subscription", "CANCEL_FAILED")
  return res.json()
}

export async function getProducts(): Promise<ProductRead[]> {
  const res = await fetch(`${API_BASE}/api/payment/products`, {
    credentials: "include",
  })
  if (!res.ok) throw new SubscriptionError("Failed to get products", "PRODUCTS_FAILED")
  const data = await res.json()
  return data.products
}
