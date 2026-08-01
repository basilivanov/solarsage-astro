// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_SCREEN — page-agnostic Today screen suite.
// ROLE: Projects a generated TodayConvergencePayload into the public Today DOM contract.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-SCREEN
// purpose: Render Today transport, access, calculation, content, time, and navigation states without legacy payload fields.
// owns:
//   - components/today-convergence/today-screen.tsx
// inputs: generated TodayConvergencePayload and parent-owned transport/profile callbacks.
// outputs: today-screen root and composed public Today block selectors.
// dependencies: packages/contracts/today-convergence.ts, today-convergence child components, existing Paywall.
// side_effects: delegates retry/dismiss callbacks and ordinary sphere link navigation.
// emitted_logs: none.
// invariants: nullable root attributes are omitted; preview/locked never render hidden evidence; state=unavailable has no facts.
// failure_policy: transport error and calculation unavailable are separate accessible states.
// END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-SCREEN

// START_MODULE_MAP: M-TODAY-CONVERGENCE-SCREEN
// public_entrypoints:
//   - TodayScreen
// semantic_blocks:
//   - TRANSPORT: loading, ready, and error root projections.
//   - ACCESS_AND_STATE: full, preview, locked, and unavailable projections.
//   - READY_COMPOSITION: hero/main/impulses/context/navigation composition.
// owned_tests:
//   - __tests__/components/today-convergence/today-screen.test.tsx
// END_MODULE_MAP: M-TODAY-CONVERGENCE-SCREEN

"use client";

import { Paywall } from "@/components/paywall";
import type {
  TodayConvergenceNarrativeClaim,
  TodayConvergencePayload,
} from "@/packages/contracts/today-convergence";
import { BirthTimeBanner } from "./birth-time-banner";
import { ConvergenceHero } from "./convergence-hero";
import { DayGeneralSky } from "./day-general-sky";
import { HowCalculated } from "./how-calculated";
import { ImpulsesList } from "./impulses-list";
import { MainEvent } from "./main-event";
import { PeriodContext } from "./period-context";
import { SphereNavigator } from "./sphere-navigator";
import { TodayLookahead } from "./today-lookahead";
import { TodayNarrative } from "./today-narrative";
import { TodayUnavailable } from "./today-unavailable";
import { getTodaySphereLabel } from "./today-formatters";

export type TodayScreenState = "loading" | "ready" | "error";

export type TodayScreenProps = {
  payload: TodayConvergencePayload;
  screenState?: TodayScreenState;
  onRetry?: () => void;
  birthTimeDismissed?: boolean;
  onBirthTimeDismiss?: () => void;
};

function narrativeClaims(payload: TodayConvergencePayload): TodayConvergenceNarrativeClaim[] {
  const claims: TodayConvergenceNarrativeClaim[] = [];
  const add = (claim: TodayConvergenceNarrativeClaim | null | undefined) => {
    if (claim) claims.push(claim);
  };

  for (const group of payload.convergences) {
    add(group.summary);
    add(group.meaning);
    add(group.action);
  }
  // Quiet-day cards own their generated summary text; keep this zone only for
  // pending/unavailable status rather than duplicating inline copy.
  if (payload.state === "quiet_day") return claims;
  if (payload.mainEvent) {
    add(payload.mainEvent.summary);
    add(payload.mainEvent.meaning);
    add(payload.mainEvent.action);
  }
  for (const impulse of payload.impulses) {
    add(impulse.summary);
    add(impulse.meaning);
    add(impulse.action);
  }
  return claims;
}

function PreviewTeaser({ payload }: { payload: TodayConvergencePayload }) {
  const spheres = payload.previewTeaser?.spheres ?? [];
  return (
    <section data-testid="today-preview-teaser" className="rounded-[24px] border border-border/60 bg-card p-5">
      <p className="text-[12px] font-medium uppercase tracking-[0.14em] text-muted-foreground">Сегодня в фокусе</p>
      <ul className="mt-3 flex flex-wrap gap-2">
        {spheres.map((sphere) => (
          <li key={sphere} className="rounded-full border border-border/70 px-3 py-1.5 text-[13px]">
            {getTodaySphereLabel(sphere)}
          </li>
        ))}
      </ul>
    </section>
  );
}

// START_BLOCK: TRANSPORT
function TransportLoading() {
  return (
    <div data-testid="today-loading-skeleton" role="status" aria-live="polite" aria-label="Загружаем разбор дня" className="space-y-3">
      <span aria-hidden className="block h-6 w-2/5 animate-pulse rounded bg-muted motion-reduce:animate-none" />
      <span aria-hidden className="block h-32 w-full animate-pulse rounded-[24px] bg-muted motion-reduce:animate-none" />
      <span aria-hidden className="block h-20 w-full animate-pulse rounded-2xl bg-muted motion-reduce:animate-none" />
    </div>
  );
}

