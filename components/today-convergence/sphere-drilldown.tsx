// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_SPHERE_DRILLDOWN — deterministic sphere evidence view.
// ROLE: Projects one published snapshot sphere into an accessible evidence chain with explicit timing and polarity.
// ############################################################################

// START_MODULE_CONTRACT: M-SPHERE-DRILLDOWN
// purpose: Render loading, honest error/access states, or the deterministic drilldown for one snapshot sphere.
// owns:
//   - components/today-convergence/sphere-drilldown.tsx
// inputs: generated TodaySphereDrilldownPayload, route sphere key, transport state, and retry callback.
// outputs: sphere-drilldown root, numbered evidence events, convergence reason, and calculation disclosure.
// dependencies: generated contracts, Today formatters, Paywall, HowCalculated.
// side_effects: delegates retry and paywall actions; local disclosure state lives in HowCalculated.
// emitted_logs: none.
// invariants: evidence is rendered only from the generated payload; polarity is textual as well as structural; no LLM fields are read.
// failure_policy: 403 renders access/paywall, 404 renders unavailable, other failures render retryable transport error.
// END_MODULE_CONTRACT: M-SPHERE-DRILLDOWN

// START_MODULE_MAP: M-SPHERE-DRILLDOWN
// public_entrypoints:
//   - SphereDrilldown
// semantic_blocks:
//   - TRANSPORT: loading and error/access projections.
//   - EVIDENCE_CHAIN: numbered event chain with timing and polarity.
//   - CONVERGENCE_CONTEXT: deterministic relationship and sphere context.
// owned_tests:
//   - __tests__/components/today-convergence/sphere-drilldown.test.tsx
// END_MODULE_MAP: M-SPHERE-DRILLDOWN

"use client";

import { Paywall } from "@/components/paywall";
import { HowCalculated } from "@/components/today-convergence/how-calculated";
import type { TodaySphereDrilldownPayload } from "@/packages/contracts";
import { CANONICAL_PRODUCT_ORDER } from "@/lib/display/sphere-labels";
import {
  formatEventTime,
  getPolarityLabel,
} from "@/components/today-convergence/today-formatters";

export type SphereDrilldownScreenState = "loading" | "ready" | "error";

export type SphereDrilldownProps = {
  payload?: TodaySphereDrilldownPayload;
  sphereKey?: string;
  screenState?: SphereDrilldownScreenState;
  errorStatus?: number;
  onRetry?: () => void;
};

function sphereLabel(key: string | undefined): string {
  return CANONICAL_PRODUCT_ORDER.find((sphere) => sphere.key === key)?.label ?? "Сфера";
}

function eventKindLabel(kind: string): string {
  if (kind === "aspect") return "Аспект";
  if (kind === "structural") return "Структурное событие";
  return "Событие";
}

function RetryState({
  testId,
  title,
  description,
  onRetry,
}: {
  testId: string;
  title: string;
  description: string;
  onRetry?: () => void;
}) {
  return (
    <section data-testid={testId} className="rounded-[24px] border border-border/60 bg-card/70 p-5 shadow-sm">
      <h1 className="font-serif text-[24px] leading-tight">{title}</h1>
      <p className="mt-2 text-[14px] leading-6 text-muted-foreground">{description}</p>
      <button
        type="button"
        onClick={() => onRetry?.()}
        className="mt-5 min-h-11 rounded-full border border-border/70 bg-background px-5 text-[13px] font-medium transition hover:border-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary motion-reduce:transition-none"
      >
        Повторить
      </button>
    </section>
  );
}

// START_BLOCK: TRANSPORT
function TransportContent({
  screenState,
  errorStatus,
  onRetry,
}: Pick<SphereDrilldownProps, "screenState" | "errorStatus" | "onRetry">) {
  if (screenState === "loading") {
    return (
      <div data-testid="sphere-drilldown-loading" role="status" aria-label="Загружаем объяснение сферы" className="space-y-3">
        <span aria-hidden className="block h-8 w-3/5 animate-pulse rounded bg-muted motion-reduce:animate-none" />
        <span aria-hidden className="block h-28 w-full animate-pulse rounded-[24px] bg-muted motion-reduce:animate-none" />
        <span aria-hidden className="block h-20 w-full animate-pulse rounded-2xl bg-muted motion-reduce:animate-none" />
      </div>
    );
  }

  if (errorStatus === 403) {
    return (
      <section data-testid="sphere-drilldown-access" className="space-y-4 rounded-[24px] border border-border/60 bg-card/70 p-5 shadow-sm">
        <h1 className="font-serif text-[24px] leading-tight">Нужен полный доступ</h1>
        <p className="text-[14px] leading-6 text-muted-foreground">
          Доказательная цепочка доступна в полном разборе дня.
        </p>
        <Paywall
          compact
          title="Открой доказательства дня"
          description="Полный доступ покажет события, время и основание связи."
        />
      </section>
    );
  }

  if (errorStatus === 404) {
    return (
      <RetryState
        testId="sphere-drilldown-unavailable"
        title="Разбор недоступен"
        description="Этот snapshot или сфера больше недоступны."
        onRetry={onRetry}
      />
    );
  }

  return (
    <RetryState
      testId="sphere-drilldown-error"
      title="Не удалось загрузить объяснение"
      description="Попробуйте запросить доказательную цепочку ещё раз."
      onRetry={onRetry}
    />
  );
}
// END_BLOCK: TRANSPORT

