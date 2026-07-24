// ############################################################################
// AI_HEADER: MODULE_FRONTEND_API_PROMO
// ROLE: Validated browser API client for promo preview and redemption.
// DEPENDENCIES: lib/log/instrumented-fetch, packages/contracts/runtime
// GRACE_ANCHORS: [PROMO_API_CLIENT, PROMO_API_ERROR, PROMO_PREVIEW, PROMO_REDEEM]
// WAVE: W-NAMED-PROMO-CAMPAIGN
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-PROMO
// purpose: Provide browser API client functions previewPromo and redeemPromo with contract validation via generated Zod schemas and safe error handling without token/PII leaks.
// owns:
//   - lib/api/promo.ts
// inputs:
//   - token: string
// outputs:
//   - previewPromo: Promise<PromoPreviewResponse>
//   - redeemPromo: Promise<PromoRedeemResponse>
//   - PromoApiError: Error class with status and code properties
// dependencies:
//   - M-LOG-INSTRUMENTED-FETCH (instrumentedFetch)
//   - M-CONTRACTS-RUNTIME (PromoPreviewResponseWireSchema, PromoRedeemResponseWireSchema, PromoErrorDetailWireSchema)
// side_effects:
//   - credentialed POST fetch requests to /api/promo/preview and /api/promo/redeem
// emitted_logs:
//   - emitted via instrumentedFetch
// invariants:
//   - token argument is never stored in error objects, properties, logs, or module state
//   - response bodies are validated using generated Zod schemas
//   - non-ok responses normalize detail into typed PromoApiError or UNKNOWN fallback
//   - ALREADY_REDEEMED code is preserved as typed PromoApiError(409, "ALREADY_REDEEMED", ...)
// failure_policy:
//   - throws PromoApiError for non-ok status or invalid response contracts; rethrows network exceptions untouched
// END_MODULE_CONTRACT: M-FRONTEND-API-PROMO

// START_MODULE_MAP: M-FRONTEND-API-PROMO
// public_entrypoints:
//   - previewPromo
//   - redeemPromo
//   - PromoApiError
//   - PromoErrorCode
// semantic_blocks:
//   - PROMO_API_ERROR: PromoApiError definition
//   - PROMO_PREVIEW: previewPromo function
//   - PROMO_REDEEM: redeemPromo function
// owned_tests:
//   - __tests__/api/promo-client.test.ts
// END_MODULE_MAP: M-FRONTEND-API-PROMO

import type {
  PromoPreviewResponse,
  PromoRedeemResponse,
  PromoErrorDetail,
} from "@/packages/contracts"
import {
  PromoPreviewResponseWireSchema,
  PromoRedeemResponseWireSchema,
  PromoErrorDetailWireSchema,
} from "@/packages/contracts/runtime"
import { instrumentedFetch } from "@/lib/log/instrumented-fetch"

export type PromoErrorCode = PromoErrorDetail["code"] | "UNKNOWN"

// START_BLOCK: PROMO_API_ERROR
export class PromoApiError extends Error {
  readonly status: number
  readonly code: PromoErrorCode

  constructor(status: number, code: PromoErrorCode, message: string) {
    super(message)
    this.name = "PromoApiError"
    this.status = status
    this.code = code
  }
}
// END_BLOCK: PROMO_API_ERROR

async function handleResponseError(
  response: Response,
  fallbackMessage: string
): Promise<never> {
  let errorJson: unknown = null
  try {
    errorJson = await response.json()
  } catch {
    errorJson = null
  }

  const detailCandidate =
    errorJson && typeof errorJson === "object" && "detail" in errorJson
      ? (errorJson as Record<string, unknown>).detail
      : null

  const detailParsed = PromoErrorDetailWireSchema.safeParse(detailCandidate)
  if (detailParsed.success) {
    throw new PromoApiError(
      response.status,
      detailParsed.data.code,
      detailParsed.data.message
    )
  }

  throw new PromoApiError(response.status, "UNKNOWN", fallbackMessage)
}

// START_BLOCK: PROMO_PREVIEW
export async function previewPromo(
  token: string
): Promise<PromoPreviewResponse> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-PROMO.previewPromo
  // purpose: Request preview of promo campaign offer and profile completeness.
  // inputs: token (string)
  // returns: Promise<PromoPreviewResponse>
  // side_effects: POST /api/promo/preview request via instrumentedFetch
  // emitted_logs: via instrumentedFetch
  // error_behavior: throws PromoApiError on non-ok/invalid response or rethrows fetch error
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-PROMO.previewPromo
  const response = await instrumentedFetch({
    operation: "promo.preview",
    routeTemplate: "POST /api/promo/preview",
    url: "/api/promo/preview",
    init: {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
      body: JSON.stringify({ token }),
    },
  })

  if (!response.ok) {
    await handleResponseError(response, "Не удалось проверить промокод.")
  }

  let json: unknown = null
  try {
    json = await response.json()
  } catch {
    throw new PromoApiError(
      response.status,
      "UNKNOWN",
      "Недопустимый формат ответа сервера."
    )
  }

  const parsed = PromoPreviewResponseWireSchema.safeParse(json)
  if (!parsed.success) {
    throw new PromoApiError(
      response.status,
      "UNKNOWN",
      "Недопустимый формат ответа сервера."
    )
  }

  return parsed.data
}
// END_BLOCK: PROMO_PREVIEW

// START_BLOCK: PROMO_REDEEM
export async function redeemPromo(
  token: string
): Promise<PromoRedeemResponse> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-PROMO.redeemPromo
  // purpose: Request redemption of promo campaign and issuance of grants.
  // inputs: token (string)
  // returns: Promise<PromoRedeemResponse>
  // side_effects: POST /api/promo/redeem request via instrumentedFetch
  // emitted_logs: via instrumentedFetch
  // error_behavior: throws PromoApiError on non-ok/invalid response or rethrows fetch error
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-PROMO.redeemPromo
  const response = await instrumentedFetch({
    operation: "promo.redeem",
    routeTemplate: "POST /api/promo/redeem",
    url: "/api/promo/redeem",
    init: {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
      body: JSON.stringify({ token }),
    },
  })

  if (!response.ok) {
    await handleResponseError(response, "Не удалось активировать промокод.")
  }

  let json: unknown = null
  try {
    json = await response.json()
  } catch {
    throw new PromoApiError(
      response.status,
      "UNKNOWN",
      "Недопустимый формат ответа сервера."
    )
  }

  const parsed = PromoRedeemResponseWireSchema.safeParse(json)
  if (!parsed.success) {
    throw new PromoApiError(
      response.status,
      "UNKNOWN",
      "Недопустимый формат ответа сервера."
    )
  }

  return parsed.data
}
// END_BLOCK: PROMO_REDEEM
