// ############################################################################
// AI_HEADER: MODULE_LOG_SHIPPER
// ROLE: Frontend log shipper — batches and ships logs to backend with exponential backoff & jitter.
// DEPENDENCIES: fetch API
// GRACE_ANCHORS: [LOG_SHIPPER, BATCH_FLUSH]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-LOG-SHIPPER
// purpose: Batch frontend log envelopes and ship to POST /api/_log with
//   scheduled retries, exponential backoff, jitter, bounded notBefore scheduling, unload sendBeacon/fetch fallback, and max attempts.
// owns:
//   - lib/log/shipper.ts
// inputs:
//   - CanonEnvelope (canonical envelope per §8.2)
//   - NEXT_PUBLIC_GRACE_LOG_SHIPPING env var (on/off)
// outputs:
//   - POST /api/_log requests with batched envelopes
// dependencies:
//   - fetch API (browser/Node.js)
// side_effects:
//   - network requests to backend
//   - schedules retry timers
// invariants:
//   - batches by 50 envelopes OR 5s, whichever first
//   - retryable: network error, 429, 5xx -> requeue with exponential backoff + jitter up to 30s max, max 5 attempts
//   - non-retryable 4xx (except 429) -> drop immediately
//   - bounded notBefore: delayed retries cannot be pulled early by fresh events or 5s timers
//   - unload fallback: sendBeacon false/throw falls back to keepalive fetch with credentials
//   - serialization failure or synchronous unload transport failure preserves batch in buffer
//   - kill-switch: GRACE_LOG_SHIPPING=off disables all shipping
// failure_policy:
//   - shipper errors handled internally without console/logging recursion or application throws
// END_MODULE_CONTRACT: M-LOG-SHIPPER

// START_MODULE_MAP: M-LOG-SHIPPER
// public_entrypoints:
//   - LogShipper
//   - getLogShipper
//   - resetLogShipperForTests
// semantic_blocks:
//   - LOG_SHIPPER: LogShipper class definition and methods.
//   - BATCH_FLUSH: singleton manager and test reset.
// owned_tests:
//   - __tests__/lib/log-shipper.test.ts
// END_MODULE_MAP: M-LOG-SHIPPER

// START_BLOCK: LOG_SHIPPER
export interface CanonEnvelope {
  ts: string
  level: string
  env: string
  service: string
  service_version: string
  slice: string
  module: string
  block: string
  event: string
  correlation_id: string
  msg?: string
  session_id?: string
  user_id_hash?: string
  payload?: Record<string, unknown>
  error?: Record<string, unknown>
  duration_ms?: number
  http?: Record<string, unknown>
  operation_id?: string
  phase?: string
}

export type TrackedEnvelope = {
  envelope: CanonEnvelope
  attempt: number
  notBefore: number
}

export class LogShipper {
  private buffer: TrackedEnvelope[] = []
  private timer: ReturnType<typeof setTimeout> | null = null
  private retryTimer: ReturnType<typeof setTimeout> | null = null
  private readonly maxBatchSize = 50
  private readonly maxWaitMs = 5000
  private readonly maxAttempts = 5
  private readonly baseBackoffMs = 1000
  private readonly maxBackoffMs = 30000
  private readonly endpoint = "/api/_log"
  private flushing = false
  private beforeUnloadHandler: (() => void) | null = null
  private pageHideHandler: (() => void) | null = null

  // START_FUNCTION_CONTRACT: F-M-LOG-SHIPPER.LogShipper.constructor
  // purpose: Initialize LogShipper and attach unload listeners if in browser.
  // inputs: enabled - boolean flag
  // returns: LogShipper instance
  // side_effects: adds window beforeunload and pagehide listeners
  // emitted_logs: none.
  // error_behavior: none.
  // END_FUNCTION_CONTRACT: F-M-LOG-SHIPPER.LogShipper.constructor
  constructor(private enabled: boolean) {
    if (typeof window !== "undefined") {
      this.beforeUnloadHandler = () => this.flushSync()
      this.pageHideHandler = () => this.flushSync()
      window.addEventListener("beforeunload", this.beforeUnloadHandler)
      window.addEventListener("pagehide", this.pageHideHandler)
    }
  }

