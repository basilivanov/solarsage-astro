
// ############################################################################
// AI_HEADER: MODULE_LIB_LOG_SHIPPER_TEST
// ROLE: Unit tests for log-shipper.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for log-shipperts behavior
// owns:
//   - __tests__/lib/log-shipper.test.ts
// inputs: Mocks, fixtures
// outputs: Assertion results
// dependencies: local modules
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
// AI_HEADER
// module: M-TEST-LOG-SHIPPER
// wave: W-1.7
// purpose: LogShipper unit tests — batching, flushing, backoff, kill-switch

import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockFetch = vi.fn();
const mockSendBeacon = vi.fn().mockReturnValue(true);
const capturedHandlers: Record<string, Array<() => void>> = {};

vi.stubGlobal('fetch', mockFetch);

beforeEach(() => {
  vi.resetModules();
  mockFetch.mockReset().mockResolvedValue({ ok: true, status: 200 });
  mockSendBeacon.mockReset().mockReturnValue(true);

  Object.defineProperty(navigator, 'sendBeacon', {
    value: mockSendBeacon,
    writable: true,
    configurable: true,
  });

  // Capture event handlers instead of adding real listeners to avoid
  // accumulation across tests. The shipper constructor registers
  // beforeunload / pagehide listeners on window.
  Object.keys(capturedHandlers).forEach((k) => delete capturedHandlers[k]);
  vi.spyOn(window, 'addEventListener').mockImplementation(
    (event: string, handler: any) => {
      if (!capturedHandlers[event]) capturedHandlers[event] = [];
      capturedHandlers[event].push(handler);
    },
  );
});

function restoreRealTimers() {
  vi.useRealTimers();
}

function useFakeTimers() {
  vi.useFakeTimers();
}

