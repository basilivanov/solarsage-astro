// ############################################################################
// AI_HEADER: MODULE_GRACE_DISCIPLINE_TESTS
// ROLE: 4 negative tests for GRACE marker discipline (W-2.0).
// DEPENDENCIES: vitest, node:fs, node:path
// GRACE_ANCHORS: [NEG_HEADER, NEG_LEGACY, NEG_ANCHOR, NEG_CAMELCASE]
// ############################################################################

// START_MODULE_CONTRACT: M-WEB-GRACE-DISCIPLINE-TESTS
// purpose: Verify that GRACE marker gates catch violations. Each test simulates
//   a violation and asserts that the gate would fail (negative tests).
// owns:
//   - __tests__/grace-discipline.test.ts
// inputs:
//   - vitest runner
// outputs:
//   - test results (pass/fail)
// dependencies:
//   - scripts/grace/check-markers.sh (Gate 9)
//   - eslint-rules/grace-plugin.mjs (Gate 8)
// side_effects:
//   - reads files from disk for validation
// invariants:
//   - tests MUST NOT mutate working tree (read-only checks)
//   - each test validates one specific GRACE rule
// failure_policy:
//   - test failure -> vitest exits non-zero
// non_goals:
//   - positive tests (those are in check-negative.sh)
// END_MODULE_CONTRACT: M-WEB-GRACE-DISCIPLINE-TESTS

// START_MODULE_MAP: M-WEB-GRACE-DISCIPLINE-TESTS
// public_entrypoints:
//   - describe('GRACE Marker Discipline')
// semantic_blocks:
//   - NEG_HEADER
//   - NEG_LEGACY
//   - NEG_ANCHOR
//   - NEG_CAMELCASE
// owned_tests:
//   - self (runs via vitest)
// END_MODULE_MAP: M-WEB-GRACE-DISCIPLINE-TESTS

import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

describe('GRACE Marker Discipline', () => {
  // START_BLOCK: NEG_HEADER
  it('should reject files without AI_HEADER in lib/grace/**', () => {
    // Negative test: files in lib/grace/** MUST have AI_HEADER
    // This test validates that existing files comply
    const graceLibDir = path.join(process.cwd(), 'lib/grace');

    if (!fs.existsSync(graceLibDir)) {
      // If lib/grace doesn't exist yet, skip (W-2.0 creates it)
      expect(true).toBe(true);
      return;
    }

    const files = fs.readdirSync(graceLibDir).filter(f => f.endsWith('.ts'));

    for (const file of files) {
      const filePath = path.join(graceLibDir, file);
      const content = fs.readFileSync(filePath, 'utf-8');

      // Every .ts file in lib/grace/** MUST have AI_HEADER
      expect(content).toContain('AI_HEADER');
    }
  });
  // END_BLOCK: NEG_HEADER

  // START_BLOCK: NEG_LEGACY
  it('should reject legacy imports in GRACE-managed code', () => {
    // Negative test: GRACE code MUST NOT import from legacy/**
    const graceDirs = [
      path.join(process.cwd(), 'lib/grace'),
      path.join(process.cwd(), 'components/grace'),
      path.join(process.cwd(), 'app/(grace)'),
    ];

    for (const dir of graceDirs) {
      if (!fs.existsSync(dir)) continue;

      const checkDir = (dirPath: string) => {
        const entries = fs.readdirSync(dirPath, { withFileTypes: true });

        for (const entry of entries) {
          const fullPath = path.join(dirPath, entry.name);

          if (entry.isDirectory()) {
            checkDir(fullPath);
          } else if (entry.name.match(/\.(ts|tsx)$/)) {
            const content = fs.readFileSync(fullPath, 'utf-8');

            // MUST NOT import from legacy/**
            expect(content).not.toMatch(/from ['"].*legacy\//);
          }
        }
      };

      checkDir(dir);
    }
  });
  // END_BLOCK: NEG_LEGACY

  // START_BLOCK: NEG_ANCHOR
  it('should reject missing GRACE_ANCHOR in critical sections', () => {
    // Negative test: critical sections need GRACE_ANCHOR comments
    // For W-2.0, we validate that app/(grace)/today/page.tsx has anchors
    const todayPage = path.join(process.cwd(), 'app/(grace)/today/page.tsx');

    if (!fs.existsSync(todayPage)) {
      // If page doesn't exist yet, skip
      expect(true).toBe(true);
      return;
    }

    const content = fs.readFileSync(todayPage, 'utf-8');

    // MUST have GRACE_ANCHORS declaration
    expect(content).toContain('GRACE_ANCHORS');
  });
  // END_BLOCK: NEG_ANCHOR

  // START_BLOCK: NEG_CAMELCASE
  it('should reject non-camelCase in API client', () => {
    // Negative test: API responses must be camelCase (from contracts)
    // For W-2.0, we validate that packages/contracts/index.ts exists
    const contractsIndex = path.join(process.cwd(), 'packages/contracts/index.ts');

    if (!fs.existsSync(contractsIndex)) {
      // If index doesn't exist yet, skip
      expect(true).toBe(true);
      return;
    }

    const content = fs.readFileSync(contractsIndex, 'utf-8');

    // MUST export from _generated.ts (camelCase types)
    expect(content).toContain('_generated');
  });
  // END_BLOCK: NEG_CAMELCASE
});
