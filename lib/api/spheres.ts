// ############################################################################
// AI_HEADER: MODULE_API_SPHERES — validated static sphere page client.
// ROLE: Fetches the long-lived natal and period layers for one product sphere.
// ############################################################################

// START_MODULE_CONTRACT: M-API-CLIENT-SPHERES
// purpose: Own the authenticated HTTP boundary for the static sphere page.
// owns:
//   - lib/api/spheres.ts
// inputs: canonical or route-provided sphere key and optional AbortSignal.
// outputs: generated TodaySpherePagePayload or a typed transport/HTTP/schema error.
// dependencies: generated sphere page contract and lib/log/instrumented-fetch.ts.
// side_effects: credentialed GET /api/spheres/{key}.
// emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed.
// invariants: successful responses are validated by the generated Zod schema; route keys are encoded once.
// failure_policy: network, HTTP, and invalid payload failures remain distinguishable to the route.
// END_MODULE_CONTRACT: M-API-CLIENT-SPHERES

// START_MODULE_MAP: M-API-CLIENT-SPHERES
// public_entrypoints:
//   - SpherePageApiError
//   - fetchSpherePage
// semantic_blocks:
//   - ERROR_TYPES: typed network, invalid-payload, and HTTP errors.
//   - SPHERE_PAGE_REQUEST: authenticated GET and generated-schema validation.
// owned_tests:
//   - __tests__/components/today-convergence/sphere-page.test.tsx
// END_MODULE_MAP: M-API-CLIENT-SPHERES

import { TodaySpherePagePayloadWireSchema } from "@/packages/contracts/today-sphere-page";
// eslint-disable-next-line grace/contracts-only-import
import type { TodaySpherePagePayload } from "@/packages/contracts/today-sphere-page";
import { instrumentedFetch } from "@/lib/log/instrumented-fetch";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export type SpherePageErrorKind = "network" | "invalid" | "http";

export class SpherePageApiError extends Error {
  // START_FUNCTION_CONTRACT: F-M-API-CLIENT-SPHERES.SpherePageApiError.constructor
  // purpose: Preserve safe failure classification and HTTP status for the sphere page route.
  // inputs: message, kind, status, and optional backend code.
  // returns: SpherePageApiError.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: exposes status/code only, never response bodies.
  // END_FUNCTION_CONTRACT: F-M-API-CLIENT-SPHERES.SpherePageApiError.constructor
  readonly kind: SpherePageErrorKind;
  readonly status: number;
  readonly code?: string;

  constructor(message: string, kind: SpherePageErrorKind, status: number, code?: string) {
    super(message);
    this.name = "SpherePageApiError";
    this.kind = kind;
    this.status = status;
    this.code = code;
  }
}

type ErrorDetails = { message?: string; code?: string };

async function readErrorDetails(response: Response): Promise<ErrorDetails> {
  try {
    const body = (await response.json()) as unknown;
    if (typeof body === "string") return { message: body };
    if (!body || typeof body !== "object") return {};

    const record = body as Record<string, unknown>;
    const detail = record.detail;
    if (typeof detail === "string") return { message: detail };
    if (detail && typeof detail === "object") {
      const detailRecord = detail as Record<string, unknown>;
      return {
        message: typeof detailRecord.message === "string" ? detailRecord.message : undefined,
        code: typeof detailRecord.code === "string" ? detailRecord.code : undefined,
      };
    }
    return {
      message: typeof record.message === "string" ? record.message : undefined,
      code: typeof record.code === "string" ? record.code : undefined,
    };
  } catch {
    return {};
  }
}

async function parsePayload(response: Response): Promise<TodaySpherePagePayload> {
  let raw: unknown;
  try {
    raw = await response.json();
  } catch {
    throw new SpherePageApiError(
      "Ответ страницы сферы имеет неверный формат",
      "invalid",
      502,
      "SCHEMA_VALIDATION_ERROR",
    );
  }

  const parsed = TodaySpherePagePayloadWireSchema.safeParse(raw);
  if (!parsed.success) {
    throw new SpherePageApiError(
      "Ответ страницы сферы имеет неверный формат",
      "invalid",
      502,
      "SCHEMA_VALIDATION_ERROR",
    );
  }
  return parsed.data;
}

// START_BLOCK: SPHERE_PAGE_REQUEST
export async function fetchSpherePage(
  sphereKey: string,
  signal?: AbortSignal,
): Promise<TodaySpherePagePayload> {
  // START_FUNCTION_CONTRACT: F-M-API-CLIENT-SPHERES.fetchSpherePage
  // purpose: Fetch and validate the long-lived natal and period layers for one sphere.
  // inputs: sphereKey — route sphere key; signal — optional cancellation signal.
  // returns: generated TodaySpherePagePayload.
  // side_effects: credentialed GET /api/spheres/{key}.
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed.
  // error_behavior: throws typed network, HTTP (including 403/422), or invalid-payload error.
  // END_FUNCTION_CONTRACT: F-M-API-CLIENT-SPHERES.fetchSpherePage
  let response: Response;
  try {
    response = await instrumentedFetch({
      operation: "spheres.page",
      routeTemplate: "GET /api/spheres/{key}",
      url: `${API_BASE}/api/spheres/${encodeURIComponent(sphereKey)}`,
      init: {
        credentials: "include",
        signal,
        headers: { Accept: "application/json" },
      },
    });
  } catch (error) {
    if (error instanceof SpherePageApiError) throw error;
    throw new SpherePageApiError(
      "Не удалось связаться со страницей сферы",
      "network",
      0,
      "NETWORK_ERROR",
    );
  }

  if (!response.ok) {
    const details = await readErrorDetails(response);
    throw new SpherePageApiError(
      details.message || "Не удалось загрузить страницу сферы",
      "http",
      response.status,
      details.code,
    );
  }

  return parsePayload(response);
}
// END_BLOCK: SPHERE_PAGE_REQUEST
