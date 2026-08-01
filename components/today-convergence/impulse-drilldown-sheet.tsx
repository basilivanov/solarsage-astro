// ############################################################################
// AI_HEADER: MODULE_TODAY_IMPULSE_DRILLDOWN — human-first impulse modal.
// ROLE: Shows deterministic Today facts immediately and lazy sphere context in a responsive sheet.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-IMPULSE-DRILLDOWN
// purpose: Render one sphere's Today impulse facts in an accessible modal and load optional natal/period context lazily.
// owns:
//   - components/today-convergence/impulse-drilldown-sheet.tsx
// inputs: grouped generated impulses, target date/timezone, snapshot identity, and close callback.
// outputs: role=dialog sheet with deterministic facts, period technique explanations, context transport states, and a context-preserving full-analysis link.
// dependencies: fetchSpherePage; generated Today and sphere contracts; Today formatters.
// side_effects: credentialed GET /api/spheres/{sphere} on open; aborts the request on close/unmount.
// emitted_logs: delegated ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed.
// invariants: Today facts render independently of sphere-context loading/error/403; natal and period facts come only from a successful sphere payload; technique explanations use the exhaustive local registry.
// failure_policy: 403 and transport failures stay inside the context area and never hide the local facts or break the dialog.
// END_MODULE_CONTRACT: M-TODAY-IMPULSE-DRILLDOWN

// START_MODULE_MAP: M-TODAY-IMPULSE-DRILLDOWN
// public_entrypoints:
//   - ImpulseDrilldownSheet
// semantic_blocks:
//   - TODAY_FACTS: sphere heading and one row per deterministic impulse.
//   - SPHERE_CONTEXT: lazy loading, access, error, natal, period, and technique-copy projections.
//   - DIALOG_SHELL: responsive bottom-sheet/modal, close actions, and full-analysis link.
// owned_tests:
//   - __tests__/components/today-convergence/today-screen.test.tsx
// END_MODULE_MAP: M-TODAY-IMPULSE-DRILLDOWN

"use client";

import { useEffect, useState } from "react";
import type { TodayConvergenceImpulse } from "@/packages/contracts/today-convergence";
import type { TodaySpherePagePayload } from "@/packages/contracts/today-sphere-page";
import { fetchSpherePage } from "@/lib/api/spheres";
import {
  formatEventTime,
  getEventTimeDateTime,
  getPolarityLabel,
  getPolarityToneClasses,
  getTodaySphereLabel,
} from "./today-formatters";
import { getPeriodTechniqueCopy } from "./period-technique-copy";

export type ImpulseDrilldownGroup = {
  sphere: TodayConvergenceImpulse["sphere"];
  impulses: readonly TodayConvergenceImpulse[];
};

type Props = {
  group: ImpulseDrilldownGroup;
  snapshotId?: string | null;
  targetDate?: string | null;
  timezone?: string | null;
  onClose: () => void;
};

type ContextState = "loading" | "ready" | "error";

const MONTHS_RU_GEN = [
  "января",
  "февраля",
  "марта",
  "апреля",
  "мая",
  "июня",
  "июля",
  "августа",
  "сентября",
  "октября",
  "ноября",
  "декабря",
] as const;

function targetDateLabel(targetDate: string | null | undefined): string | null {
  if (!targetDate || !/^\d{4}-\d{2}-\d{2}$/u.test(targetDate)) return null;
  const [year, month, day] = targetDate.split("-").map(Number);
  if (!year || month < 1 || month > 12 || day < 1 || day > 31) return null;
  return `${day} ${MONTHS_RU_GEN[month - 1]} ${year}`;
}

function errorStatus(error: unknown): number | undefined {
  if (!error || typeof error !== "object") return undefined;
  const status = (error as { status?: unknown }).status;
  return typeof status === "number" ? status : undefined;
}

