// ############################################################################
// AI_HEADER: MODULE_APP_SYNASTRY_PAGE
// ROLE: Next.js page component for /synastry route
// DEPENDENCIES: react, components/synastry/*
// ############################################################################

// START_MODULE_CONTRACT: M-APP-SYNASTRY-PAGE
// purpose: Next.js page wrapper for synastry (together) feature, managing active partner state.
// owns:
//   - app/(grace)/synastry/page.tsx
// inputs: none
// outputs: SynastryPage TSX render
// dependencies: components/synastry/synastry-screen, components/synastry/synastry-detail-screen
// side_effects: none
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-APP-SYNASTRY-PAGE

// START_MODULE_MAP: M-APP-SYNASTRY-PAGE
// public_entrypoints:
//   - SynastryPage
// semantic_blocks:
//   - SYNASTRY_PAGE: Next.js page component
// owned_tests: none
// END_MODULE_MAP: M-APP-SYNASTRY-PAGE

"use client"

import { useState } from "react"
import { SynastryScreen } from "@/components/synastry/synastry-screen"
import { SynastryDetailScreen } from "@/components/synastry/synastry-detail-screen"

// START_BLOCK: SYNASTRY_PAGE
export default function SynastryPage() {
  const [selectedPartnerId, setSelectedPartnerId] = useState<string | null>(null)

  if (selectedPartnerId) {
    return (
      <div className="mx-auto max-w-xl p-4">
        <SynastryDetailScreen
          partnerId={selectedPartnerId}
          onBack={() => setSelectedPartnerId(null)}
        />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-xl p-4">
      <SynastryScreen
        onSelectPartner={(partnerId) => setSelectedPartnerId(partnerId)}
      />
    </div>
  )
}
// END_BLOCK: SYNASTRY_PAGE