  // START_FUNCTION_CONTRACT: F-M-LOG-SHIPPER.LogShipper.destroy
  // purpose: Clear timers, remove window listeners, and reset buffer.
  // inputs: none
  // returns: void
  // side_effects: removes window event listeners and clears active timers
  // emitted_logs: none.
  // error_behavior: none.
  // END_FUNCTION_CONTRACT: F-M-LOG-SHIPPER.LogShipper.destroy
  destroy(): void {
    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
    }
    if (this.retryTimer) {
      clearTimeout(this.retryTimer)
      this.retryTimer = null
    }
    if (typeof window !== "undefined") {
      if (this.beforeUnloadHandler) {
        window.removeEventListener("beforeunload", this.beforeUnloadHandler)
        this.beforeUnloadHandler = null
      }
      if (this.pageHideHandler) {
        window.removeEventListener("pagehide", this.pageHideHandler)
        this.pageHideHandler = null
      }
    }
    this.buffer = []
    this.flushing = false
  }

  // START_FUNCTION_CONTRACT: F-M-LOG-SHIPPER.LogShipper.enqueue
  // purpose: Enqueue a log envelope for shipping.
  // inputs: envelope - CanonEnvelope object
  // returns: void
  // side_effects: pushes item to buffer, triggers flush or schedules timer
  // emitted_logs: none.
  // error_behavior: disabled or debug/batch flush scheduled safely.
  // END_FUNCTION_CONTRACT: F-M-LOG-SHIPPER.LogShipper.enqueue
  enqueue(envelope: CanonEnvelope): void {
    if (!this.enabled) return

    this.buffer.push({ envelope, attempt: 1, notBefore: 0 })

    if (process.env.NEXT_PUBLIC_LOG_LEVEL === "debug") {
      void this.flush()
      return
    }

    const now = Date.now()
    const eligibleCount = this.buffer.filter((item) => item.notBefore <= now).length

    if (eligibleCount >= this.maxBatchSize) {
      void this.flush()
      return
    }

    this.scheduleNextWork()
  }

  // START_FUNCTION_CONTRACT: F-M-LOG-SHIPPER.LogShipper.calculateBackoff
  // purpose: Compute exponential backoff delay with bounded ±20% jitter.
  // inputs: attempt - attempt number, randomValue - optional random float [0,1]
  // returns: number delay in ms
  // side_effects: none
  // emitted_logs: none.
  // error_behavior: none.
  // END_FUNCTION_CONTRACT: F-M-LOG-SHIPPER.LogShipper.calculateBackoff
  calculateBackoff(attempt: number, randomValue = Math.random()): number {
    const exp = Math.min(this.maxBackoffMs, this.baseBackoffMs * Math.pow(2, Math.max(0, attempt - 1)))
    const clampedRandom = Math.max(0, Math.min(1, randomValue))
    const jitter = exp * 0.2 * (clampedRandom * 2 - 1)
    return Math.max(100, Math.min(this.maxBackoffMs, Math.round(exp + jitter)))
  }

  private scheduleNextWork(): void {
    if (this.flushing || !this.enabled) return

    const now = Date.now()
    const eligible = this.buffer.filter((item) => item.notBefore <= now)

    if (eligible.length >= this.maxBatchSize) {
      void this.flush()
      return
    }

    if (eligible.length > 0 && !this.timer) {
      this.timer = setTimeout(() => {
        this.timer = null
        void this.flush()
      }, this.maxWaitMs)
    }

    const delayedItems = this.buffer.filter((item) => item.notBefore > now)
    if (delayedItems.length > 0) {
      const earliest = Math.min(...delayedItems.map((item) => item.notBefore))
      const delay = Math.max(0, earliest - now)

      if (this.retryTimer) {
        clearTimeout(this.retryTimer)
        this.retryTimer = null
      }

      this.retryTimer = setTimeout(() => {
        this.retryTimer = null
        void this.flush()
      }, delay)
    }
  }

  // START_FUNCTION_CONTRACT: F-M-LOG-SHIPPER.LogShipper.flush
  // purpose: Asynchronously flush eligible envelopes to POST /api/_log.
  // inputs: none
  // returns: Promise<void>
  // side_effects: network fetch call, buffer modification
  // emitted_logs: none.
  // error_behavior: transient network/429/5xx errors trigger requeue with backoff up to 5 attempts; 4xx non-429 dropped.
  // END_FUNCTION_CONTRACT: F-M-LOG-SHIPPER.LogShipper.flush
  async flush(): Promise<void> {
    if (!this.enabled || this.flushing) return

    const now = Date.now()
    const eligibleIndices: number[] = []

    for (let i = 0; i < this.buffer.length; i++) {
      if (this.buffer[i].notBefore <= now) {
        eligibleIndices.push(i)
        if (eligibleIndices.length >= this.maxBatchSize) break
      }
    }

    if (eligibleIndices.length === 0) {
      this.scheduleNextWork()
      return
    }

    this.flushing = true

    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
    }

    // Extract eligible items from buffer preserving relative order
    const batchTracked: TrackedEnvelope[] = []
    eligibleIndices.sort((a, b) => a - b)
    for (let i = eligibleIndices.length - 1; i >= 0; i--) {
      const [item] = this.buffer.splice(eligibleIndices[i], 1)
      batchTracked.unshift(item)
    }

    const envelopesPayload = batchTracked.map((item) => item.envelope)

    let response: Response | null = null
    let networkError = false

    try {
      response = await fetch(this.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ envelopes: envelopesPayload }),
        credentials: "include",
      })
    } catch {
      networkError = true
    }

    if (response?.ok) {
      this.flushing = false
      this.scheduleNextWork()
      return
    }

    const isRetryable = networkError || (response && (response.status === 429 || response.status >= 500))

    if (isRetryable) {
      const requeued: TrackedEnvelope[] = []
      const failNow = Date.now()

      for (const item of batchTracked) {
        const nextAttempt = item.attempt + 1
        if (nextAttempt <= this.maxAttempts) {
          const delay = this.calculateBackoff(item.attempt)
          requeued.push({
            envelope: item.envelope,
            attempt: nextAttempt,
            notBefore: failNow + delay,
          })
        }
      }

      if (requeued.length > 0) {
        this.buffer.push(...requeued)
      }
    }

    this.flushing = false
    this.scheduleNextWork()
  }

  private flushSync(): void {
    if (!this.enabled || this.buffer.length === 0) return

    const batchTracked = this.buffer.splice(0)
    const envelopesPayload = batchTracked.map((b) => b.envelope)

    let body: string
    try {
      body = JSON.stringify({ envelopes: envelopesPayload })
    } catch {
      // Re-add to buffer on serialization failure
      this.buffer.unshift(...batchTracked)
      return
    }

    let beaconSent = false
    try {
      if (typeof navigator !== "undefined" && typeof navigator.sendBeacon === "function") {
        beaconSent = navigator.sendBeacon(this.endpoint, new Blob([body], { type: "application/json" })) === true
      }
    } catch {
      beaconSent = false
    }

    if (beaconSent) {
      return
    }

    // Fallback to fetch with keepalive: true, credentials: "include"
    try {
      if (typeof fetch !== "undefined") {
        fetch(this.endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body,
          keepalive: true,
          credentials: "include",
        }).catch(() => {
          this.buffer.unshift(...batchTracked)
        })
      } else {
        this.buffer.unshift(...batchTracked)
      }
    } catch {
      this.buffer.unshift(...batchTracked)
    }
  }
}
// END_BLOCK: LOG_SHIPPER