describe('LogShipper', () => {
  async function createShipper(opts?: { shipping?: boolean; logLevel?: string }) {
    process.env.NEXT_PUBLIC_GRACE_LOG_SHIPPING =
      opts?.shipping !== false ? 'true' : 'false';
    process.env.NEXT_PUBLIC_LOG_LEVEL = opts?.logLevel || 'info';
    const mod = await import('@/lib/log/shipper');
    return mod.getLogShipper();
  }

  function envelope(msg: string): import('@/lib/log/shipper').CanonEnvelope {
    return {
      ts: new Date().toISOString(),
      level: 'info',
      env: 'test',
      service: 'web',
      service_version: 'test',
      slice: 'W-TEST',
      module: 'M-TEST-SHIPPER',
      block: 'TEST_ENVELOPE',
      event: 'system.request',
      correlation_id: 'test-corr-id',
      msg,
    };
  }

  // 1 — enqueue pushes to buffer without flushing when under batch size
  it('enqueue adds to buffer without flushing (under batch size)', async () => {
    const shipper = await createShipper();
    shipper.enqueue(envelope('hello'));
    expect(mockFetch).not.toHaveBeenCalled();
  });

  // 2 — flush sends a batch to /api/_log
  it('flush sends batch to /api/_log', async () => {
    const shipper = await createShipper();
    shipper.enqueue(envelope('hello'));
    await shipper.flush();
    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/_log');
    const body = JSON.parse(init.body);
    expect(body.envelopes).toHaveLength(1);
    expect(body.envelopes[0].msg).toBe('hello');
  });

  // 3 — batch auto-flushes when buffer reaches maxBatchSize (50)
  it('batch flushes when maxBatchSize reached (50)', async () => {
    const shipper = await createShipper();
    for (let i = 0; i < 50; i++) {
      shipper.enqueue(envelope(`msg-${i}`));
    }
    expect(mockFetch).toHaveBeenCalledTimes(1);
    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.envelopes).toHaveLength(50);
  });

  // 4 — timer triggers flush after maxWaitMs (5000)
  it('timer flushes after maxWaitMs (5000)', async () => {
    useFakeTimers();
    const shipper = await createShipper();
    shipper.enqueue(envelope('tick'));
    expect(mockFetch).not.toHaveBeenCalled();
    vi.advanceTimersByTime(5000);
    expect(mockFetch).toHaveBeenCalledTimes(1);
    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.envelopes).toHaveLength(1);
    restoreRealTimers();
  });

  // 5 — flushSync uses sendBeacon on beforeunload
  it('flushSync uses sendBeacon on beforeunload', async () => {
    const shipper = await createShipper();
    shipper.enqueue(envelope('goodbye'));
    expect(mockSendBeacon).not.toHaveBeenCalled();

    // Trigger the captured beforeunload handler (arrow fn → correct this)
    const handlers = capturedHandlers['beforeunload'] ?? [];
    expect(handlers.length).toBeGreaterThanOrEqual(1);
    handlers[0]();

    expect(mockSendBeacon).toHaveBeenCalledTimes(1);
    const [url, blob] = mockSendBeacon.mock.calls[0];
    expect(url).toBe('/api/_log');
    expect((blob as Blob).type).toBe('application/json');
  });

  // 6 — network error re-enqueues items for next flush
  it('network error re-enqueues and sends on next flush', async () => {
    mockFetch.mockRejectedValueOnce(new Error('offline'));
    const shipper = await createShipper();
    shipper.enqueue(envelope('msg1'));
    await shipper.flush();
    expect(mockFetch).toHaveBeenCalledTimes(1);

    mockFetch.mockResolvedValueOnce({ ok: true, status: 200 });
    shipper.enqueue(envelope('msg2'));
    await shipper.flush();
    expect(mockFetch).toHaveBeenCalledTimes(2);
    const body = JSON.parse(mockFetch.mock.calls[1][1].body);
    expect(body.envelopes).toHaveLength(2);
  });

  // 7a — 429 backoff re-enqueues
  it('429 backoff re-enqueues', async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 429 });
    const shipper = await createShipper();
    shipper.enqueue(envelope('rate-limited'));
    await shipper.flush();
    expect(mockFetch).toHaveBeenCalledTimes(1);

    mockFetch.mockResolvedValueOnce({ ok: true, status: 200 });
    shipper.enqueue(envelope('retry'));
    await shipper.flush();
    expect(mockFetch).toHaveBeenCalledTimes(2);
    const body = JSON.parse(mockFetch.mock.calls[1][1].body);
    expect(body.envelopes).toHaveLength(2);
  });

  // 7b — 500 backoff re-enqueues
  it('500 backoff re-enqueues', async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });
    const shipper = await createShipper();
    shipper.enqueue(envelope('server-error'));
    await shipper.flush();
    expect(mockFetch).toHaveBeenCalledTimes(1);

    mockFetch.mockResolvedValueOnce({ ok: true, status: 200 });
    shipper.enqueue(envelope('recovered'));
    await shipper.flush();
    expect(mockFetch).toHaveBeenCalledTimes(2);
    const body = JSON.parse(mockFetch.mock.calls[1][1].body);
    expect(body.envelopes).toHaveLength(2);
  });

  // 8 — constructor registers beforeunload + pagehide listeners
  it('constructor adds beforeunload/pagehide listeners', async () => {
    await createShipper();
    expect(capturedHandlers['beforeunload']?.length).toBeGreaterThanOrEqual(1);
    expect(capturedHandlers['pagehide']?.length).toBeGreaterThanOrEqual(1);
  });

  // 9 — enabled=false skips shipping entirely
  it('enabled=false skips shipping', async () => {
    const shipper = await createShipper({ shipping: false });
    shipper.enqueue(envelope('secret'));
    expect(mockFetch).not.toHaveBeenCalled();
    await shipper.flush();
    expect(mockFetch).not.toHaveBeenCalled();
  });

  // 10 — debug mode flushes immediately (no batching)
  it('debug mode flushes immediately on first enqueue', async () => {
    const shipper = await createShipper({ logLevel: 'debug' });
    shipper.enqueue(envelope('one'));
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it('debug mode flushes each enqueue when awaited between calls', async () => {
    const shipper = await createShipper({ logLevel: 'debug' });

    shipper.enqueue(envelope('first'));
    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Let the async flush() finalise before next enqueue
    await Promise.resolve();

    shipper.enqueue(envelope('second'));
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });
});
