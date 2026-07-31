// ############################################################################
// AI_HEADER: MODULE_APP_SPHERE_DRILLDOWN_PAGE — snapshot sphere evidence route.
// ROLE: Loads one owned published snapshot sphere and projects its transport/error state into the drilldown component.
// ############################################################################

// START_MODULE_CONTRACT: M-APP-SPHERE-DRILLDOWN-PAGE
// purpose: Render /day/snapshots/{id}/spheres/{key} from the generated deterministic drilldown envelope.
// owns:
//   - app/(grace)/day/snapshots/[id]/spheres/[key]/page.tsx
// inputs: Next route snapshot id and canonical sphere key.
// outputs: SphereDrilldown loading, ready, access, unavailable, or retryable error state.
// dependencies: next/navigation, fetchSphereDrilldown, SphereDrilldown.
// side_effects: credentialed GET request and abort on route change/unmount.
// emitted_logs: delegated to fetchSphereDrilldown.
// invariants: route identifiers are sent unchanged to the typed client; ownership/403/404 semantics remain visible.
// failure_policy: 403 and 404 are passed as honest status states; other failures keep a retry action.
// END_MODULE_CONTRACT: M-APP-SPHERE-DRILLDOWN-PAGE

// START_MODULE_MAP: M-APP-SPHERE-DRILLDOWN-PAGE
// public_entrypoints:
//   - SphereDrilldownPage
// semantic_blocks:
//   - ROUTE_PARAMS: normalize route parameters.
//   - LOAD_DRILLDOWN: abort-safe typed fetch and status mapping.
// owned_tests:
//   - __tests__/components/today-convergence/sphere-drilldown.test.tsx
// END_MODULE_MAP: M-APP-SPHERE-DRILLDOWN-PAGE

"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { SphereDrilldown } from "@/components/today-convergence/sphere-drilldown";
import {
  fetchSphereDrilldown,
  TodayConvergenceApiError,
} from "@/lib/api/today-convergence";

// START_BLOCK: ROUTE_PARAMS
export default function SphereDrilldownPage() {
  // START_FUNCTION_CONTRACT: F-M-APP-SPHERE-DRILLDOWN-PAGE.SphereDrilldownPage
  // purpose: Resolve route identifiers and render the snapshot sphere drilldown lifecycle.
  // inputs: Next route params id and key.
  // returns: SphereDrilldown component with typed transport state.
  // side_effects: delegated GET, abort controller, and retry state.
  // emitted_logs: delegated API lifecycle events.
  // error_behavior: missing route identifiers map to the honest 404 state.
  // END_FUNCTION_CONTRACT: F-M-APP-SPHERE-DRILLDOWN-PAGE.SphereDrilldownPage
  const params = useParams<{ id?: string; key?: string }>();
  const snapshotId = typeof params.id === "string" ? params.id : "";
  const sphereKey = typeof params.key === "string" ? params.key : "";
  const [screenState, setScreenState] = useState<"loading" | "ready" | "error">("loading");
  const [payload, setPayload] = useState<Awaited<ReturnType<typeof fetchSphereDrilldown>>>();
  const [errorStatus, setErrorStatus] = useState<number | undefined>();
  const [retryNonce, setRetryNonce] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setScreenState("loading");
    setPayload(undefined);
    setErrorStatus(undefined);

    if (!snapshotId || !sphereKey) {
      setScreenState("error");
      setErrorStatus(404);
      return () => {
        active = false;
        controller.abort();
      };
    }

    fetchSphereDrilldown(snapshotId, sphereKey, controller.signal)
      .then((nextPayload) => {
        if (!active) return;
        setPayload(nextPayload);
        setScreenState("ready");
      })
      .catch((error: unknown) => {
        if (!active || controller.signal.aborted) return;
        setErrorStatus(error instanceof TodayConvergenceApiError ? error.status : undefined);
        setScreenState("error");
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [retryNonce, snapshotId, sphereKey]);

  return (
    <SphereDrilldown
      payload={payload}
      sphereKey={sphereKey}
      screenState={screenState}
      errorStatus={errorStatus}
      onRetry={() => setRetryNonce((value) => value + 1)}
    />
  );
}
// END_BLOCK: ROUTE_PARAMS
