// ############################################################################
// AI_HEADER: TEST_LOG_BEACON — immediate single-envelope telemetry coverage.
// ROLE: Verifies sendBeacon transport, canonical envelope shape, and page-lifetime correlation.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-LOG-BEACON
// purpose: Test lib/log/beacon.ts against a mocked navigator.sendBeacon.
// owns:
//   - __tests__/lib/beacon.test.ts
// inputs: jsdom navigator/Blob and mocked sendBeacon.
// outputs: Vitest assertions on transport arguments and envelope fields.
// dependencies: lib/log/beacon, Vitest.
// side_effects: replaces navigator.sendBeacon for the test only.
// emitted_logs: none.
// invariants: beacon traffic is one envelope, not a batch; Blob type is application/json.
// failure_policy: fail on transport, envelope, or correlation drift.
// END_MODULE_CONTRACT: M-TEST-LOG-BEACON

// START_MODULE_MAP: M-TEST-LOG-BEACON
// public_entrypoints:
//   - sendBeaconEvent transport and envelope assertions
//   - page-lifetime correlation assertions
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-LOG-BEACON

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  BEACON_ENDPOINT,
  getBeaconCorrelationId,
  resetBeaconForTests,
  sendBeaconEvent,
} from "@/lib/log/beacon";

const originalSendBeacon = Object.getOwnPropertyDescriptor(navigator, "sendBeacon");
let sendBeacon: ReturnType<typeof vi.fn>;

function blobText(blob: Blob): Promise<string> {
  if (typeof blob.text === "function") return blob.text();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(blob);
  });
}

async function readEnvelope(callIndex = 0): Promise<Record<string, unknown>> {
  const [, body] = sendBeacon.mock.calls[callIndex] as [string, Blob];
  return JSON.parse(await blobText(body)) as Record<string, unknown>;
}

beforeEach(() => {
  resetBeaconForTests();
  sendBeacon = vi.fn(() => true);
  Object.defineProperty(navigator, "sendBeacon", {
    configurable: true,
    writable: true,
    value: sendBeacon,
  });
});

afterEach(() => {
  resetBeaconForTests();
  if (originalSendBeacon) {
    Object.defineProperty(navigator, "sendBeacon", originalSendBeacon);
  } else {
    Reflect.deleteProperty(navigator, "sendBeacon");
  }
});

describe("sendBeaconEvent", () => {
  it("sends one canonical envelope as an application/json Blob", async () => {
    const accepted = sendBeaconEvent(
      "day.load_start",
      { source: "initial_load" },
      {
        slice: "W-WHITE-SCREEN-RESILIENCE",
        module: "M-HOOK-TODAY-CONVERGENCE",
        block: "INITIAL_LOAD",
      },
    );

    expect(accepted).toBe(true);
    expect(sendBeacon).toHaveBeenCalledTimes(1);
    expect(sendBeacon.mock.calls[0][0]).toBe(BEACON_ENDPOINT);

    const body = sendBeacon.mock.calls[0][1] as Blob;
    expect(body).toBeInstanceOf(Blob);
    expect(body.type).toBe("application/json");
    expect("envelopes" in (await readEnvelope())).toBe(false);

    const envelope = await readEnvelope();
    expect(envelope).toMatchObject({
      level: "info",
      service: "web",
      slice: "W-WHITE-SCREEN-RESILIENCE",
      module: "M-HOOK-TODAY-CONVERGENCE",
      block: "INITIAL_LOAD",
      event: "day.load_start",
      payload: { source: "initial_load" },
    });
    expect(typeof envelope.ts).toBe("string");
    expect(typeof envelope.correlation_id).toBe("string");
    expect(envelope.session_id).toBeUndefined();
  });

  it("reuses one correlation id for the page lifetime", async () => {
    sendBeaconEvent("day.load_start", { source: "initial_load" });
    sendBeaconEvent("day.load_ok", { source: "initial_load", attempt: 1 });

    const first = await readEnvelope(0);
    const second = await readEnvelope(1);

    expect(first.correlation_id).toBe(second.correlation_id);
    expect(getBeaconCorrelationId()).toBe(first.correlation_id);

    resetBeaconForTests();
    expect(getBeaconCorrelationId()).not.toBe(first.correlation_id);
  });

  it("returns false without throwing when sendBeacon is unavailable", () => {
    Reflect.deleteProperty(navigator, "sendBeacon");

    expect(() => sendBeaconEvent("auth.ok", { platform: "web" })).not.toThrow();
    expect(sendBeaconEvent("auth.ok", { platform: "web" })).toBe(false);
  });
});