// START_BLOCK: BATCH_FLUSH
let shipper: LogShipper | null = null

// START_FUNCTION_CONTRACT: F-M-LOG-SHIPPER.getLogShipper
// purpose: Get or instantiate singleton LogShipper instance.
// inputs: none
// returns: LogShipper
// side_effects: instantiates LogShipper on first call
// emitted_logs: none.
// error_behavior: none.
// END_FUNCTION_CONTRACT: F-M-LOG-SHIPPER.getLogShipper
export function getLogShipper(): LogShipper {
  if (!shipper) {
    const enabled = process.env.NEXT_PUBLIC_GRACE_LOG_SHIPPING === "true"
    shipper = new LogShipper(enabled)
  }
  return shipper
}

// START_FUNCTION_CONTRACT: F-M-LOG-SHIPPER.resetLogShipperForTests
// purpose: Destroy and reset singleton LogShipper instance for unit tests.
// inputs: none
// returns: void
// side_effects: calls destroy() on active instance and resets shipper to null
// emitted_logs: none.
// error_behavior: none.
// END_FUNCTION_CONTRACT: F-M-LOG-SHIPPER.resetLogShipperForTests
export function resetLogShipperForTests(): void {
  if (shipper) {
    shipper.destroy()
    shipper = null
  }
}
// END_BLOCK: BATCH_FLUSH
