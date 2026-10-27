// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_SCREEN — page-agnostic Today screen suite.
// ROLE: Projects a generated TodayConvergencePayload into the public Today DOM contract.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-SCREEN
// purpose: Render Today transport, access, calculation, target-date copy, content, time, and navigation states without legacy payload fields.
// owns:
//   - components/today-convergence/today-screen.tsx
// inputs: generated TodayConvergencePayload and parent-owned transport/profile callbacks.
// outputs: today-screen root, single-column content stack, and composed public
//   Today block selectors.
// dependencies: packages/contracts/today-convergence.ts, today-convergence child components, existing Paywall, resume-guard.
// side_effects: delegates retry/dismiss callbacks, ordinary sphere navigation, lazy impulse context loading, timezone-aware child formatting, resume detection, and pagehide telemetry.
// emitted_logs: resume-guard events (snapshot/stale reload, loop suppression) and app.pagehide_state beacon.
// invariants: nullable root attributes are omitted; target-date copy comes only from payload.targetDate; preview/locked never render hidden evidence; state=unavailable has no facts.
// failure_policy: transport error and calculation unavailable are separate accessible states; suppressed resume reloads surface as the error state.
// END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-SCREEN

// START_MODULE_MAP: M-TODAY-CONVERGENCE-SCREEN
// public_entrypoints:
//   - TodayScreen
// semantic_blocks:
//   - TRANSPORT: loading, ready, and error root projections.
//   - RESUME_GUARD: installs the client resume detector and maps loop suppression to error UI.
//   - ACCESS_AND_STATE: full, preview, locked, and unavailable projections.
//   - READY_COMPOSITION: one vertical main/context composition with enough width to preserve full event meta rows.
// owned_tests:
//   - __tests__/components/today-convergence/today-screen.test.tsx
// END_MODULE_MAP: M-TODAY-CONVERGENCE-SCREEN

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Paywall } from "@/components/paywall";
import { readSignalFacet } from "@/lib/display/facet-labels";
import { hardReloadWithCacheBuster, installResumeGuard } from "@/lib/grace/resume-guard";
import type {
  TodayConvergenceNarrativeClaim,
  TodayConvergencePayload,
} from "@/packages/contracts/today-convergence";
import type { TodaySpherePagePayload } from "@/packages/contracts/today-sphere-page";
import type { NatalPreviewChart } from "@/lib/contracts/natal";
import { BirthTimeBanner } from "./birth-time-banner";
import { ConvergenceUnifiedList } from "./convergence-unified-list";
import { DayGeneralSky } from "./day-general-sky";
import { HowCalculated } from "./how-calculated";
import {
  ImpulseDrilldownSheet,
  type DrilldownImpulse,
  type ImpulseDrilldownGroup,
} from "./impulse-drilldown-sheet";
import { ImpulsesList } from "./impulses-list";
import { MainEvent } from "./main-event";
import { PeriodContext } from "./period-context";
import { SphereNavigator } from "./sphere-navigator";
import { TodayLookahead } from "./today-lookahead";
import { TodayNarrative } from "./today-narrative";
import { TodayUnavailable } from "./today-unavailable";
import { formatTargetDateRu, getTodaySphereLabel } from "./today-formatters";

export type TodayScreenState = "loading" | "ready" | "error";

