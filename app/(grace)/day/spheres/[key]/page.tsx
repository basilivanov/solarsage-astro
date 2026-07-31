// ############################################################################
// AI_HEADER: MODULE_APP_SPHERE_PAGE — static sphere page route.
// ROLE: Loads the long-lived sphere payload and projects its public UI states.
// ############################################################################

// START_MODULE_CONTRACT: M-APP-SPHERE-PAGE
// purpose: Render /day/spheres/{key} from the generated static sphere page payload.
// owns:
//   - app/(grace)/day/spheres/[key]/page.tsx
// inputs: Next route sphere key.
// outputs: SpherePage loading, ready, access, unavailable, or retryable error state.
// dependencies: next/navigation, fetchSpherePage, SpherePage.
// side_effects: credentialed GET request and abort on route change/unmount.
// emitted_logs: delegated to fetchSpherePage.
// invariants: the route key is passed to the typed client; 403/422 remain visible to the UI.
// failure_policy: missing keys map to 422; transport failures retain a retry action.
// END_MODULE_CONTRACT: M-APP-SPHERE-PAGE

// START_MODULE_MAP: M-APP-SPHERE-PAGE
// public_entrypoints:
//   - SpherePageRoute
// semantic_blocks:
//   - ROUTE_PARAMS: normalize the dynamic key.
//   - LOAD_SPHERE_PAGE: abort-safe typed fetch and status mapping.
// owned_tests:
//   - __tests__/components/today-convergence/sphere-page.test.tsx
// END_MODULE_MAP: M-APP-SPHERE-PAGE

"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { SpherePage } from "@/components/today-convergence/sphere-page";
import { fetchSpherePage, SpherePageApiError } from "@/lib/api/spheres";

// START_BLOCK: ROUTE_PARAMS
export default function SpherePageRoute() {
  // START_FUNCTION_CONTRACT: F-M-APP-SPHERE-PAGE.SpherePageRoute
  // purpose: Resolve the dynamic sphere key and render its fetch lifecycle.
  // inputs: Next route param key.
  // returns: SpherePage with typed transport state.
  // side_effects: delegated GET, abort controller, and retry state.
  // emitted_logs: delegated API lifecycle events.
  // error_behavior: missing route key maps to the honest 422 unavailable state.
  // END_FUNCTION_CONTRACT: F-M-APP-SPHERE-PAGE.SpherePageRoute
  const params = useParams<{ key?: string }>();
  const sphereKey = typeof params.key === "string" ? params.key : "";
  const [screenState, setScreenState] = useState<"loading" | "ready" | "error">("loading");
  const [payload, setPayload] = useState<Awaited<ReturnType<typeof fetchSpherePage>>>();
  const [errorStatus, setErrorStatus] = useState<number | undefined>();
  const [retryNonce, setRetryNonce] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setScreenState("loading");
    setPayload(undefined);
    setErrorStatus(undefined);

    if (!sphereKey) {
      setScreenState("error");
      setErrorStatus(422);
      return () => {
        active = false;
        controller.abort();
      };
    }

    fetchSpherePage(sphereKey, controller.signal)
      .then((nextPayload) => {
        if (!active) return;
        setPayload(nextPayload);
        setScreenState("ready");
      })
      .catch((error: unknown) => {
        if (!active || controller.signal.aborted) return;
        setErrorStatus(error instanceof SpherePageApiError ? error.status : undefined);
        setScreenState("error");
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [retryNonce, sphereKey]);

  return (
    <SpherePage
      payload={payload}
      sphereKey={sphereKey}
      screenState={screenState}
      errorStatus={errorStatus}
      onRetry={() => setRetryNonce((value) => value + 1)}
    />
  );
}
// END_BLOCK: ROUTE_PARAMS
