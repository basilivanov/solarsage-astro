
// ############################################################################
// AI_HEADER: MODULE_HOOKS_USE_MOBILE
// ROLE: React hook
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: UI use-mobile — component
// owns:
//   - hooks/use-mobile.ts
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: React state management
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// public_entrypoints:
//   - useIsMobile
// semantic_blocks:
//   - USE_IS_MOBILE_HOOK: Mobile viewport match media hook
// owned_tests:
//   - __tests__/hooks/useToast.test.ts
// END_MODULE_MAP
import * as React from 'react'

const MOBILE_BREAKPOINT = 768

// START_BLOCK: USE_IS_MOBILE_HOOK
export function useIsMobile() {
  const [isMobile, setIsMobile] = React.useState<boolean | undefined>(undefined)

  React.useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)
    const onChange = () => {
      setIsMobile(window.innerWidth < MOBILE_BREAKPOINT)
    }
    mql.addEventListener('change', onChange)
    setIsMobile(window.innerWidth < MOBILE_BREAKPOINT)
    return () => mql.removeEventListener('change', onChange)
  }, [])

  return !!isMobile
}
// END_BLOCK: USE_IS_MOBILE_HOOK
