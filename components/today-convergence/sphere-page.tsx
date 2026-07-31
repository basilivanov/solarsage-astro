// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_SPHERE_PAGE — static sphere page view.
// ROLE: Projects long-lived natal and period layers without daily verdicts.
// ############################################################################

// START_MODULE_CONTRACT: M-SPHERE-PAGE
// purpose: Render the static sphere page with honest content, access, and transport states.
// owns:
//   - components/today-convergence/sphere-page.tsx
// inputs: generated TodaySpherePagePayload, route sphere key, and transport state.
// outputs: sphere-page root, natal paragraphs, period items, birth-time notice, and error/access states.
// dependencies: generated sphere page contract, canonical sphere labels, Paywall.
// side_effects: delegates retry and paywall actions; no calculations or network calls.
// emitted_logs: none.
// invariants: daily verdict language is absent; houses are never invented when unavailable; date labels are date-only.
// failure_policy: natal unavailable is an honest no-retry content state; transport failures expose retry except 403 paywall.
// END_MODULE_CONTRACT: M-SPHERE-PAGE

// START_MODULE_MAP: M-SPHERE-PAGE
// public_entrypoints:
//   - SpherePage
// semantic_blocks:
//   - TRANSPORT: loading, access, unavailable, and retryable error states.
//   - NATAL_LAYER: paragraph-bound natal copy and house availability notice.
//   - PERIOD_LAYER: active long-lived themes with date-only end labels.
// owned_tests:
//   - __tests__/components/today-convergence/sphere-page.test.tsx
// END_MODULE_MAP: M-SPHERE-PAGE

"use client";

import { Paywall } from "@/components/paywall";
import { CANONICAL_PRODUCT_ORDER } from "@/lib/display/sphere-labels";
import type { TodaySpherePagePayload } from "@/packages/contracts/today-sphere-page";

export type SpherePageScreenState = "loading" | "ready" | "error";

export type SpherePageProps = {
  payload?: TodaySpherePagePayload;
  sphereKey?: string;
  screenState?: SpherePageScreenState;
  errorStatus?: number;
  onRetry?: () => void;
};

const RUSSIAN_MONTHS = [
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

function sphereLabel(key: string | undefined): string {
  return CANONICAL_PRODUCT_ORDER.find((sphere) => sphere.key === key)?.label ?? "Сфера";
}

function formatDateOnly(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return value;

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (month < 1 || month > 12 || day < 1 || day > 31) return value;

  const date = new Date(Date.UTC(year, month - 1, day));
  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day
  ) {
    return value;
  }

  return `${day} ${RUSSIAN_MONTHS[month - 1]} ${year} г.`;
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
    <section data-testid={testId} className="rounded-[24px] border border-border/60 bg-card p-5">
      <h1 className="font-serif text-[24px] leading-tight">{title}</h1>
      <p className="mt-2 text-[14px] leading-6 text-muted-foreground">{description}</p>
      <button
        type="button"
        onClick={() => onRetry?.()}
        className="mt-5 min-h-11 rounded-full border border-border/70 bg-background px-5 text-[13px] font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
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
}: Pick<SpherePageProps, "screenState" | "errorStatus" | "onRetry">) {
  if (screenState === "loading") {
    return (
      <div
        data-testid="sphere-page-loading"
        role="status"
        aria-label="Загружаем страницу сферы"
        className="space-y-3"
      >
        <span aria-hidden className="block h-8 w-3/5 animate-pulse rounded bg-muted" />
        <span aria-hidden className="block h-28 w-full animate-pulse rounded-[24px] bg-muted" />
        <span aria-hidden className="block h-24 w-full animate-pulse rounded-[24px] bg-muted" />
      </div>
    );
  }

  if (errorStatus === 403) {
    return (
      <section data-testid="sphere-page-access" className="space-y-4">
        <h1 className="font-serif text-[24px] leading-tight">Нужен полный доступ</h1>
        <p className="text-[14px] leading-6 text-muted-foreground">
          Полный разбор сферы доступен по подписке.
        </p>
        <Paywall
          compact
          title="Открой разбор сферы"
          description="Подписка открывает натальный текст и действующие периоды."
        />
      </section>
    );
  }

  if (errorStatus === 422) {
    return (
      <RetryState
        testId="sphere-page-unavailable"
        title="Страница недоступна"
        description="Проверьте выбранную сферу и попробуйте ещё раз."
        onRetry={onRetry}
      />
    );
  }

  return (
    <RetryState
      testId="sphere-page-error"
      title="Не удалось загрузить страницу"
      description="Попробуйте запросить данные сферы ещё раз."
      onRetry={onRetry}
    />
  );
}
// END_BLOCK: TRANSPORT