// START_BLOCK: EVIDENCE_CHAIN
function EvidenceChain({ payload }: { payload: TodaySphereDrilldownPayload }) {
  return (
    <section data-testid="drilldown-evidence" className="space-y-3">
      <h2 className="text-[12px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Доказательная цепочка
      </h2>
      <ol className="space-y-3">
        {payload.events.map((event, index) => (
          <li
            key={event.id}
            data-testid={`drilldown-event-${event.id}`}
            data-polarity={event.polarity}
            data-event-kind={event.kind}
            className="rounded-[20px] border border-border/60 bg-card p-4 shadow-sm"
          >
            <div className="flex items-start gap-3">
              <span aria-hidden className="flex h-7 w-7 flex-none items-center justify-center rounded-full bg-secondary text-[13px] font-medium">
                {index + 1}
              </span>
              <div className="min-w-0">
                <p className="text-[14px] font-medium text-foreground">
                  {eventKindLabel(event.kind)} · {sphereLabel(event.sphere)}
                </p>
                <p className="mt-1 text-[13px] leading-5 text-muted-foreground tabular-nums">
                  <span data-testid={`drilldown-event-time-${event.id}`}>{formatEventTime(event.time)}</span>
                  {" · "}
                  <span data-testid={`drilldown-event-polarity-${event.id}`}>
                    {getPolarityLabel(event.polarity)}
                  </span>
                </p>
                <p className="mt-2 text-[13px] leading-5 text-foreground/85">
                  Это событие несёт смысл «{getPolarityLabel(event.polarity)}» для сферы «{sphereLabel(event.sphere)}».
                </p>
              </div>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
// END_BLOCK: EVIDENCE_CHAIN

// START_BLOCK: CONVERGENCE_CONTEXT
function ConvergenceContext({ payload }: { payload: TodaySphereDrilldownPayload }) {
  const convergence = payload.convergence;
  const secondary = convergence?.secondarySphere;

  return (
    <>
      {convergence ? (
        <section
          data-testid="drilldown-convergence"
          data-polarity={convergence.polarity}
          className="rounded-[20px] border border-border/60 bg-card p-4 shadow-sm"
        >
          <h2 className="text-[14px] font-medium">Основание связи</h2>
          <p className="mt-2 text-[13px] leading-5 text-muted-foreground">
            {sphereLabel(convergence.primarySphere)}
            {secondary ? ` и ${sphereLabel(secondary)}` : ""} связаны двумя или более детерминированными событиями.
          </p>
          <p className="mt-2 text-[12px] text-muted-foreground">
            Уровень evidence: {convergence.evidenceLevel} · событий: {convergence.eventIds.length}
          </p>
        </section>
      ) : null}

      <section data-testid="drilldown-context" className="rounded-[20px] border border-border/60 bg-card/70 p-4 shadow-sm">
        <h2 className="text-[14px] font-medium">Контекст сферы</h2>
        <p className="mt-2 text-[13px] leading-5 text-muted-foreground">
          Цепочка относится к опубликованному snapshot и не заменяет исходные события расчёта.
        </p>
      </section>
    </>
  );
}
// END_BLOCK: CONVERGENCE_CONTEXT

// START_BLOCK: READY_SCREEN
export function SphereDrilldown({
  payload,
  sphereKey,
  screenState = "ready",
  errorStatus,
  onRetry,
}: SphereDrilldownProps) {
  // START_FUNCTION_CONTRACT: F-M-SPHERE-DRILLDOWN.SphereDrilldown
  // purpose: Render the transport state or deterministic evidence chain for one sphere.
  // inputs: payload — generated drilldown envelope; sphereKey — route key; screenState/errorStatus — transport projection; onRetry — retry callback.
  // returns: accessible sphere drilldown root.
  // side_effects: delegates retry/paywall actions and local calculation disclosure.
  // emitted_logs: none.
  // error_behavior: missing ready payload degrades to a retryable unavailable state.
  // END_FUNCTION_CONTRACT: F-M-SPHERE-DRILLDOWN.SphereDrilldown
  const resolvedSphere = sphereKey ?? payload?.sphere;
  const ready = screenState === "ready" && payload !== undefined;
  const renderedScreenState: SphereDrilldownScreenState = ready
    ? "ready"
    : screenState === "ready"
      ? "error"
      : screenState;
  const dataState = renderedScreenState === "loading"
    ? "loading"
    : renderedScreenState === "ready"
      ? payload?.state
      : errorStatus === 403
        ? "locked"
        : errorStatus === 404
          ? "empty"
          : "error";

  return (
    <main
      data-testid="sphere-drilldown"
      data-sphere={resolvedSphere}
      data-screen-state={renderedScreenState}
      data-state={dataState}
      data-day-tone={ready ? payload.dayTone : undefined}
      data-birth-time-mode={ready ? payload.birthTimeMode : undefined}
      role={renderedScreenState === "error" ? "alert" : undefined}
      aria-busy={renderedScreenState === "loading" ? true : undefined}
      aria-label="Объяснение сферы"
      className="min-h-full bg-background text-foreground"
    >
      <div className="mx-auto flex w-full max-w-[640px] flex-col gap-5 px-5 py-8">
        {renderedScreenState !== "ready" ? (
          <TransportContent screenState={renderedScreenState} errorStatus={errorStatus} onRetry={onRetry} />
        ) : null}
        {ready ? (
          <>
            <header>
              <p className="text-[12px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                Почему сошлось
              </p>
              <h1 className="mt-2 font-serif text-[28px] leading-tight">
                {sphereLabel(payload.sphere)} — сегодня
              </h1>
            </header>
            <EvidenceChain payload={payload} />
            <ConvergenceContext payload={payload} />
            <HowCalculated />
          </>
        ) : null}
      </div>
    </main>
  );
}
// END_BLOCK: READY_SCREEN
