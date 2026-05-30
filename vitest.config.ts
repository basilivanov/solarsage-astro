// ############################################################################
// AI_HEADER: MODULE_VITEST_CONFIG
// ROLE: Vitest configuration for frontend GRACE unit tests (W-2.0).
// DEPENDENCIES: vitest, @vitejs/plugin-react
// GRACE_ANCHORS: [TEST_CONFIG]
// ############################################################################

// START_MODULE_CONTRACT: M-WEB-TEST-CONFIG
// purpose: Configure Vitest for frontend unit tests in lib/grace/** and
//   components/grace/**. Enables jsdom environment for React component tests.
// owns:
//   - vitest.config.ts
// inputs:
//   - vitest CLI invocation
// outputs:
//   - test runner configuration
// dependencies:
//   - vitest, @vitejs/plugin-react
// side_effects:
//   - none (config only)
// invariants:
//   - test environment MUST be jsdom for React components
//   - path aliases MUST match tsconfig.json
// failure_policy:
//   - invalid config -> vitest exits with error
// non_goals:
//   - E2E tests, Playwright, backend tests
// END_MODULE_CONTRACT: M-WEB-TEST-CONFIG

// START_MODULE_MAP: M-WEB-TEST-CONFIG
// public_entrypoints:
//   - default export (vitest config)
// semantic_blocks:
//   - TEST_CONFIG
// owned_tests:
//   - __tests__/grace-discipline.test.ts (runs via this config)
// END_MODULE_MAP: M-WEB-TEST-CONFIG

import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

// START_BLOCK: TEST_CONFIG
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['__tests__/**/*.test.ts', '__tests__/**/*.test.tsx'],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './'),
      '@/lib': path.resolve(__dirname, './lib'),
      '@/components': path.resolve(__dirname, './components'),
      '@/packages': path.resolve(__dirname, './packages'),
    },
  },
});
// END_BLOCK: TEST_CONFIG