// START_BLOCK: NATAL_LAYER
function NatalLayer({ payload }: { payload: TodaySpherePagePayload }) {
  const paragraphs = payload.natal.paragraphs ?? [];
  const hasNatalText = payload.natal.state === "ready" && paragraphs.length > 0;

  return (
    <section
      data-testid="sphere-natal"
      data-state={hasNatalText ? "ready" : "empty"}
      data-content-state={hasNatalText ? "ready" : "unavailable"}
      className="rounded-[24px] border border-border/60 bg-card p-5"
    >
      <h2 className="font-serif text-[22px] leading-tight">В твоей карте</h2>
      {hasNatalText ? (
        <div className="mt-4 space-y-4">
          {paragraphs.map((paragraph, index) => (
            <p
              key={`${index}-${paragraph.sourceFactIds.join("-")}`}
              data-testid={`sphere-natal-paragraph-${index}`}
              data-source-fact-ids={paragraph.sourceFactIds.join(",")}
              className="text-pretty text-[15px] leading-7 text-foreground/90"
            >
              {paragraph.text}
            </p>
          ))}
        </div>
      ) : (
        <p
          data-testid="sphere-natal-unavailable"
          className="mt-4 text-[15px] leading-7 text-muted-foreground"
        >
          Разбор сферы готовится
        </p>
      )}
      {!payload.housesAvailable ? (
        <p
          data-testid="sphere-houses-unavailable"
          className="mt-4 rounded-2xl bg-secondary/60 px-4 py-3 text-[13px] leading-5 text-muted-foreground"
        >
          Дома и точные часы скрыты: время рождения не указано
        </p>
      ) : null}
    </section>
  );
}
// END_BLOCK: NATAL_LAYER

// START_BLOCK: PERIOD_LAYER
function PeriodLayer({ payload }: { payload: TodaySpherePagePayload }) {
  const hasPeriods = payload.period.length > 0;
  const periodUnavailable = payload.periodUnavailable === true;

  return (
    <section
      data-testid="sphere-period"
      data-state={hasPeriods ? "ready" : "empty"}
      data-content-state={hasPeriods ? "ready" : periodUnavailable ? "unavailable" : "empty"}
      data-period-identity={payload.periodIdentity}
      className="rounded-[24px] border border-border/60 bg-card p-5"
    >
      <h2 className="font-serif text-[22px] leading-tight">Сейчас действует</h2>
      {hasPeriods ? (
        <ol className="mt-4 space-y-3">
          {payload.period.map((item) => (
            <li
              key={item.id}
              data-testid={`sphere-period-${item.id}`}
              data-technique={item.technique}
              data-active-until={item.activeUntil}
              className="rounded-2xl border border-border/60 px-4 py-3"
            >
              <p className="text-[15px] leading-6 text-foreground">{item.title}</p>
              <time
                dateTime={item.activeUntil}
                className="mt-1 block text-[13px] leading-5 text-muted-foreground"
              >
                до {formatDateOnly(item.activeUntil)}
              </time>
            </li>
          ))}
        </ol>
      ) : (
        <p data-testid="sphere-period-empty" className="mt-4 text-[15px] leading-7 text-muted-foreground">
          {periodUnavailable ? "Периодический контекст пока недоступен" : "Активных периодов нет"}
        </p>
      )}
    </section>
  );
}
// END_BLOCK: PERIOD_LAYER

// START_BLOCK: READY_SCREEN
export function SpherePage({
  payload,
  sphereKey,
  screenState = "ready",
  errorStatus,
  onRetry,
}: SpherePageProps) {
  // START_FUNCTION_CONTRACT: F-M-SPHERE-PAGE.SpherePage
  // purpose: Render the static sphere page or its transport/access projection.
  // inputs: payload — generated natal/period envelope; sphereKey — route key; screenState/errorStatus — transport state; onRetry — refetch callback.
  // returns: accessible sphere-page root with two long-lived content layers.
  // side_effects: delegates retry and paywall actions only.
  // emitted_logs: none.
  // error_behavior: a missing ready payload degrades to a retryable error state.
  // END_FUNCTION_CONTRACT: F-M-SPHERE-PAGE.SpherePage
  const resolvedSphere = sphereKey ?? payload?.sphere;
  const ready = screenState === "ready" && payload !== undefined;
  const renderedScreenState: SpherePageScreenState = ready
    ? "ready"
    : screenState === "ready"
      ? "error"
      : screenState;
  const dataState = renderedScreenState === "loading"
    ? "loading"
    : renderedScreenState === "ready"
      ? "ready"
      : errorStatus === 403
        ? "locked"
        : "error";

  return (
    <main
      data-testid="sphere-page"
      data-sphere={resolvedSphere || undefined}
      data-screen-state={renderedScreenState}
      data-state={dataState}
      data-birth-time-mode={ready ? payload.birthTimeMode : "unknown"}
      data-houses-available={ready ? String(payload.housesAvailable) : undefined}
      role={renderedScreenState === "error" ? "alert" : undefined}
      aria-busy={renderedScreenState === "loading" ? true : undefined}
      aria-label="Страница сферы"
      className="min-h-full bg-background text-foreground"
    >
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-5 py-6">
        {renderedScreenState !== "ready" ? (
          <TransportContent
            screenState={renderedScreenState}
            errorStatus={errorStatus}
            onRetry={onRetry}
          />
        ) : null}
        {ready ? (
          <>
            <header>
              <p className="text-[12px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                Страница сферы
              </p>
              <h1 className="mt-2 font-serif text-[28px] leading-tight">{sphereLabel(payload.sphere)}</h1>
            </header>
            <NatalLayer payload={payload} />
            <PeriodLayer payload={payload} />
          </>
        ) : null}
      </div>
    </main>
  );
}
// END_BLOCK: READY_SCREEN
