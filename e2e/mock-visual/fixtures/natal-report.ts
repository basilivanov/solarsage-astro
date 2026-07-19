// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_FIXTURE_NATAL_REPORT
// ROLE: Contract-valid NatalReportRead fixtures for natal report state tests.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-FIXTURE-NATAL-REPORT
// purpose: Provide the contract-valid static NatalReportRead payload for the
//   natal full-report GENERATING lifecycle state. The HTTP-500 error scenario
//   in natal.spec.ts uses its own inline route body ({ detail: ... }) and
//   does not depend on this fixture.
// owns:
//   - e2e/mock-visual/fixtures/natal-report.ts
// inputs: none (static fixture)
// outputs: Named exports: natalReportGeneratingPayload, natalReportGeneratingId
// dependencies: lib/contracts/natal (NatalReportRead)
// side_effects: none
// emitted_logs: none
// invariants:
//   - Shape matches NatalReportReadSchema (id, status, meta, sections).
//   - No fabricated astrology — placeholder payload only for state rendering.
// failure_policy: n/a (static data)
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-FIXTURE-NATAL-REPORT

// START_MODULE_MAP: M-E2E-MOCK-VISUAL-FIXTURE-NATAL-REPORT
// public_entrypoints:
//   - natalReportGeneratingPayload
//   - natalReportGeneratingId
// semantic_blocks:
//   - GENERATING_PAYLOAD: valid GENERATING report fixture
// owned_tests:
//   - e2e/mock-visual/natal.spec.ts
// END_MODULE_MAP: M-E2E-MOCK-VISUAL-FIXTURE-NATAL-REPORT

import type { NatalReportRead } from "../../../lib/contracts/natal";

// START_BLOCK: GENERATING_PAYLOAD
export const natalReportGeneratingId = "gen-visual-1";

export const natalReportGeneratingPayload: NatalReportRead = {
  id: natalReportGeneratingId,
  status: "GENERATING",
  accessState: "FREE_PREVIEW",
  meta: {
    userName: "Ada",
    birthDate: "1985-12-10",
    birthTime: null,
    birthPlace: "Lisbon, Portugal",
    houseSystem: "Placidus",
    contextHash: null,
    promptVersion: "1",
  },
  sections: [],
  errorCode: null,
  errorMessage: null,
  createdAt: "2026-07-08T09:00:00Z",
  completedAt: null,
};
// END_BLOCK: GENERATING_PAYLOAD
