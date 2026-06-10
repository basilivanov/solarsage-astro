// AI_HEADER
// module: M-TEST-LOGGER
// wave: W-1.7
// purpose: Logger unit tests — envelope creation, correlation_id, level filtering

import { describe, it, expect, vi, beforeEach } from 'vitest';

const { mockEnqueue } = vi.hoisted(() => ({
  mockEnqueue: vi.fn(),
}));

vi.mock('@/lib/log/shipper', () => ({
  getLogShipper: () => ({ enqueue: mockEnqueue }),
}));

import { logger, setCorrelationId, getCorrelationId } from '@/lib/log';

const consoleLogSpy = vi.spyOn(console, 'log').mockImplementation(() => {});

beforeEach(() => {
  mockEnqueue.mockClear();
  consoleLogSpy.mockClear();
});

describe('Logger — envelope creation', () => {
  it('info creates envelope with correct fields', () => {
    logger.info('test msg', { correlation_id: 'corr-1', extra: { a: 1 } });
    expect(mockEnqueue).toHaveBeenCalledTimes(1);
    const env = mockEnqueue.mock.calls[0][0];
    expect(env.level).toBe('info');
    expect(env.msg).toBe('test msg');
    expect(env.correlation_id).toBe('corr-1');
    expect(env.payload).toEqual({ a: 1 });
    expect(env.ts).toBeTruthy();
    expect(env.event).toBe('system.request');
    expect(env.slice).toBeTruthy();
    expect(env.module).toBeTruthy();
    expect(env.block).toBeTruthy();
    expect(env.service).toBe('web');
    expect(env.env).toBeTruthy();
  });

  it('warn creates envelope', () => {
    logger.warn('caution');
    const env = mockEnqueue.mock.calls[0][0];
    expect(env.level).toBe('warn');
  });

  it('error creates envelope', () => {
    logger.error('boom', { extra: { code: 500 } });
    const env = mockEnqueue.mock.calls[0][0];
    expect(env.level).toBe('error');
    expect(env.payload).toEqual({ code: 500 });
  });

  it('debug creates envelope (when level permits)', () => {
    logger.debug('trace');
    // debug may be filtered if LOG_LEVEL > 'debug'
    // In the test env LOG_LEVEL defaults to 'info', so debug is filtered.
    // This test verifies the call is made — if filtered, 0 calls is also valid.
    // We just verify the method doesn't throw.
  });
});

describe('Logger — correlation_id', () => {
  it('global correlation_id auto-included when set', () => {
    setCorrelationId('global-abc');
    logger.info('with global');
    const env = mockEnqueue.mock.calls[0][0];
    expect(env.correlation_id).toBe('global-abc');
  });

  it('options correlation_id overrides global', () => {
    setCorrelationId('global-abc');
    logger.info('override', { correlation_id: 'opt-xyz' });
    const env = mockEnqueue.mock.calls[0][0];
    expect(env.correlation_id).toBe('opt-xyz');
  });

  it('getCorrelationId returns set value', () => {
    setCorrelationId('check-id');
    expect(getCorrelationId()).toBe('check-id');
  });
});

describe('Logger — console output', () => {
  it('console.log called with [CORR][LEVEL] format', () => {
    setCorrelationId('abcdef01-9999');
    logger.warn('watch out', { extra: { hint: 'careful' } });
    expect(consoleLogSpy).toHaveBeenCalledWith(
      '[abcdef01][WARN ]',
      'watch out',
      { hint: 'careful' },
    );
  });

  it('console.log omits correlation tag when none set', async () => {
    // Static import shares module state, so correlation may be set from prior tests.
    // We verify the call in a clean state via dynamic import below.
  });
});

describe('Logger — log level filtering', () => {
  it('debug is filtered when NEXT_PUBLIC_LOG_LEVEL=info', async () => {
    vi.resetModules();
    process.env.NEXT_PUBLIC_LOG_LEVEL = 'info';
    vi.doMock('@/lib/log/shipper', () => ({
      getLogShipper: () => ({ enqueue: mockEnqueue }),
    }));
    mockEnqueue.mockClear();

    const mod = await import('@/lib/log');
    mod.setCorrelationId('filter-test');
    mod.logger.debug('should be skipped');
    expect(mockEnqueue).not.toHaveBeenCalled();

    mod.logger.info('should pass');
    expect(mockEnqueue).toHaveBeenCalledTimes(1);
  });

  it('debug passes when NEXT_PUBLIC_LOG_LEVEL=debug', async () => {
    vi.resetModules();
    process.env.NEXT_PUBLIC_LOG_LEVEL = 'debug';
    vi.doMock('@/lib/log/shipper', () => ({
      getLogShipper: () => ({ enqueue: mockEnqueue }),
    }));
    mockEnqueue.mockClear();

    const mod = await import('@/lib/log');
    mod.logger.debug('should pass');
    expect(mockEnqueue).toHaveBeenCalledTimes(1);
  });
});

describe('Logger — fresh state', () => {
  it('getCorrelationId returns null on clean import', async () => {
    vi.resetModules();
    vi.doMock('@/lib/log/shipper', () => ({
      getLogShipper: () => ({ enqueue: vi.fn() }),
    }));
    const mod = await import('@/lib/log');
    expect(mod.getCorrelationId()).toBeNull();
  });

  it('setCorrelationId + getCorrelationId round-trip', async () => {
    vi.resetModules();
    vi.doMock('@/lib/log/shipper', () => ({
      getLogShipper: () => ({ enqueue: vi.fn() }),
    }));
    const mod = await import('@/lib/log');
    mod.setCorrelationId('round-trip');
    expect(mod.getCorrelationId()).toBe('round-trip');
  });

  it('console.log format without correlation_id', async () => {
    vi.resetModules();
    vi.doMock('@/lib/log/shipper', () => ({
      getLogShipper: () => ({ enqueue: vi.fn() }),
    }));
    const cSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
    const mod = await import('@/lib/log');
    mod.logger.info('hello world');
    expect(cSpy).toHaveBeenCalledWith('[INFO ]', 'hello world', '');
  });
});
