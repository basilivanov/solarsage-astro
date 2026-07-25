
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_THEME_PROVIDER
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Module: theme-provider.tsx
// owns:
//   - components/theme-provider.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// public_entrypoints:
//   - ThemeProvider
// semantic_blocks:
//   - THEME_PROVIDER: Next-themes theme provider component
// owned_tests:
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
// END_MODULE_MAP

'use client'

import * as React from 'react'
import {
  ThemeProvider as NextThemesProvider,
  type ThemeProviderProps,
} from 'next-themes'

// START_BLOCK: THEME_PROVIDER
export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>
}
// END_BLOCK: THEME_PROVIDER
