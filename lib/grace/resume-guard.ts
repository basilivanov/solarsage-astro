// ############################################################################
// AI_HEADER: MODULE_RESUME_GUARD — client-only webview resume detector.
// ROLE: Distinguishes a frozen/restored page from a live one and recovers without reload loops.
// ############################################################################

// START_MODULE_CONTRACT: M-RESUME-GUARD
// purpose: Detect pageshow-from-snapshot and stale visibility resumes, then soft-refetch or hard-reload safely.
// owns:
//   - lib/grace/resume-guard.ts
// inputs: readiness getter, soft-refetch callback, and an optional suppression callback.
// outputs: install/cleanup function, hard-reload helper, and bounded sessionStorage reload history.
// dependencies: lib/log/index.ts (logEvent), browser window/document/sessionStorage/location.
// side_effects: heartbeat interval, window/document listeners, sessionStorage writes, logs, and navigation.
// emitted_logs: resume.snapshot_reload, resume.stale_reload, resume.reload_loop_suppressed.
// invariants:
//   - no React imports; the module is safe to import in client components and inert without a browser.
//   - auto reloads are capped at two per ten-minute sessionStorage window.
//   - a suppressed reload surfaces through onReloadSuppressed instead of navigating.
// failure_policy: unavailable storage or navigation suppresses reload and reports the loop guard.
// END_MODULE_CONTRACT: M-RESUME-GUARD

// START_MODULE_MAP: M-RESUME-GUARD
// public_entrypoints:
//   - RESUME_HEARTBEAT_MS
//   - RESUME_STALE_AFTER_MS
//   - RESUME_RELOAD_LIMIT
//   - RESUME_RELOAD_WINDOW_MS
//   - RESUME_RELOAD_STORAGE_KEY
//   - ResumeGuardOptions
//   - hardReloadWithCacheBuster
//   - installResumeGuard
// semantic_blocks:
//   - HEARTBEAT: module-level lastAliveTs updated every five seconds.
//   - PAGESHOW: restored snapshot detection.
//   - VISIBILITY: stale visible resume detection with ready/not-ready routing.
//   - RELOAD_LOOP_GUARD: sessionStorage-backed auto-reload budget.
//   - HARD_RELOAD: cache-busting location.replace.
// owned_tests:
//   - __tests__/lib/resume-guard.test.ts
// END_MODULE_MAP: M-RESUME-GUARD

"use client";

import { logEvent } from "@/lib/log";

export const RESUME_HEARTBEAT_MS = 5_000;
export const RESUME_STALE_AFTER_MS = 30_000;
export const RESUME_RELOAD_LIMIT = 2;
export const RESUME_RELOAD_WINDOW_MS = 10 * 60_000;
export const RESUME_RELOAD_STORAGE_KEY = "solarsage.resume_reload_history.v1";

type AutoReloadEvent = "resume.snapshot_reload" | "resume.stale_reload";
type ReloadReason = "pageshow_persisted" | "visibility_stale";

export type ResumeGuardOptions = {
  /** Returns true only when the day screen is showing ready content. */
  isReady: () => boolean;
  /** Soft-refresh path used when a stale page is still healthy. */
  refetch: () => void;
  /** Called instead of navigating when the reload budget is exhausted or storage is unavailable. */
  onReloadSuppressed?: () => void;
};

let lastAliveTs = 0;
let activeCleanup: (() => void) | null = null;

// START_BLOCK: RELOAD_LOOP_GUARD
function readReloadHistory(): number[] {
  try {
    const raw = window.sessionStorage.getItem(RESUME_RELOAD_STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (value): value is number => typeof value === "number" && Number.isFinite(value),
    );
  } catch {
    return [];
  }
}

function writeReloadHistory(timestamps: number[]): boolean {
  try {
    window.sessionStorage.setItem(RESUME_RELOAD_STORAGE_KEY, JSON.stringify(timestamps));
    return true;
  } catch {
    return false;
  }
}

function reserveAutoReload(now: number): { allowed: boolean; count: number } {
  const recent = readReloadHistory().filter(
    (timestamp) => timestamp <= now && now - timestamp < RESUME_RELOAD_WINDOW_MS,
  );
  if (recent.length >= RESUME_RELOAD_LIMIT) {
    return { allowed: false, count: recent.length };
  }

  recent.push(now);
  if (!writeReloadHistory(recent)) {
    return { allowed: false, count: recent.length - 1 };
  }
  return { allowed: true, count: recent.length };
}
// END_BLOCK: RELOAD_LOOP_GUARD

