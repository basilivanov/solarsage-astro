// ############################################################################
// AI_HEADER: MODULE_TODAY_DEV_AUDIT_DRAWER
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TODAY-CALENDAR
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Module: dev-audit-drawer.tsx
// owns:
//   - components/today/dev-audit-drawer.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// public_entrypoints:
//   - DevAuditDrawer
// semantic_blocks:
//   - DEV_AUDIT_DRAWER: Dev audit drawer debug component
// owned_tests:
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
// END_MODULE_MAP

import React, { useState, useEffect } from "react"
import { TodayV2Audit } from "@/lib/contracts/today"

interface DevAuditDrawerProps {
  audit: TodayV2Audit | null | undefined
  forceShow?: boolean
}

// START_BLOCK: DEV_AUDIT_DRAWER
export function DevAuditDrawer({ audit, forceShow = false }: DevAuditDrawerProps) {
  const [show, setShow] = useState(forceShow)

  useEffect(() => {
    if (typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search)
      const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
      const isNonProd = process.env.NODE_ENV !== "production" || isLocal
      if (forceShow || (isNonProd && urlParams.get("audit") === "1")) {
        setShow(true)
      }
    }
  }, [forceShow])

  if (!show || !audit) return null

  return (
    <div
      data-testid="dev-audit-drawer"
      className="p-4 bg-slate-900 text-slate-100 rounded-2xl border border-slate-800 space-y-4 font-mono text-xs shadow-xl"
    >
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <h3 className="font-bold text-amber-400">Dev Audit Console</h3>
        <button
          onClick={() => setShow(false)}
          className="text-slate-400 hover:text-slate-100 text-sm font-sans"
        >
          ✕
        </button>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <span className="text-slate-400">Payload:</span> {audit.payloadVersion}
        </div>
        <div>
          <span className="text-slate-400">Calc Ver:</span> {audit.calculationVersion}
        </div>
        <div>
          <span className="text-slate-400">Scoring Ver:</span> {audit.scoringVersion}
        </div>
        <div>
          <span className="text-slate-400">Act Ver:</span> {audit.activationLayerVersion}
        </div>
      </div>

      {audit.traceId && (
        <div>
          <span className="text-slate-400">Trace ID:</span> {audit.traceId}
        </div>
      )}

      {audit.canonVersions && Object.keys(audit.canonVersions).length > 0 && (
        <div className="space-y-1">
          <span className="text-slate-400 font-semibold block border-b border-slate-800 pb-0.5">
            Canon Versions:
          </span>
          <div className="grid grid-cols-2 gap-x-4">
            {Object.entries(audit.canonVersions).map(([key, val]) => (
              <div key={key}>
                {key}: <span className="text-amber-200">{val}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {audit.v1V2Diff && Object.keys(audit.v1V2Diff).length > 0 && (
        <div className="space-y-1">
          <span className="text-slate-400 font-semibold block border-b border-slate-800 pb-0.5">
            V1/V2 Diff Summary:
          </span>
          <pre className="p-2 rounded bg-slate-950 text-emerald-400 overflow-x-auto whitespace-pre-wrap max-h-40">
            {JSON.stringify(audit.v1V2Diff, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
// END_BLOCK: DEV_AUDIT_DRAWER
