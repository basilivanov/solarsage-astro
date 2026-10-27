// ############################################################################
// AI_HEADER: MODULE_DAY_DATE_PAGE — real Today Convergence route wiring.
// ROLE: Preserves date routing/onboarding while delegating data and state to the generated Today screen.
// ############################################################################

// START_MODULE_CONTRACT: M-APP-DAY-PAGE
// purpose: Render /day/[date] and /day/today from the Today Convergence envelope.
// owns:
//   - app/(grace)/day/[date]/page.tsx
// inputs: route date parameter, authenticated session, hook payload, and touch gestures.
// outputs: safe-area-aware date navigation plus TodayScreen transport/ready/error states.
// dependencies: next/navigation, useTodayConvergence, useOnboarded, lib/date, lib/today, generated Today contract.
// side_effects: API lifecycle delegated to the hook; route replace/push and onboarding sync.
// emitted_logs: delegated to useTodayConvergence and authentication/profile hooks.
// invariants: today and valid ISO parameters reach the API unchanged; invalid parameters redirect to today's ISO route;
//             a local-date rollover updates today state and leaves an old ISO route for /day/today;
//             transport fallback payload is never rendered as ready content.
// failure_policy: TodayScreen owns loading/error presentation; invalid routes are replaced with today's route.
// END_MODULE_CONTRACT: M-APP-DAY-PAGE

// START_MODULE_MAP: M-APP-DAY-PAGE
// public_entrypoints:
//   - DayPage
// semantic_blocks:
//   - ROUTE_DATE: normalize today/ISO route values and invalid redirects.
//   - DATE_NAVIGATION: human date header plus safe-area-aware previous/today/next route navigation and horizontal swipes.
//   - TODAY_WIRING: connect hook state to the new TodayScreen.
// owned_tests:
//   - __tests__/app/day-page.test.tsx
// END_MODULE_MAP: M-APP-DAY-PAGE

"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type TouchEvent } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { TodayScreen } from "@/components/today-convergence/today-screen";
import { useOnboarded } from "@/hooks/use-onboarded";
import { useTodayConvergence } from "@/lib/grace/hooks/useTodayConvergence";
import { formatDayMonth, fromDateParam, toDateParam } from "@/lib/date";
import { sameDay } from "@/lib/today";

const TRANSPORT_PAYLOAD = {
  schemaVersion: 2,
  snapshotId: null,
  targetDate: "",
  timezone: "UTC",
  publishedAt: null,
  access: {
    state: "locked",
    reason: "outside_access_window",
    referralDaysLeft: 0,
    subscriptionActive: false,
    accessUntil: null,
  },
  birthTime: {
    mode: "unknown",
    bucket: null,
    rangeStart: "00:00",
    rangeEnd: "24:00",
    capabilities: { houses: false, angles: false, lots: false, exactTiming: false },
  },
  state: null,
  dayTone: null,
  personal: null,
  previewTeaser: null,
  convergences: [],
  mainEvent: null,
  impulses: [],
  periodContext: null,
  lookahead: null,
  events: [],
  contentState: "not_needed",
  formulaVersion: "today-convergence-2",
  calculationVersion: "transport",
} satisfies Parameters<typeof TodayScreen>[0]["payload"];

function shiftDate(date: Date, days: number): Date {
  const shifted = new Date(date);
  shifted.setDate(shifted.getDate() + days);
  return shifted;
}

// START_FUNCTION_CONTRACT: F-M-APP-DAY-PAGE.formatDateHeader
// purpose: Render the selected day as a human Russian date relative to today.
// inputs: date — selected local calendar date; today — current local calendar date.
// returns: Today/yesterday/tomorrow label or day-month label with a year only outside the current year.
// side_effects: none.
// emitted_logs: none.
// error_behavior: valid Date inputs always produce a deterministic label.
// END_FUNCTION_CONTRACT: F-M-APP-DAY-PAGE.formatDateHeader
function formatDateHeader(date: Date, today: Date): string {
  const dayMonth = formatDayMonth(date);
  if (sameDay(date, today)) return `Сегодня, ${dayMonth}`;
  if (sameDay(date, shiftDate(today, -1))) return `Вчера, ${dayMonth}`;
  if (sameDay(date, shiftDate(today, 1))) return `Завтра, ${dayMonth}`;
  return date.getFullYear() === today.getFullYear()
    ? dayMonth
    : `${dayMonth} ${date.getFullYear()}`;
}

function isInteractiveTarget(target: EventTarget | null): boolean {
  return target instanceof Element && Boolean(
    target.closest("a,button,input,textarea,select,option,label,[contenteditable='true'],[role='button'],[role='link']"),
  );
}