// START_BLOCK: HARD_RELOAD
// START_FUNCTION_CONTRACT: F-M-RESUME-GUARD.hardReloadWithCacheBuster
// purpose: Navigate to the current path with a timestamp cache-buster via location.replace.
// inputs: now — optional timestamp used for the r query parameter.
// returns: true when location.replace was invoked; false outside a browser or on failure.
// side_effects: calls location.replace and may unload the page.
// emitted_logs: none.
// error_behavior: navigation failures return false without throwing.
// END_FUNCTION_CONTRACT: F-M-RESUME-GUARD.hardReloadWithCacheBuster
export function hardReloadWithCacheBuster(now: number = Date.now()): boolean {
  try {
    if (typeof window === "undefined" || typeof window.location === "undefined") return false;
    const { location } = window;
    if (typeof location.replace !== "function") return false;
    const url = new URL(location.href);
    url.searchParams.set("r", String(now));
    location.replace(`${url.pathname}${url.search}${url.hash}`);
    return true;
  } catch {
    return false;
  }
}
// END_BLOCK: HARD_RELOAD

// START_BLOCK: RELOAD_LOOP_GUARD
function reportReloadSuppressed(options: ResumeGuardOptions, reason: ReloadReason, count: number): void {
  logEvent(
    "resume.reload_loop_suppressed",
    { reason, reload_count: count, reload_limit: RESUME_RELOAD_LIMIT },
    {
      level: "error",
      slice: "W-WHITE-SCREEN-RESILIENCE",
      module: "M-RESUME-GUARD",
      block: "RELOAD_LOOP_GUARD",
    },
  );
  options.onReloadSuppressed?.();
}

function attemptAutoReload(
  eventName: AutoReloadEvent,
  reason: ReloadReason,
  options: ResumeGuardOptions,
): void {
  const now = Date.now();
  const reservation = reserveAutoReload(now);
  if (!reservation.allowed) {
    reportReloadSuppressed(options, reason, reservation.count);
    return;
  }

  logEvent(
    eventName,
    { reason, reload_count: reservation.count },
    {
      level: "warn",
      slice: "W-WHITE-SCREEN-RESILIENCE",
      module: "M-RESUME-GUARD",
      block: reason === "pageshow_persisted" ? "PAGESHOW" : "VISIBILITY",
    },
  );

  if (!hardReloadWithCacheBuster(now)) {
    reportReloadSuppressed(options, reason, reservation.count);
  }
}
// END_BLOCK: RELOAD_LOOP_GUARD

// START_BLOCK: RESUME_LISTENERS
// START_FUNCTION_CONTRACT: F-M-RESUME-GUARD.installResumeGuard
// purpose: Install heartbeat, pageshow, and visibility listeners for one mounted day screen.
// inputs: options — readiness getter, soft refetch callback, and optional suppression callback.
// returns: cleanup function that removes listeners and the heartbeat timer.
// side_effects: timers, document/window listeners, logs, sessionStorage, and possible navigation.
// emitted_logs: resume.snapshot_reload, resume.stale_reload, resume.reload_loop_suppressed.
// error_behavior: no-op outside a browser; storage/navigation failures are reported as suppression.
// END_FUNCTION_CONTRACT: F-M-RESUME-GUARD.installResumeGuard
export function installResumeGuard(options: ResumeGuardOptions): () => void {
  if (typeof window === "undefined" || typeof document === "undefined") return () => {};
  activeCleanup?.();
  lastAliveTs = Date.now();

  const heartbeat = window.setInterval(() => {
    // A hidden/frozen page must age so the first visible frame can detect it.
    if (document.visibilityState === "visible") lastAliveTs = Date.now();
  }, RESUME_HEARTBEAT_MS);

  const handlePageShow = (event: Event) => {
    if ((event as PageTransitionEvent).persisted !== true) return;
    if (options.isReady()) return;
    attemptAutoReload("resume.snapshot_reload", "pageshow_persisted", options);
  };

  const handleVisibilityChange = () => {
    if (document.visibilityState !== "visible") return;
    const now = Date.now();
    if (now - lastAliveTs <= RESUME_STALE_AFTER_MS) return;
    lastAliveTs = now;
    if (options.isReady()) {
      options.refetch();
      return;
    }
    attemptAutoReload("resume.stale_reload", "visibility_stale", options);
  };

  window.addEventListener("pageshow", handlePageShow);
  document.addEventListener("visibilitychange", handleVisibilityChange);

  const cleanup = () => {
    window.clearInterval(heartbeat);
    window.removeEventListener("pageshow", handlePageShow);
    document.removeEventListener("visibilitychange", handleVisibilityChange);
    if (activeCleanup === cleanup) activeCleanup = null;
  };
  activeCleanup = cleanup;
  return cleanup;
}
// END_BLOCK: RESUME_LISTENERS
