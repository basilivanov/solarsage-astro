// ############################################################################
// AI_HEADER: TEST_FIXTURES_TODAY_CONVERGENCE_V2 — canonical Today and Yesterday fixture barrel.
// ROLE: Exposes the immutable JSON fixture matrix with generated contract types.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-FIXTURES
// purpose: Provide one typed import surface for the 16 Today and 3 Yesterday wire fixtures.
// owns:
//   - __tests__/fixtures/today_convergence_v2/*.json
//   - __tests__/fixtures/today_convergence_v2/index.ts
// inputs: JSON fixtures committed beside this barrel.
// outputs: typed named fixtures and grouped fixture arrays.
// dependencies: packages/contracts/today-convergence.ts, packages/contracts/index.ts.
// side_effects: none.
// emitted_logs: none.
// invariants: named exports preserve the exact 16+3 fixture matrix and generated wire types.
// failure_policy: TypeScript compilation fails when a fixture drifts from its generated type.
// END_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-FIXTURES

// START_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-FIXTURES
// public_entrypoints:
//   - 16 named Today fixture exports
//   - 3 named Yesterday fixture exports
//   - todayConvergenceFixtures
//   - yesterdayFixtures
// semantic_blocks:
//   - TODAY_FIXTURES: typed Today Convergence payloads.
//   - YESTERDAY_FIXTURES: typed check-in/forecast response payloads.
// owned_tests:
//   - __tests__/contracts/today-convergence-fixtures.test.ts
// END_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-FIXTURES

import type { YesterdayCheckinResponse } from "@/packages/contracts";
import type { TodayConvergencePayload } from "@/packages/contracts/today-convergence";

import heroSupportiveJson from "./01_hero_supportive.json";
import heroTenseJson from "./02_hero_tense.json";
import heroMixedJson from "./03_hero_mixed.json";
import heroThreeSpheresJson from "./04_hero_three_spheres.json";
import quietSteadyJson from "./05_quiet_steady.json";
import quietTenseImpulseJson from "./06_quiet_tense_impulse.json";
import quietZeroImpulsesJson from "./07_quiet_zero_impulses.json";
import quietMainMaxJson from "./08_quiet_main_max.json";
import quietGeneralBackgroundJson from "./09_quiet_general_background.json";
import contentPendingJson from "./10_content_pending.json";
import contentUnavailableJson from "./11_content_unavailable.json";
import stateUnavailableJson from "./12_state_unavailable.json";
import birthBucketJson from "./13_birth_bucket.json";
import birthUnknownJson from "./14_birth_unknown.json";
import accessPreviewJson from "./15_access_preview.json";
import accessLockedJson from "./16_access_locked.json";
import yesterdayPreSubmitJson from "./yesterday_pre_submit.json";
import yesterdayPostSubmitJson from "./yesterday_post_submit.json";
import yesterdayNoSnapshotJson from "./yesterday_no_snapshot.json";

// START_BLOCK: TODAY_FIXTURES
// JSON module imports widen wire enum literals to `string`; the validator test
// below is the runtime guard, while these casts keep the public barrel typed.
export const heroSupportive: TodayConvergencePayload = heroSupportiveJson as TodayConvergencePayload;
export const heroTense: TodayConvergencePayload = heroTenseJson as TodayConvergencePayload;
export const heroMixed: TodayConvergencePayload = heroMixedJson as TodayConvergencePayload;
export const heroThreeSpheres: TodayConvergencePayload = heroThreeSpheresJson as TodayConvergencePayload;
export const quietSteady: TodayConvergencePayload = quietSteadyJson as TodayConvergencePayload;
export const quietTenseImpulse: TodayConvergencePayload = quietTenseImpulseJson as TodayConvergencePayload;
export const quietZeroImpulses: TodayConvergencePayload = quietZeroImpulsesJson as TodayConvergencePayload;
export const quietMainMax: TodayConvergencePayload = quietMainMaxJson as TodayConvergencePayload;
export const quietGeneralBackground: TodayConvergencePayload = quietGeneralBackgroundJson as TodayConvergencePayload;
export const contentPending: TodayConvergencePayload = contentPendingJson as TodayConvergencePayload;
export const contentUnavailable: TodayConvergencePayload = contentUnavailableJson as TodayConvergencePayload;
export const stateUnavailable: TodayConvergencePayload = stateUnavailableJson as TodayConvergencePayload;
export const birthBucket: TodayConvergencePayload = birthBucketJson as TodayConvergencePayload;
export const birthUnknown: TodayConvergencePayload = birthUnknownJson as TodayConvergencePayload;
export const accessPreview: TodayConvergencePayload = accessPreviewJson as TodayConvergencePayload;
export const accessLocked: TodayConvergencePayload = accessLockedJson as TodayConvergencePayload;

export const todayConvergenceFixtures: readonly TodayConvergencePayload[] = [
  heroSupportive,
  heroTense,
  heroMixed,
  heroThreeSpheres,
  quietSteady,
  quietTenseImpulse,
  quietZeroImpulses,
  quietMainMax,
  quietGeneralBackground,
  contentPending,
  contentUnavailable,
  stateUnavailable,
  birthBucket,
  birthUnknown,
  accessPreview,
  accessLocked,
];
// END_BLOCK: TODAY_FIXTURES

// START_BLOCK: YESTERDAY_FIXTURES
export const yesterdayPreSubmit: YesterdayCheckinResponse = yesterdayPreSubmitJson as YesterdayCheckinResponse;
export const yesterdayPostSubmit: YesterdayCheckinResponse = yesterdayPostSubmitJson as YesterdayCheckinResponse;
export const yesterdayNoSnapshot: YesterdayCheckinResponse = yesterdayNoSnapshotJson as YesterdayCheckinResponse;

export const yesterdayFixtures: readonly YesterdayCheckinResponse[] = [
  yesterdayPreSubmit,
  yesterdayPostSubmit,
  yesterdayNoSnapshot,
];
// END_BLOCK: YESTERDAY_FIXTURES