// START_BLOCK: ROUTE_DATE
export default function DayPage() {
  // START_FUNCTION_CONTRACT: F-M-APP-DAY-PAGE.DayPage
  // purpose: Resolve the route parameter and connect the Today Convergence hook to the page.
  // inputs: Next route params containing today or an ISO date.
  // returns: date navigation and TodayScreen.
  // side_effects: route replacement/push, onboarding sync, and delegated hook requests.
  // emitted_logs: delegated hook/auth events.
  // error_behavior: invalid date parameters are replaced with today's ISO route.
  // END_FUNCTION_CONTRACT: F-M-APP-DAY-PAGE.DayPage
  const params = useParams<{ date?: string }>();
  const router = useRouter();
  const { setOnboarded } = useOnboarded();
  const rawDateParam = typeof params.date === "string" ? params.date : "today";
  const isTodayParam = rawDateParam === "today";
  // Keep today as state rather than a module-level constant: a webview can stay
  // mounted across midnight, and the header/navigation must follow the rollover.
  const [todayDate, setTodayDate] = useState(() => new Date());
  const selectedDate = useMemo(
    () => (isTodayParam ? todayDate : fromDateParam(rawDateParam) ?? todayDate),
    [isTodayParam, rawDateParam, todayDate],
  );
  const isValidDateParam = isTodayParam || fromDateParam(rawDateParam) !== null;
  const requestDateParam = isValidDateParam ? rawDateParam : "today";
  const { screenState, payload, refetch } = useTodayConvergence(requestDateParam);

  useEffect(() => {
    if (!isValidDateParam) router.replace(`/day/${toDateParam(todayDate)}`);
  }, [isValidDateParam, router, todayDate]);

  useEffect(() => {
    if (screenState === "ready" && payload) setOnboarded(true);
  }, [payload, screenState, setOnboarded]);

  const navigateToDate = useCallback(
    (date: Date) => router.push(`/day/${toDateParam(date)}`),
    [router],
  );

  const handleDateRollover = useCallback(() => {
    setTodayDate(new Date());
    // An explicit old ISO route must leave for the today sentinel. The today
    // sentinel already resolves server-side to the new local date, so refresh
    // it in place instead of navigating to the same URL.
    if (isTodayParam) {
      void refetch();
      return;
    }
    router.replace("/day/today");
  }, [isTodayParam, refetch, router]);

  const swipeStartRef = useRef<{ x: number; y: number } | null>(null);
  const handleTouchStart = useCallback((event: TouchEvent<HTMLDivElement>) => {
    const touch = event.touches[0];
    if (!touch || isInteractiveTarget(event.target)) {
      swipeStartRef.current = null;
      return;
    }
    swipeStartRef.current = {
      x: touch.clientX,
      y: touch.clientY,
    };
  }, []);

  const handleTouchEnd = useCallback((event: TouchEvent<HTMLDivElement>) => {
    const start = swipeStartRef.current;
    swipeStartRef.current = null;
    const touch = event.changedTouches[0];
    if (!start || !touch || isInteractiveTarget(event.target)) return;

    const dx = touch.clientX - start.x;
    const dy = touch.clientY - start.y;
    if (Math.abs(dx) < 48 || Math.abs(dx) <= 1.5 * Math.abs(dy)) return;
    navigateToDate(shiftDate(selectedDate, dx < 0 ? 1 : -1));
  }, [navigateToDate, selectedDate]);

  return (
    <div
      className="min-h-full bg-background"
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      onTouchCancel={() => {
        swipeStartRef.current = null;
      }}
    >
      <DayDateNavigation
        selectedDate={selectedDate}
        today={todayDate}
        onDateChange={navigateToDate}
      />
      <TodayScreen
        payload={payload ?? TRANSPORT_PAYLOAD}
        screenState={screenState}
        onRetry={() => void refetch()}
        onDateRollover={handleDateRollover}
      />
    </div>
  );
}
// END_BLOCK: ROUTE_DATE

// START_BLOCK: DATE_NAVIGATION
function DayDateNavigation({
  selectedDate,
  today,
  onDateChange,
}: {
  selectedDate: Date;
  today: Date;
  onDateChange: (date: Date) => void;
}) {
  // START_FUNCTION_CONTRACT: F-M-APP-DAY-PAGE.DayDateNavigation
  // purpose: Preserve the previous/today/next day navigation around the new screen below Telegram/iOS top safe areas.
  // inputs: selectedDate, current local today, and route callback.
  // returns: accessible day navigation.
  // side_effects: invokes onDateChange on button activation.
  // emitted_logs: none.
  // error_behavior: none.
  // END_FUNCTION_CONTRACT: F-M-APP-DAY-PAGE.DayDateNavigation
  return (
    <nav
      data-testid="day-date-navigation"
      aria-label="Навигация по дням"
      className="mx-auto flex w-full max-w-5xl items-center justify-between px-5"
      style={{ paddingTop: "max(var(--tg-content-safe-area-inset-top, 0px), env(safe-area-inset-top), 1rem)" }}
    >
      <button
        type="button"
        aria-label="Предыдущий день"
        onClick={() => onDateChange(shiftDate(selectedDate, -1))}
        className="flex h-9 w-9 items-center justify-center rounded-full border border-border/50 bg-card text-muted-foreground shadow-(--shadow-card) transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary motion-reduce:transition-none"
      >
        <ChevronLeft aria-hidden className="h-4 w-4" />
      </button>
      <span className="font-serif text-[17px] leading-[22px]">{formatDateHeader(selectedDate, today)}</span>
      <button
        type="button"
        aria-label="Следующий день"
        onClick={() => onDateChange(shiftDate(selectedDate, 1))}
        className="flex h-9 w-9 items-center justify-center rounded-full border border-border/50 bg-card text-muted-foreground shadow-(--shadow-card) transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary motion-reduce:transition-none"
      >
        <ChevronRight aria-hidden className="h-4 w-4" />
      </button>
    </nav>
  );
}
// END_BLOCK: DATE_NAVIGATION
