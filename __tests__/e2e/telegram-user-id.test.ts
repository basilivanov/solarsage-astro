// ############################################################################
// AI_HEADER: MODULE_TEST_TELEGRAM_USER_ID — deriveTelegramUserId contract.
// ROLE: Directed tests for the deterministic E2E Telegram user id derivation.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-TELEGRAM-USER-ID
// purpose: Prove run-salted Telegram user ids are stable for identical inputs
//   and distinct across retry indexes, projects and run salts, with every id
//   recorded in the cleanup ledger.
// owns:
//   - __tests__/e2e/telegram-user-id.test.ts
// inputs: e2e/fixtures.ts deriveTelegramUserId.
// outputs: vitest assertions.
// dependencies: fs, os, path, vitest.
// side_effects: temporary ledger files under the OS temp dir (removed).
// emitted_logs: none.
// invariants:
//   - No Playwright/browser startup; pure function-level assertions.
// failure_policy: fail test.
// END_MODULE_CONTRACT: M-TEST-TELEGRAM-USER-ID

// START_MODULE_MAP: M-TEST-TELEGRAM-USER-ID
// public_entrypoints: describe/it blocks
// semantic_blocks:
//   - ID_DERIVATION_TESTS: stability, retry uniqueness, ledger recording.
// END_MODULE_MAP: M-TEST-TELEGRAM-USER-ID

import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

let dir = '';
let derive: (projectName: string, testId: string, repeatEachIndex: number, retry: number) => number;

beforeAll(async () => {
  dir = mkdtempSync(join(tmpdir(), 'tg-id-test-'));
  process.env.E2E_CREATED_USERS_FILE = join(dir, 'users.jsonl');
  process.env.E2E_RUN_SALT = 'test-salt';
  ({ deriveTelegramUserId: derive } = await import('@/e2e/fixtures'));
});

afterAll(() => {
  if (dir) rmSync(dir, { recursive: true, force: true });
});

describe('deriveTelegramUserId', () => {
  it('is stable for identical inputs and distinct across retry indexes', () => {
    const firstAttempt = derive('chromium', 'spec#case', 0, 0);
    const firstAttemptAgain = derive('chromium', 'spec#case', 0, 0);
    const retryAttempt = derive('chromium', 'spec#case', 0, 1);
    expect(firstAttemptAgain).toBe(firstAttempt);
    expect(retryAttempt).not.toBe(firstAttempt);
  });

  it('is distinct across projects and run salts', () => {
    const chromium = derive('chromium', 'spec#case', 0, 0);
    const mobile = derive('mobile', 'spec#case', 0, 0);
    expect(mobile).not.toBe(chromium);

    process.env.E2E_RUN_SALT = 'other-salt';
    const otherRun = derive('chromium', 'spec#case', 0, 0);
    expect(otherRun).not.toBe(chromium);
    process.env.E2E_RUN_SALT = 'test-salt';
  });

  it('records every derived id in the cleanup ledger', () => {
    const id = derive('chromium', 'spec#ledger', 0, 0);
    const ledger = readFileSync(process.env.E2E_CREATED_USERS_FILE!, 'utf8');
    expect(ledger).toContain(`"tg_user_id":${id}`);
    expect(ledger).toContain('"run_salt":"test-salt"');
  });
});
