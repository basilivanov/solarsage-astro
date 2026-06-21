// ############################################################################
// AI_HEADER: MODULE_TODAY_PAGE
// ROLE: Pilot RSC demonstrating full GRACE markup on the frontend (W-2.0).
//   Renders a TodayPayload fetched from the backend's /api/today endpoint.
// DEPENDENCIES: react, @/packages/contracts (W-1.1B types), @/lib/grace/log
// GRACE_ANCHORS: [TODAY_FETCH, TODAY_RENDER, ERROR_FALLBACK]
// ############################################################################

// START_MODULE_CONTRACT: M-WEB-TODAY.page
// purpose: Render the Today screen using a server-fetched TodayPayload. Acts
//   as the living example for §7.6 frontend mapping — every other GRACE-
//   conformant page should mirror this structure.
// owns:
//   - app/(grace)/today/page.tsx
// inputs:
//   - GET ${API_BASE_URL}/api/today (typed via @/packages/contracts)
// outputs:
//   - RSC tree (server-rendered HTML)
// dependencies:
//   - M-API-TODAY (contract producer, when available)
//   - M-WEB-CONTRACTS.barrel
//   - M-WEB-LOG.envelope
// side_effects:
//   - one outbound HTTP GET per request; stdout log lines
// invariants:
//   - TodayPayload type comes only from @/packages/contracts (no local re-decl)
//   - 5xx upstream MUST resolve to ERROR_FALLBACK, never throw past page
//   - cache: "no-store" — Today screen is per-request, not static
// failure_policy:
//   - upstream non-2xx -> ERROR_FALLBACK with status surfaced for observability
//   - network throw -> caught and routed to ERROR_FALLBACK
// non_goals:
//   - mutation, auth, calendar editing, client-side hydration of payload
// END_MODULE_CONTRACT: M-WEB-TODAY.page

// START_MODULE_MAP: M-WEB-TODAY.page
// public_entrypoints:
//   - default export TodayPage
// semantic_blocks:
//   - TODAY_FETCH
//   - TODAY_RENDER
//   - ERROR_FALLBACK
// owned_tests:
//   - scripts/grace/check-markers.sh (positive: this file passes the gate)
//   - scripts/grace/check-negative.sh (mutates copies of this file)
// END_MODULE_MAP: M-WEB-TODAY.page

import type { TodayPayload } from "@/packages/contracts";
import { logEvent } from "@/lib/grace/log";

const MODULE = "M-WEB-TODAY.page";

export default async function TodayPage() {
  // START_FUNCTION_CONTRACT: M-WEB-TODAY.page.TodayPage
  // purpose: Server-fetch TodayPayload and render its three regions. Pilot
  //   for the frontend half of GRACE — all comments here are load-bearing.
  // inputs: none (no params/searchParams in W-2.0 pilot)
  // returns: JSX tree
  // side_effects: outbound HTTP GET; stdout log lines
  // emitted_logs: web.today.fetch, web.today.render, web.today.fallback
  // error_behavior: never throws past the page boundary; routes to fallback
  // END_FUNCTION_CONTRACT: M-WEB-TODAY.page.TodayPage

  const apiBase = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

  // START_BLOCK: TODAY_FETCH
  let payload: TodayPayload | null = null;
  let upstreamStatus: number | null = null;
  let upstreamError: string | null = null;

  try {
    const res = await fetch(`${apiBase}/api/today`, { cache: "no-store" });
    upstreamStatus = res.status;
    if (res.ok) {
      payload = (await res.json()) as TodayPayload;
      logEvent({
        module: MODULE,
        fn: "TodayPage",
        block: "TODAY_FETCH",
        event: "web.today.fetch",
        result: "ok",
        extra: { status: res.status },
      });
    } else {
      logEvent({
        module: MODULE,
        fn: "TodayPage",
        block: "TODAY_FETCH",
        event: "web.today.fetch",
        result: "error",
        extra: { status: res.status },
      });
    }
  } catch (err) {
    upstreamError = err instanceof Error ? err.message : String(err);
    logEvent({
      module: MODULE,
      fn: "TodayPage",
      block: "TODAY_FETCH",
      event: "web.today.fetch",
      result: "error",
      extra: { error: upstreamError },
    });
  }
  // END_BLOCK: TODAY_FETCH

  if (payload === null) {
    // START_BLOCK: ERROR_FALLBACK
    logEvent({
      module: MODULE,
      fn: "TodayPage",
      block: "ERROR_FALLBACK",
      event: "web.today.fallback",
      result: "ok",
      extra: { status: upstreamStatus, error: upstreamError },
    });
    return (
      <main className="flex min-h-screen items-center justify-center bg-background px-6">
        <div className="flex w-full max-w-md flex-col gap-3">
          <h1 className="text-balance text-xl font-semibold tracking-tight text-foreground">
            Today is temporarily unavailable
          </h1>
          <p className="text-pretty text-sm leading-relaxed text-muted-foreground">
            {upstreamStatus !== null
              ? `Upstream responded with status ${upstreamStatus}.`
              : "Upstream is unreachable."}
          </p>
        </div>
      </main>
    );
    // END_BLOCK: ERROR_FALLBACK
  }

  // START_BLOCK: TODAY_RENDER
  logEvent({
    module: MODULE,
    fn: "TodayPage",
    block: "TODAY_RENDER",
    event: "web.today.render",
    result: "ok",
  });
  return (
    <main className="flex min-h-screen flex-col gap-6 bg-background px-6 py-10">
      <header className="flex flex-col gap-2">
        <h1 className="text-balance text-2xl font-semibold tracking-tight text-foreground">
          Today
        </h1>
        <p className="text-pretty text-sm leading-relaxed text-muted-foreground">
          Pilot screen for GRACE W-2.0. Payload typed via @/packages/contracts.
        </p>
      </header>
      <pre className="overflow-auto rounded-md border border-border bg-muted p-4 text-xs leading-relaxed text-foreground">
        {JSON.stringify(payload, null, 2)}
      </pre>
    </main>
  );
  // END_BLOCK: TODAY_RENDER
}