function ContextLayer({
  state,
  payload,
  status,
}: {
  state: ContextState;
  payload?: TodaySpherePagePayload;
  status?: number;
}) {
  if (state === "loading") {
    return (
      <div
        data-testid="impulse-drilldown-context-loading"
        data-state="loading"
        role="status"
        aria-label="Загружаем контекст сферы"
        className="rounded-2xl border border-border/60 bg-muted/30 p-4 text-[14px] leading-6 text-muted-foreground"
      >
        Загружаем контекст сферы…
      </div>
    );
  }

  if (status === 403) {
    return (
      <div
        data-testid="impulse-drilldown-context-access"
        data-state="locked"
        role="alert"
        className="rounded-2xl border border-border/60 bg-muted/30 p-4"
      >
        <p className="text-[14px] font-medium leading-5">Контекст сферы пока закрыт</p>
        <p className="mt-1 text-[13px] leading-5 text-muted-foreground">
          Факты сегодняшнего дня доступны выше, а подробный контекст откроется с полным доступом.
        </p>
      </div>
    );
  }

  if (state === "error" || !payload) {
    return (
      <div
        data-testid="impulse-drilldown-context-error"
        data-state="error"
        role="alert"
        className="rounded-2xl border border-border/60 bg-muted/30 p-4 text-[13px] leading-5 text-muted-foreground"
      >
        Не удалось загрузить контекст сферы. Факты сегодняшнего дня остаются доступны выше.
      </div>
    );
  }

  const natalParagraphs = payload.natal.state === "ready" ? payload.natal.paragraphs ?? [] : [];
  const periods = payload.periodUnavailable ? [] : payload.period;

  return (
    <section
      data-testid="impulse-drilldown-context"
      data-state="ready"
      className="space-y-4 rounded-2xl border border-border/60 bg-card p-4"
    >
      <h3 className="text-[12px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Контекст сферы
      </h3>

      {natalParagraphs.length > 0 ? (
        <div data-testid="impulse-drilldown-natal" className="space-y-2">
          <h4 className="text-[14px] font-medium">В твоей карте</h4>
          {natalParagraphs.map((paragraph, index) => (
            <p
              key={`${paragraph.sourceFactIds.join("-")}-${index}`}
              data-testid={`impulse-drilldown-natal-${index}`}
              data-source-fact-ids={paragraph.sourceFactIds.join(",")}
              className="text-[14px] leading-6 text-foreground/85"
            >
              {paragraph.text}
            </p>
          ))}
        </div>
      ) : null}

      {periods.length > 0 ? (
        <div data-testid="impulse-drilldown-periods" className="space-y-2">
          <h4 className="text-[14px] font-medium">Сейчас действует</h4>
          <ul className="space-y-2">
            {periods.map((period) => {
              const copy = getPeriodTechniqueCopy(period.technique);
              return (
                <li
                  key={period.id}
                  data-testid={`impulse-drilldown-period-${period.id}`}
                  data-technique={period.technique ?? "unknown"}
                  data-active-until={period.activeUntil}
                  className="rounded-xl bg-muted/40 px-3 py-2 text-[13px] leading-5"
                >
                  <span className="font-medium">{period.title}</span>
                  <time dateTime={period.activeUntil} className="mt-0.5 block text-muted-foreground">
                    {period.activeFrom} — {period.activeUntil}
                  </time>
                  <section
                    data-testid={`impulse-drilldown-period-technique-copy-${period.id}`}
                    data-technique={period.technique ?? "unknown"}
                    className="mt-3 border-t border-border/50 pt-3"
                  >
                    <h5 className="font-medium text-foreground">{copy.label}</h5>
                    <dl className="mt-2 space-y-2 text-muted-foreground">
                      <div data-technique-part="what-it-is">
                        <dt className="font-medium text-foreground">Что это</dt>
                        <dd data-testid={`impulse-drilldown-period-what-it-is-${period.id}`}>
                          {copy.whatItIs}
                        </dd>
                      </div>
                      <div data-technique-part="how-it-affects-now">
                        <dt className="font-medium text-foreground">Как влияет сейчас</dt>
                        <dd data-testid={`impulse-drilldown-period-how-it-affects-now-${period.id}`}>
                          {copy.howItAffectsNow}
                        </dd>
                      </div>
                      <div data-technique-part="what-you-may-notice">
                        <dt className="font-medium text-foreground">Что можно заметить</dt>
                        <dd data-testid={`impulse-drilldown-period-what-you-may-notice-${period.id}`}>
                          {copy.whatYouMayNotice}
                        </dd>
                      </div>
                    </dl>
                  </section>
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}

      {natalParagraphs.length === 0 && periods.length === 0 ? (
        <p data-testid="impulse-drilldown-context-empty" className="text-[13px] leading-5 text-muted-foreground">
          Дополнительный контекст сферы пока недоступен.
        </p>
      ) : null}
    </section>
  );
}

// START_BLOCK: DIALOG_SHELL
export function ImpulseDrilldownSheet({
  group,
  snapshotId,
  targetDate,
  timezone,
  onClose,
}: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-IMPULSE-DRILLDOWN.ImpulseDrilldownSheet
  // purpose: Render deterministic grouped impulse facts and lazy sphere context in a responsive accessible dialog.
  // inputs: group — one sphere and its Today impulses; snapshotId/targetDate/timezone — product context; onClose — parent close action.
  // returns: dialog DOM with local facts immediately and context transport/content states.
  // side_effects: GET /api/spheres/{sphere} on mount; aborts that request on unmount; listens for Escape.
  // emitted_logs: delegated ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed.
  // error_behavior: context failures render inside the dialog while deterministic Today facts remain visible.
  // END_FUNCTION_CONTRACT: F-M-TODAY-IMPULSE-DRILLDOWN.ImpulseDrilldownSheet
  const [contextState, setContextState] = useState<ContextState>("loading");
  const [contextPayload, setContextPayload] = useState<TodaySpherePagePayload>();
  const [contextStatus, setContextStatus] = useState<number>();
  const titleId = `impulse-drilldown-title-${group.sphere}`;
  const dateLabel = targetDateLabel(targetDate);
  const fullHref = snapshotId
    ? `/day/snapshots/${encodeURIComponent(snapshotId)}/spheres/${group.sphere}`
    : `/day/spheres/${group.sphere}`;

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setContextState("loading");
    setContextPayload(undefined);
    setContextStatus(undefined);

    fetchSpherePage(group.sphere, controller.signal)
      .then((payload) => {
        if (!active) return;
        setContextPayload(payload);
        setContextState("ready");
      })
      .catch((error: unknown) => {
        if (!active || controller.signal.aborted) return;
        setContextStatus(errorStatus(error));
        setContextState("error");
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [group.sphere]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div
      data-testid="impulse-drilldown-sheet"
      data-state={contextStatus === 403 ? "locked" : contextState}
      data-context-state={contextState}
      data-sphere={group.sphere}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      className="fixed inset-0 z-50 flex items-end justify-center md:items-center"
    >
      <div aria-hidden className="absolute inset-0 bg-foreground/20 backdrop-blur-[2px]" />
      <section className="relative flex max-h-[88vh] w-full flex-col overflow-hidden rounded-t-[28px] border border-border/70 bg-background shadow-2xl md:max-h-[min(80vh,720px)] md:w-[min(560px,calc(100vw-2rem))] md:rounded-[24px]">
        <header className="flex items-start justify-between gap-4 border-b border-border/60 px-5 pb-4 pt-5">
          <div>
            <p className="text-[12px] font-medium uppercase tracking-[0.14em] text-muted-foreground">Сегодня</p>
            <h2 id={titleId} className="mt-1 font-serif text-[26px] leading-tight">
              {getTodaySphereLabel(group.sphere)}
            </h2>
            {dateLabel ? (
              <p data-testid="impulse-drilldown-date" className="mt-1 text-[13px] text-muted-foreground">
                {dateLabel}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            data-testid="impulse-drilldown-close"
            aria-label="Закрыть разбор импульса"
            onClick={onClose}
            className="flex h-11 w-11 flex-none items-center justify-center rounded-full border border-border/70 text-[20px] text-muted-foreground transition hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <span aria-hidden>×</span>
          </button>
        </header>

        <div className="min-h-0 space-y-5 overflow-y-auto px-5 py-5">
          <section data-testid="impulse-drilldown-today-facts" className="space-y-3">
            <h3 className="text-[12px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              Факты сегодняшнего дня
            </h3>
            <ul className="space-y-3">
              {group.impulses.map((impulse) => (
                <li
                  key={impulse.eventId}
                  data-testid={`impulse-drilldown-fact-${impulse.eventId}`}
                  data-polarity={impulse.polarity}
                  data-time-mode={impulse.time.mode}
                  className="rounded-2xl border border-border/60 bg-card p-4 shadow-sm"
                >
                  <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-[15px] leading-[22px]">
                    <time
                      className="tabular-nums"
                      dateTime={getEventTimeDateTime(impulse.time)}
                    >
                      {formatEventTime(impulse.time, timezone)}
                    </time>
                    <span className="font-medium">{getTodaySphereLabel(impulse.sphere)}</span>
                    <span className={`rounded-full px-2 py-0.5 text-[13px] leading-[18px] ${getPolarityToneClasses(impulse.polarity)}`}>
                      {getPolarityLabel(impulse.polarity)}
                    </span>
                  </div>
                  {impulse.summary ? (
                    <p className="mt-2 text-[15px] leading-[22px] text-pretty text-foreground/85">
                      {impulse.summary.text}
                    </p>
                  ) : null}
                  {impulse.action ? (
                    <p
                      data-testid={`impulse-drilldown-action-${impulse.eventId}`}
                      className="mt-2 border-l-2 border-border/70 pl-3 text-[14px] leading-5 text-muted-foreground"
                    >
                      <span className="font-medium text-foreground">Можно сделать: </span>
                      {impulse.action.text}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          </section>

          <ContextLayer state={contextState} payload={contextPayload} status={contextStatus} />

          <a
            data-testid="impulse-drilldown-full-link"
            href={fullHref}
            className="inline-flex min-h-11 items-center rounded-full border border-border/70 px-4 py-2 text-[13px] font-medium transition hover:border-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            Полный разбор сферы
          </a>
        </div>
      </section>
    </div>
  );
}
// END_BLOCK: DIALOG_SHELL
