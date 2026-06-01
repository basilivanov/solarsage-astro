// ############################################################################
// AI_HEADER: MODULE_LOG_SHIPPER
// ROLE: Frontend log shipper — batches and ships logs to backend.
// DEPENDENCIES: fetch API
// GRACE_ANCHORS: [LOG_SHIPPER, BATCH_FLUSH]
// WAVE: W-1.7
// ############################################################################

// START_MODULE_CONTRACT: M-LOG-SHIPPER
// purpose: Batch frontend log envelopes and ship to POST /api/_log with
//   backoff on 429/5xx and kill-switch via GRACE_LOG_SHIPPING flag.
// owns:
//   - lib/log/shipper.ts
// inputs:
//   - LogEnvelope { timestamp, level, message, correlation_id?, extra? }
//   - NEXT_PUBLIC_GRACE_LOG_SHIPPING env var (on/off)
// outputs:
//   - POST /api/_log requests with batched envelopes
// dependencies:
//   - fetch API (browser/Node.js)
// side_effects:
//   - network requests to backend
//   - console.error on shipping failures
// invariants:
//   - batches by 50 envelopes OR 5s, whichever first
//   - backoff on 429/5xx (5s delay + re-enqueue)
//   - kill-switch: GRACE_LOG_SHIPPING=off disables all shipping
// failure_policy:
//   - network error -> console.error, batch dropped
//   - 429/5xx -> re-enqueue with 5s delay
// non_goals:
//   - no persistent queue (in-memory only)
//   - no retry limit (deferred to W-CANON-LOG)
// END_MODULE_CONTRACT: M-LOG-SHIPPER

// START_MODULE_MAP: M-LOG-SHIPPER
// public_entrypoints:
//   - getLogShipper
//   - LogEnvelope (type)
// semantic_blocks:
//   - LOG_SHIPPER: singleton shipper instance
//   - BATCH_FLUSH: batch flushing logic
// owned_tests:
//   - apps/api/tests/test_log_intake.py (e2e)
// END_MODULE_MAP: M-LOG-SHIPPER

// START_BLOCK: LOG_SHIPPER
export interface LogEnvelope {
  timestamp: string;
  level: string;
  message: string;
  correlation_id?: string;
  extra?: Record<string, any>;
}

class LogShipper {
  private buffer: LogEnvelope[] = [];
  private timer: NodeJS.Timeout | null = null;
  private readonly maxBatchSize = 50;
  private readonly maxWaitMs = 5000;
  private readonly endpoint = "/api/_log";
  private flushing = false;

  constructor(private enabled: boolean) {
    if (typeof window !== 'undefined') {
      // Flush on page unload to not lose logs
      window.addEventListener('beforeunload', () => this.flushSync());
      window.addEventListener('pagehide', () => this.flushSync());
    }
  }

  enqueue(envelope: LogEnvelope): void {
    if (!this.enabled) return;

    this.buffer.push(envelope);

    // In debug mode, flush immediately — don't batch
    if (process.env.NEXT_PUBLIC_LOG_LEVEL === 'debug') {
      this.flush();
      return;
    }

    // Flush if batch is full
    if (this.buffer.length >= this.maxBatchSize) {
      this.flush();
      return;
    }

    // Start timer if not running
    if (!this.timer) {
      this.timer = setTimeout(() => this.flush(), this.maxWaitMs);
    }
  }

  async flush(): Promise<void> {
    if (this.buffer.length === 0 || this.flushing) return;
    this.flushing = true;

    // Clear timer
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }

    const batch = this.buffer.splice(0, this.maxBatchSize);

    try {
      const response = await fetch(this.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ envelopes: batch }),
        credentials: "include",
      });

      if (!response.ok) {
        // Re-enqueue on server error
        if (response.status === 429 || response.status >= 500) {
          this.buffer.unshift(...batch);
        }
      }
    } catch {
      // Network error — re-enqueue
      this.buffer.unshift(...batch);
    } finally {
      this.flushing = false;
    }
  }

  private flushSync(): void {
    if (this.buffer.length === 0) return;
    const batch = this.buffer.splice(0);
    const body = JSON.stringify({ envelopes: batch });
    // Use sendBeacon for reliable delivery on page unload
    if (navigator.sendBeacon) {
      navigator.sendBeacon(this.endpoint, new Blob([body], { type: 'application/json' }));
    } else {
      fetch(this.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
        keepalive: true,
      }).catch(() => {});
    }
  }
}
// END_BLOCK: LOG_SHIPPER

// START_BLOCK: BATCH_FLUSH
// Singleton instance
let shipper: LogShipper | null = null;

export function getLogShipper(): LogShipper {
  if (!shipper) {
    const enabled = process.env.NEXT_PUBLIC_GRACE_LOG_SHIPPING === "true";
    shipper = new LogShipper(enabled);
  }
  return shipper;
}
// END_BLOCK: BATCH_FLUSH
