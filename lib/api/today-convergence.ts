// ############################################################################
// AI_HEADER: MODULE_API_TODAY_CONVERGENCE — validated Today Convergence HTTP client.
// ROLE: Fetches the generated day envelope, requests a retry, and records a best-effort day impression.
// ############################################################################

// START_MODULE_CONTRACT: M-API-CLIENT-TODAY-CONVERGENCE
// purpose: Own the frontend HTTP boundary for the Today Convergence day envelope and impression lineage.
// owns:
//   - lib/api/today-convergence.ts
// inputs: dateParam, snapshotId, optional AbortSignal.
// outputs: generated TodayConvergencePayload, retry acceptance metadata, or void telemetry result.
// dependencies: generated Today contracts, lib/log/instrumented-fetch.ts, lib/log/index.ts.
// side_effects: credentialed GET/POST requests to /api/day/*.
// emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed, day.impression_recorded, day.impression_rejected.
// invariants: every successful day envelope is Zod-validated; impression failure never escapes the client.
// failure_policy: network errors are typed as network; HTTP errors preserve status; invalid envelopes are typed invalid.
// END_MODULE_CONTRACT: M-API-CLIENT-TODAY-CONVERGENCE

// START_MODULE_MAP: M-API-CLIENT-TODAY-CONVERGENCE
// public_entrypoints:
//   - TodayConvergenceApiError
//   - fetchTodayConvergence
//   - retryTodayConvergence
//   - recordDayImpression
// semantic_blocks:
//   - ERROR_TYPES: typed network, invalid-payload, and HTTP errors.
//   - DAY_REQUEST: GET envelope with generated schema validation.
//   - RETRY_REQUEST: POST retry with Retry-After parsing.
//   - IMPRESSION: best-effort day impression.
// owned_tests:
//   - __tests__/hooks/useTodayConvergence.test.ts
// END_MODULE_MAP: M-API-CLIENT-TODAY-CONVERGENCE

import {
  TodayConvergencePayloadWireSchema,
} from "@/packages/contracts/today-convergence";
import type { TodayConvergencePayload } from "@/packages/contracts";
import { logEvent } from "@/lib/log";
import { instrumentedFetch } from "@/lib/log/instrumented-fetch";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export type { TodayConvergencePayload };

export type TodayConvergenceErrorKind = "network" | "invalid" | "http";

export class TodayConvergenceApiError extends Error {
  // START_FUNCTION_CONTRACT: F-M-API-CLIENT-TODAY-CONVERGENCE.TodayConvergenceApiError.constructor
  // purpose: Create a typed, safe error for the Today Convergence transport boundary.
  // inputs: message, kind, status, and optional backend code.
  // returns: TodayConvergenceApiError.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: preserves status/code for callers without exposing response bodies by default.
  // END_FUNCTION_CONTRACT: F-M-API-CLIENT-TODAY-CONVERGENCE.TodayConvergenceApiError.constructor
  readonly kind: TodayConvergenceErrorKind;
  readonly status: number;
  readonly code?: string;

  constructor(
    message: string,
    kind: TodayConvergenceErrorKind,
    status: number,
    code?: string,
  ) {
    super(message);
    this.name = "TodayConvergenceApiError";
    this.kind = kind;
    this.status = status;
    this.code = code;
  }
}

type RequestOptions = { signal?: AbortSignal };

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

function asNetworkError(error: unknown): TodayConvergenceApiError {
  if (error instanceof TodayConvergenceApiError) return error;
  return new TodayConvergenceApiError(
    "Не удалось связаться с сервисом дня",
    "network",
    0,
    "NETWORK_ERROR",
  );
}

async function request(
  method: "GET" | "POST",
  path: string,
  options: RequestOptions & { body?: unknown; routeTemplate: string },
): Promise<Response> {
  try {
    return await instrumentedFetch({
      operation: `today-convergence.${method.toLowerCase()}`,
      routeTemplate: options.routeTemplate,
      url: `${API_BASE}${path}`,
      init: {
        method,
        credentials: "include",
        signal: options.signal,
        headers: {
          Accept: "application/json",
          ...(options.body === undefined ? {} : { "Content-Type": "application/json" }),
        },
        ...(options.body === undefined ? {} : { body: JSON.stringify(options.body) }),
      },
    });
  } catch (error) {
    throw asNetworkError(error);
  }
}

async function throwHttpError(response: Response, fallbackMessage: string): Promise<never> {
  const details = await readErrorDetails(response);
  throw new TodayConvergenceApiError(
    details.message || fallbackMessage,
    "http",
    response.status,
    details.code,
  );
}

async function parsePayload(response: Response): Promise<TodayConvergencePayload> {
  let raw: unknown;
  try {
    raw = await response.json();
  } catch {
    throw new TodayConvergenceApiError(
      "Ответ дня имеет неверный формат",
      "invalid",
      502,
      "SCHEMA_VALIDATION_ERROR",
    );
  }

  const parsed = TodayConvergencePayloadWireSchema.safeParse(raw);
  if (!parsed.success) {
    throw new TodayConvergenceApiError(
      "Ответ дня имеет неверный формат",
      "invalid",
      502,
      "SCHEMA_VALIDATION_ERROR",
    );
  }
  return parsed.data;
}