function TransportError({ onRetry }: { onRetry?: () => void }) {
  return (
    <div data-testid="today-transport-error" className="rounded-[24px] border border-border/60 bg-card p-5">
      <p>Не удалось загрузить день.</p>
      <button
        type="button"
        onClick={() => onRetry?.()}
        className="mt-4 min-h-11 rounded-full border border-border/70 bg-background px-5 text-[13px] font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      >
        Повторить
      </button>
    </div>
  );
}
// END_BLOCK: TRANSPORT

// START_BLOCK: ACCESS_AND_STATE
function ReadyContent({
  payload,
  onRetry,
  birthTimeDismissed,
  onBirthTimeDismiss,
}: Omit<TodayScreenProps, "screenState">) {
  const claims = narrativeClaims(payload);
  const isUnavailable = payload.state === "unavailable";
  const isLocked = payload.access.state === "locked";
  const isPreview = payload.access.state === "preview";
  const isFullCalculation = payload.access.state === "full" && !isUnavailable;

  return (
    <div className="mx-auto grid w-full max-w-[1120px] grid-cols-1 items-start gap-6 px-5 py-5 lg:grid-cols-[minmax(0,640px)_minmax(0,400px)] lg:gap-8">
      <div data-testid="today-main-column" className="min-w-0 space-y-4">
        <BirthTimeBanner
          birthTime={payload.birthTime}
          dismissed={birthTimeDismissed}
          onDismiss={onBirthTimeDismiss}
        />
        {payload.personal === false ? <DayGeneralSky /> : null}

        {isUnavailable ? <TodayUnavailable onRetry={onRetry} /> : null}

        {isLocked ? (
          <Paywall
            compact
            title="Открой полный разбор дня"
            description="Персональные события и их объяснение доступны после открытия доступа."
          />
        ) : null}

        {isPreview ? (
          <>
            <PreviewTeaser payload={payload} />
            <Paywall
              compact
              title="Открой полный разбор дня"
              description="Полный порядок событий, времена и объяснения появятся после открытия доступа."
            />
          </>
        ) : null}

        {!isUnavailable && !isLocked && !isPreview && payload.state === "convergence_today" ? (
          <ConvergenceHero
            groups={payload.convergences}
            dayTone={payload.dayTone}
            contentState={payload.contentState}
            onRetry={onRetry}
          />
        ) : null}

        {!isUnavailable && !isLocked && !isPreview && payload.state === "quiet_day" ? (
          <>
            {payload.mainEvent ? <MainEvent event={payload.mainEvent} snapshotId={payload.snapshotId} /> : null}
            <ImpulsesList impulses={payload.impulses} snapshotId={payload.snapshotId} />
            <TodayNarrative state={payload.contentState} claims={claims} onRetry={onRetry} />
            {payload.lookahead ? <TodayLookahead lookahead={payload.lookahead} /> : null}
          </>
        ) : null}
      </div>

      <aside
        data-testid="today-layout-rail"
        aria-label="Дополнительный контекст дня"
        className="min-w-0 space-y-4 lg:sticky lg:top-5 lg:self-start"
      >
        {payload.periodContext ? <PeriodContext context={payload.periodContext} /> : null}
        <SphereNavigator payload={payload} rail />
        {isFullCalculation ? <HowCalculated /> : null}
      </aside>
    </div>
  );
}
// END_BLOCK: ACCESS_AND_STATE

// START_BLOCK: READY_COMPOSITION
export function TodayScreen({
  payload,
  screenState = "ready",
  onRetry,
  birthTimeDismissed = false,
  onBirthTimeDismiss,
}: TodayScreenProps) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-SCREEN.TodayScreen
  // purpose: Project transport and generated Today state into the public screen DOM contract.
  // inputs: payload — generated wire envelope; screenState — transport state; callbacks — parent-owned actions.
  // returns: Today screen root with state-specific child composition.
  // side_effects: delegates retry/dismiss and link navigation.
  // emitted_logs: none.
  // error_behavior: loading/error render transport-only content; ready renders payload projection.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-SCREEN.TodayScreen
  const isReady = screenState === "ready";

  return (
    <section
      data-testid="today-screen"
      data-screen-state={screenState}
      data-state={isReady ? payload.state ?? undefined : undefined}
      data-day-tone={isReady ? payload.dayTone ?? undefined : undefined}
      data-content-state={isReady ? payload.contentState : undefined}
      data-access-state={isReady ? payload.access.state : undefined}
      data-birth-time-mode={isReady ? payload.birthTime.mode : undefined}
      role={screenState === "error" ? "alert" : undefined}
      aria-busy={screenState === "loading" ? true : undefined}
      aria-label="Разбор дня"
      className="min-h-full bg-background text-foreground"
    >
      {screenState === "loading" ? <TransportLoading /> : null}
      {screenState === "error" ? <TransportError onRetry={onRetry} /> : null}
      {isReady ? (
        <ReadyContent
          payload={payload}
          onRetry={onRetry}
          birthTimeDismissed={birthTimeDismissed}
          onBirthTimeDismiss={onBirthTimeDismiss}
        />
      ) : null}
    </section>
  );
}
// END_BLOCK: READY_COMPOSITION