export type TodayScreenProps = {
  payload: TodayConvergencePayload;
  screenState?: TodayScreenState;
  onRetry?: () => void;
  /** Called on resume when the local calendar date changed since mount. */
  onDateRollover?: () => void;
  birthTimeDismissed?: boolean;
  onBirthTimeDismiss?: () => void;
  /** Prototype seam (sandbox only): fixture-provided sphere context payloads replacing the /api/spheres fetch. */
  sphereContexts?: Record<string, TodaySpherePagePayload>;
  /** Prototype seam (sandbox only): natal chart data for the HowCalculated wheel. */
  natalChart?: NatalPreviewChart | null;
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

function drilldownGroup(
  payload: TodayConvergencePayload,
  sphere: string,
): ImpulseDrilldownGroup | null {
  const events = payload.events.filter((event) => event.sphere === sphere);
  const eventIds = new Set(events.map((event) => event.id));
  const selected: DrilldownImpulse[] = payload.impulses.filter((impulse) => impulse.sphere === sphere);
  if (payload.mainEvent?.sphere === sphere && !selected.some((item) => item.eventId === payload.mainEvent?.eventId)) {
    selected.unshift(payload.mainEvent);
  }
  for (const event of events) {
    if (selected.some((item) => item.eventId === event.id)) continue;
    selected.push({
      eventId: event.id,
      sphere: event.sphere,
      facet: readSignalFacet(event),
      polarity: event.polarity,
      evidenceLevel: event.evidenceLevel,
      time: event.time,
      summary: null,
      meaning: null,
      action: null,
    });
  }
  const impulses = selected.filter((item) => eventIds.size === 0 || eventIds.has(item.eventId));
  return { sphere, impulses, events };
}

function PreviewTeaser({ payload }: { payload: TodayConvergencePayload }) {
  const spheres = payload.previewTeaser?.spheres ?? [];
  const targetDateLabel = formatTargetDateRu(payload.targetDate);
  return (
    <section data-testid="today-preview-teaser" className="rounded-[24px] border border-border/60 bg-card p-5">
      <p className="text-[12px] font-medium uppercase tracking-[0.14em] text-muted-foreground">В фокусе {targetDateLabel}</p>
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
function TransportLoading({ pending = false }: { pending?: boolean }) {
  return (
    <div
      data-testid="today-loading-skeleton"
      role="status"
      aria-live="polite"
      aria-label={pending ? "Считаем день, собираем разбор" : "Считаем день"}
      className="space-y-3"
    >
      <p className="text-[13px] font-medium text-muted-foreground">Считаем день…</p>
      {pending ? (
        <p className="text-[13px] text-muted-foreground">Собираем разбор, ещё немного…</p>
      ) : null}
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
      <div className="mt-4 flex flex-col gap-2 sm:flex-row">
        <button
          type="button"
          data-testid="today-error-retry"
          aria-label="Повторить"
          onClick={() => onRetry?.()}
          className="min-h-11 rounded-full border border-border/70 bg-background px-5 text-[13px] font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          Повторить
        </button>
        <button
          type="button"
          data-testid="today-error-reload"
          aria-label="Обновить полностью"
          onClick={() => hardReloadWithCacheBuster()}
          className="min-h-11 rounded-full border border-border/70 bg-background px-5 text-[13px] font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          Обновить полностью
        </button>
      </div>
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
  sphereContexts,
  natalChart,
}: Omit<TodayScreenProps, "screenState">) {
  const [openSphere, setOpenSphere] = useState<string | null>(null);
  const claims = narrativeClaims(payload);
  const isUnavailable = payload.state === "unavailable";
  const isLocked = payload.access.state === "locked";
  const isPreview = payload.access.state === "preview";
  const isFullCalculation = payload.access.state === "full" && !isUnavailable;
  const activeGroup = openSphere ? drilldownGroup(payload, openSphere) : null;

  return (
    <div
      data-testid="today-content-stack"
      data-layout="single-column"
      className="mx-auto flex w-full max-w-[1120px] flex-col items-stretch gap-6 px-5 py-5"
    >
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
          <ConvergenceUnifiedList
            groups={payload.convergences}
            events={payload.events}
            targetDate={payload.targetDate}
            timezone={payload.timezone}
            contentState={payload.contentState}
            onOpenDrilldown={setOpenSphere}
            onRetry={onRetry}
          />
        ) : null}

        {!isUnavailable && !isLocked && !isPreview && payload.state === "quiet_day" ? (
          <>
            {payload.mainEvent ? (
              <MainEvent
                event={payload.mainEvent}
                timezone={payload.timezone}
                onOpenDrilldown={setOpenSphere}
              />
            ) : null}
            <ImpulsesList
              impulses={payload.impulses}
              events={payload.events}
              timezone={payload.timezone}
              onOpenDrilldown={setOpenSphere}
            />
            <TodayNarrative state={payload.contentState} claims={claims} onRetry={onRetry} />
            {payload.lookahead ? <TodayLookahead lookahead={payload.lookahead} /> : null}
          </>
        ) : null}
      </div>

      <aside
        data-testid="today-layout-rail"
        aria-label="Дополнительный контекст дня"
        className="min-w-0 space-y-4"
      >
        {payload.periodContext ? <PeriodContext context={payload.periodContext} /> : null}
        <SphereNavigator payload={payload} onOpenDrilldown={setOpenSphere} />
        {isFullCalculation ? <HowCalculated payload={payload} chart={natalChart} /> : null}
      </aside>
      {activeGroup ? (
        <ImpulseDrilldownSheet
          group={activeGroup}
          targetDate={payload.targetDate}
          timezone={payload.timezone}
          contextOverride={sphereContexts?.[activeGroup.sphere]}
          onClose={() => setOpenSphere(null)}
        />
      ) : null}
    </div>
  );
}
// END_BLOCK: ACCESS_AND_STATE

// START_BLOCK: READY_COMPOSITION
export function TodayScreen({
  payload,
  screenState = "ready",
  onRetry,
  onDateRollover,
  birthTimeDismissed = false,
  onBirthTimeDismiss,
  sphereContexts,
  natalChart,
}: TodayScreenProps) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-SCREEN.TodayScreen
  // purpose: Project transport and generated Today state into the public screen DOM contract.
  // inputs: payload — generated wire envelope; screenState — transport state; callbacks — parent-owned actions.
  // returns: Today screen root with state-specific child composition.
  // side_effects: delegates retry/dismiss and link navigation; installs resume detection and pagehide telemetry.
  // emitted_logs: delegated resume-guard events and app.pagehide_state.
  // error_behavior: loading/error render transport-only content; ready renders payload projection.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-SCREEN.TodayScreen
  const [resumeSuppressed, setResumeSuppressed] = useState(false);
  const screenStateRef = useRef(screenState);
  const effectiveScreenStateRef = useRef<TodayScreenState>(screenState);
  const onRetryRef = useRef(onRetry);
  const onDateRolloverRef = useRef(onDateRollover);

  useEffect(() => {
    screenStateRef.current = screenState;
    effectiveScreenStateRef.current = resumeSuppressed ? "error" : screenState;
  }, [screenState, resumeSuppressed]);

  useEffect(() => {
    onRetryRef.current = onRetry;
  }, [onRetry]);

  useEffect(() => {
    onDateRolloverRef.current = onDateRollover;
  }, [onDateRollover]);

  useEffect(
    () =>
      installResumeGuard({
        isReady: () => screenStateRef.current === "ready",
        refetch: () => onRetryRef.current?.(),
        onReloadSuppressed: () => setResumeSuppressed(true),
        getScreenState: () => effectiveScreenStateRef.current,
        ...(onDateRollover
          ? { onDateRollover: () => onDateRolloverRef.current?.() }
          : {}),
      }),
    [onDateRollover],
  );

  useEffect(() => {
    if (screenState === "ready") setResumeSuppressed(false);
  }, [screenState]);

  const effectiveScreenState = resumeSuppressed ? "error" : screenState;
  const isReady = effectiveScreenState === "ready";
  const handleRetry = useCallback(() => {
    setResumeSuppressed(false);
    onRetry?.();
  }, [onRetry]);

  return (
    <section
      data-testid="today-screen"
      data-screen-state={effectiveScreenState}
      data-state={isReady ? payload.state ?? undefined : undefined}
      data-day-tone={isReady ? payload.dayTone ?? undefined : undefined}
      data-content-state={isReady ? payload.contentState : undefined}
      data-access-state={isReady ? payload.access.state : undefined}
      data-birth-time-mode={isReady ? payload.birthTime.mode : undefined}
      role={effectiveScreenState === "error" ? "alert" : undefined}
      aria-busy={effectiveScreenState === "loading" ? true : undefined}
      aria-label="Разбор дня"
      className="min-h-full bg-background text-foreground"
    >
      {effectiveScreenState === "loading" ? (
        <TransportLoading pending={payload.contentState === "pending"} />
      ) : null}
      {effectiveScreenState === "error" ? <TransportError onRetry={handleRetry} /> : null}
      {isReady ? (
        <ReadyContent
          payload={payload}
          onRetry={handleRetry}
          birthTimeDismissed={birthTimeDismissed}
          onBirthTimeDismiss={onBirthTimeDismiss}
          sphereContexts={sphereContexts}
          natalChart={natalChart}
        />
      ) : null}
    </section>
  );
}
// END_BLOCK: READY_COMPOSITION