function parseRetryAfter(value: string | null): number | undefined {
  if (!value) return undefined;
  const seconds = Number.parseInt(value, 10);
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : undefined;
}

// START_BLOCK: DAY_REQUEST
export async function fetchTodayConvergence(
  dateParam: string,
  signal?: AbortSignal,
): Promise<TodayConvergencePayload> {
  // START_FUNCTION_CONTRACT: F-M-API-CLIENT-TODAY-CONVERGENCE.fetchTodayConvergence
  // purpose: Fetch and validate one Today Convergence envelope.
  // inputs: dateParam — today or an ISO YYYY-MM-DD route parameter; signal — optional cancellation signal.
  // returns: generated TodayConvergencePayload.
  // side_effects: credentialed GET /api/day/{dateParam}.
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed.
  // error_behavior: throws typed network, HTTP, or invalid-payload error.
  // END_FUNCTION_CONTRACT: F-M-API-CLIENT-TODAY-CONVERGENCE.fetchTodayConvergence
  const safeDateParam = encodeURIComponent(dateParam);
  const response = await request("GET", `/api/day/${safeDateParam}`, {
    signal,
    routeTemplate: "GET /api/day/{date}",
  });
  if (!response.ok) return throwHttpError(response, "Не удалось загрузить день");
  return parsePayload(response);
}
// END_BLOCK: DAY_REQUEST

// START_BLOCK: RETRY_REQUEST
export async function retryTodayConvergence(
  dateParam: string,
  signal?: AbortSignal,
): Promise<{ payload?: TodayConvergencePayload; retryAfterSeconds?: number }> {
  // START_FUNCTION_CONTRACT: F-M-API-CLIENT-TODAY-CONVERGENCE.retryTodayConvergence
  // purpose: Request an idempotent day retry and normalize 200/202 responses.
  // inputs: dateParam — today or ISO route parameter; signal — optional cancellation signal.
  // returns: payload for an immediate 200 or retryAfterSeconds for 202 acceptance.
  // side_effects: credentialed POST /api/day/{dateParam}/retry.
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed.
  // error_behavior: throws typed network, HTTP, or invalid-payload error.
  // END_FUNCTION_CONTRACT: F-M-API-CLIENT-TODAY-CONVERGENCE.retryTodayConvergence
  const safeDateParam = encodeURIComponent(dateParam);
  const response = await request("POST", `/api/day/${safeDateParam}/retry`, {
    signal,
    routeTemplate: "POST /api/day/{date}/retry",
  });
  if (!response.ok && response.status !== 202) {
    return throwHttpError(response, "Не удалось повторить расчёт дня");
  }
  if (response.status === 202) {
    return { retryAfterSeconds: parseRetryAfter(response.headers.get("Retry-After")) };
  }
  return { payload: await parsePayload(response) };
}
// END_BLOCK: RETRY_REQUEST

// START_BLOCK: IMPRESSION
export async function recordDayImpression(
  snapshotId: string,
  signal?: AbortSignal,
): Promise<void> {
  // START_FUNCTION_CONTRACT: F-M-API-CLIENT-TODAY-CONVERGENCE.recordDayImpression
  // purpose: Record a best-effort day surface impression for a published snapshot.
  // inputs: snapshotId — opaque published snapshot identifier; signal — optional cancellation signal.
  // returns: void regardless of telemetry outcome.
  // side_effects: credentialed POST /api/day/snapshots/{snapshotId}/impression.
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed, day.impression_recorded, day.impression_rejected.
  // error_behavior: swallows all network and HTTP failures.
  // END_FUNCTION_CONTRACT: F-M-API-CLIENT-TODAY-CONVERGENCE.recordDayImpression
  try {
    const safeSnapshotId = encodeURIComponent(snapshotId);
    const response = await request("POST", `/api/day/snapshots/${safeSnapshotId}/impression`, {
      signal,
      routeTemplate: "POST /api/day/snapshots/{snapshotId}/impression",
      body: { surface: "day" },
    });
    if (!response.ok) {
      logEvent("day.impression_rejected", { surface: "day" }, {
        slice: "W-TODAY-CONVERGENCE",
        module: "M-API-CLIENT-TODAY-CONVERGENCE",
        block: "IMPRESSION",
        level: "warn",
      });
      return;
    }
    logEvent("day.impression_recorded", { surface: "day" }, {
      slice: "W-TODAY-CONVERGENCE",
      module: "M-API-CLIENT-TODAY-CONVERGENCE",
      block: "IMPRESSION",
    });
  } catch {
    logEvent("day.impression_rejected", { surface: "day" }, {
      slice: "W-TODAY-CONVERGENCE",
      module: "M-API-CLIENT-TODAY-CONVERGENCE",
      block: "IMPRESSION",
      level: "warn",
    });
  }
}
// END_BLOCK: IMPRESSION
