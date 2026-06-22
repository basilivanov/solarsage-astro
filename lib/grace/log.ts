// ############################################################################
// AI_HEADER: MODULE_GRACE_LOG
// ROLE: Structured logging envelope for frontend server actions and route
//   handlers, mirroring the §8 envelope used by the backend.
// DEPENDENCIES: none (stdout JSON only)
// GRACE_ANCHORS: [LOG_ENVELOPE]
// ############################################################################

// START_MODULE_CONTRACT: M-WEB-LOG.envelope
// purpose: Emit a single-line JSON record with the canonical GRACE envelope
//   so frontend events are correlatable with backend events by trace_id.
// owns:
//   - lib/grace/log.ts
// inputs:
//   - LogEvent { module, fn, block, event, result, trace_id?, scenario_id?, extra? }
// outputs:
//   - one JSON line on process.stdout per call
// dependencies:
//   - none
// side_effects:
//   - writes to stdout
// invariants:
//   - MUST be safe to call in RSC, route handlers, and server actions
//   - MUST NOT throw on unserializable extras (replaces with "[unserializable]")
//   - field order is fixed for grep-friendliness: ts, module, fn, block, event, result
// failure_policy:
//   - JSON.stringify failure -> stdout receives a fallback record with
//     event="log.serialize_error" and never throws upstream
// non_goals:
//   - log shipping, sampling, log levels beyond "result"
// END_MODULE_CONTRACT: M-WEB-LOG.envelope

// START_MODULE_MAP: M-WEB-LOG.envelope
// public_entrypoints:
//   - logEvent
//   - LogEvent (type)
// semantic_blocks:
//   - LOG_ENVELOPE
// owned_tests:
//   - app/(grace)/today/page.tsx (calls logEvent in TODAY_FETCH / ERROR_FALLBACK)
// END_MODULE_MAP: M-WEB-LOG.envelope

// START_BLOCK: LOG_ENVELOPE
export type LogResult = "ok" | "error" | "skipped";

export type LogEvent = {
  module: string;
  fn: string;
  block: string;
  event: string;
  result: LogResult;
  trace_id?: string;
  scenario_id?: string;
  extra?: Record<string, unknown>;
};

export function logEvent(e: LogEvent): void {
  const record = {
    ts: new Date().toISOString(),
    module: e.module,
    fn: e.fn,
    block: e.block,
    event: e.event,
    result: e.result,
    trace_id: e.trace_id,
    scenario_id: e.scenario_id,
    extra: e.extra,
  };
  try {
    // Single-line JSON; matches backend §8 envelope for cross-tier grep.
    process.stdout.write(JSON.stringify(record) + "\n");
  } catch {
    process.stdout.write(
      JSON.stringify({
        ts: new Date().toISOString(),
        module: e.module,
        fn: e.fn,
        block: e.block,
        event: "log.serialize_error",
        result: "error",
      }) + "\n",
    );
  }
}
// END_BLOCK: LOG_ENVELOPE
