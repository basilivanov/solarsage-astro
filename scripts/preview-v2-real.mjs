#!/usr/bin/env node
// ############################################################################
// AI_HEADER: MODULE_PREVIEW_V2_REAL — fail-closed launcher for the real V2 preview.
// ROLE: Verifies canonical services and tracked config, starts Next on 3003,
//   reports readiness, and owns bounded child/process-group cleanup.
// ############################################################################

// START_MODULE_CONTRACT: M-PREVIEW-V2-REAL
// purpose: Start the local real-backend preview on 127.0.0.1:3003 without
//   starting, replacing, or mocking the canonical API and sidecar.
// owns:
//   - scripts/preview-v2-real.mjs
// inputs:
//   - process environment and CLI invocation
//   - canonical API health at 127.0.0.1:8000
//   - canonical sidecar health at 127.0.0.1:18091
//   - tracked next-env.d.ts and tsconfig.json snapshots
// outputs:
//   - Next development server on 127.0.0.1:3003
//   - exact [preview:v2:real] URL and backend labels after readiness
// dependencies:
//   - node:child_process
//   - node:fs
//   - node:net
//   - node:path
//   - node:url
// side_effects:
//   - binds a temporary port probe
//   - spawns a detached POSIX process group (or a normal Windows child)
//   - restores only an exact Next-generated next-env.d.ts declaration
//   - restores startup tsconfig drift before reporting readiness
// emitted_logs:
//   - [preview:v2:real] lifecycle errors
//   - [preview:v2:real] Real API: http://127.0.0.1:8000
//   - [preview:v2:real] acceptance URL
//   - [preview:v2:real] REAL backend preview; no fixture or mock API.
// invariants:
//   - no backend, fixture server, shell command, or manual API process is started
//   - tsconfig.json is verify-only at runtime and is never written after success
//   - unsafe next-env.d.ts content is preserved and produces a non-zero result
//   - readiness polling and child shutdown are bounded
//   - successful or failed shutdown leaves no owned child/process group
// failure_policy:
//   - missing files, unhealthy services, occupied port, config drift, timeout,
//     unsafe generated-file state, spawn failure, or unexpected child exit fail closed
// END_MODULE_CONTRACT: M-PREVIEW-V2-REAL

// START_MODULE_MAP: M-PREVIEW-V2-REAL
// public_entrypoints:
//   - ACCEPTANCE_URL
//   - buildEnv
//   - isDirectCli
//   - readFileSnapshot
//   - checkPort
//   - checkHealth
//   - buildGeneratedNextEnv
//   - classifyNextEnv
//   - restoreGeneratedNextEnv
//   - verifyStartupTsconfig
//   - terminateProcessGroup
//   - waitForReady
//   - main
//   - shutdown
// semantic_blocks:
//   - CONSTANTS_AND_STATE: canonical endpoints, runtime state, and snapshots
//   - CLI_AND_ENV: import-safe CLI resolution and canonical child environment
//   - FILE_HYGIENE: exact byte/mode snapshots and closed declaration classifier
//   - PREFLIGHT: non-destructive port and canonical health checks
//   - READINESS: bounded HTTP readiness state machine
//   - PROCESS_LIFECYCLE: platform-safe signals and awaited idempotent shutdown
//   - MAIN: preflight, spawn, startup verification, output, and child wait
// owned_tests:
//   - __tests__/scripts/preview-v2-real.test.ts
// END_MODULE_MAP: M-PREVIEW-V2-REAL

import { spawn } from "node:child_process"
import { chmodSync, readFileSync, statSync, writeFileSync } from "node:fs"
import { createServer } from "node:net"
import { dirname, resolve } from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"

// START_BLOCK: CONSTANTS_AND_STATE
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..")
const NEXT_HOST = "127.0.0.1"
const NEXT_PORT = 3003
const API_BASE = "http://127.0.0.1:8000"
const API_HEALTH_URL = `${API_BASE}/api/health`
const SIDECAR_HEALTH_URL = "http://127.0.0.1:18091/v1/health"
const NEXT_DIST_DIR = ".next-v2-real-preview"
const READINESS_URL = `http://${NEXT_HOST}:${NEXT_PORT}/`
const NEXT_ENV_PATH = resolve(ROOT, "next-env.d.ts")
const TSCONFIG_PATH = resolve(ROOT, "tsconfig.json")
const READY_TIMEOUT_MS = 60_000
const TERM_TIMEOUT_MS = 5_000
const KILL_TIMEOUT_MS = 2_000

export const ACCEPTANCE_URL = `http://${NEXT_HOST}:${NEXT_PORT}/day/2026-07-08?why=1`

let child = null
let snapshots = null
let shutdownPromise = null
let processHandlers = null
// END_BLOCK: CONSTANTS_AND_STATE

function log(...args) {
  console.log("[preview:v2:real]", ...args)
}

function warn(...args) {
  console.error("[preview:v2:real]", ...args)
}

function sleep(ms) {
  return new Promise((resolveSleep) => setTimeout(resolveSleep, ms))
}

// START_BLOCK: CLI_AND_ENV
export function isDirectCli(moduleUrl = import.meta.url, argvPath = process.argv[1]) {
  // START_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.isDirectCli
  // purpose: Determine whether this module is the directly invoked CLI entry.
  // inputs: moduleUrl - import.meta.url candidate; argvPath - absolute or relative CLI path.
  // returns: true only when both resolve to the same file URL.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: returns false when argvPath is absent.
  // END_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.isDirectCli
  return Boolean(argvPath) && moduleUrl === pathToFileURL(resolve(argvPath)).href
}

export function buildEnv(baseEnv = process.env) {
  // START_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.buildEnv
  // purpose: Build the closed Next development environment for real API preview.
  // inputs: baseEnv - ambient environment copied without mutation.
  // returns: environment with canonical API, dist, development, and telemetry values.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: none.
  // END_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.buildEnv
  return {
    ...baseEnv,
    NODE_ENV: "development",
    NEXT_DIST_DIR,
    DEV_API_REWRITE_BASE_URL: API_BASE,
    NEXT_TELEMETRY_DISABLED: "1",
  }
}
// END_BLOCK: CLI_AND_ENV

// START_BLOCK: FILE_HYGIENE
export function readFileSnapshot(filePath) {
  // START_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.readFileSnapshot
  // purpose: Capture required tracked-file bytes, UTF-8 text, and permission bits.
  // inputs: filePath - required existing file.
  // returns: immutable-use snapshot object with bytes, text, and mode & 0o777.
  // side_effects: reads file metadata and bytes.
  // emitted_logs: none.
  // error_behavior: throws when the file or metadata cannot be read.
  // END_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.readFileSnapshot
  const bytes = readFileSync(filePath)
  return {
    bytes,
    text: bytes.toString("utf8"),
    mode: statSync(filePath).mode & 0o777,
  }
}

function snapshotEol(snapshotText) {
  return snapshotText.includes("\r\n") ? "\r\n" : "\n"
}

function snapshotHasFinalNewline(snapshotText) {
  return snapshotText.endsWith("\n") || snapshotText.endsWith("\r")
}

export function buildGeneratedNextEnv(snapshotText) {
  // START_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.buildGeneratedNextEnv
  // purpose: Build the sole accepted Next 16 declaration for the real preview dist.
  // inputs: snapshotText - original text supplying only EOL and final-newline style.
  // returns: exact deterministic five-line generated declaration.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: none.
  // END_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.buildGeneratedNextEnv
  const eol = snapshotEol(snapshotText)
  const generated = [
    '/// <reference types="next" />',
    '/// <reference types="next/image-types/global" />',
    'import "./.next-v2-real-preview/dev/types/routes.d.ts";',
    "",
    "// NOTE: This file should not be edited",
    "// see https://nextjs.org/docs/app/api-reference/config/typescript for more information.",
  ].join(eol)
  return snapshotHasFinalNewline(snapshotText) ? `${generated}${eol}` : generated
}

export function classifyNextEnv(snapshotText, currentText) {
  // START_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.classifyNextEnv
  // purpose: Classify next-env.d.ts with exact, closed content equality only.
  // inputs: snapshotText - original content; currentText - current file content.
  // returns: unchanged, generated, or unsafe_user_edit.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: all unrecognized content is unsafe_user_edit.
  // END_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.classifyNextEnv
  if (currentText === snapshotText) return "unchanged"
  if (currentText === buildGeneratedNextEnv(snapshotText)) return "generated"
  return "unsafe_user_edit"
}

export function restoreGeneratedNextEnv(filePath, snapshot) {
  // START_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.restoreGeneratedNextEnv
  // purpose: Restore original bytes/mode only from the exact generated declaration.
  // inputs: filePath - required current file; snapshot - original bytes/text/mode.
  // returns: unchanged, generated, or unsafe_user_edit classification.
  // side_effects: generated content is replaced with exact snapshot bytes and mode.
  // emitted_logs: none.
  // error_behavior: throws for missing/unreadable files; preserves unsafe content.
  // END_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.restoreGeneratedNextEnv
  const currentText = readFileSync(filePath, "utf8")
  const classification = classifyNextEnv(snapshot.text, currentText)
  if (classification === "generated") {
    writeFileSync(filePath, snapshot.bytes)
    chmodSync(filePath, snapshot.mode)
  }
  return classification
}

export function verifyStartupTsconfig(filePath, snapshot, io = {}) {
  // START_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.verifyStartupTsconfig
  // purpose: Verify tsconfig stayed byte-exact during startup and restore drift once.
  // inputs: filePath - required current file; snapshot - original bytes/mode;
  //   io - optional injected write/chmod functions for behavioral tests.
  // returns: true when unchanged; false after exact restoration of detected drift.
  // side_effects: drift is restored to exact snapshot bytes and permission bits.
  // emitted_logs: none.
  // error_behavior: throws for missing/unreadable files or failed restoration.
  // END_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.verifyStartupTsconfig
  const currentBytes = readFileSync(filePath)
  if (currentBytes.equals(snapshot.bytes)) return true
  const writeFileImpl = io.writeFileImpl ?? writeFileSync
  const chmodImpl = io.chmodImpl ?? chmodSync
  writeFileImpl(filePath, snapshot.bytes)
  chmodImpl(filePath, snapshot.mode)
  return false
}
// END_BLOCK: FILE_HYGIENE

// START_BLOCK: PREFLIGHT
export function checkPort(host, port) {
  // START_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.checkPort
  // purpose: Probe whether an address can be bound without touching an occupant.
  // inputs: host - bind host; port - requested port, including ephemeral zero in tests.
  // returns: Promise<boolean> true after bind-and-close, false on bind error.
  // side_effects: briefly binds and closes a TCP server when free.
  // emitted_logs: none.
  // error_behavior: resolves false rather than terminating another process.
  // END_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.checkPort
  return new Promise((resolvePort) => {
    const server = createServer()
    server.once("error", () => resolvePort(false))
    server.once("listening", () => server.close(() => resolvePort(true)))
    server.listen({ host, port, exclusive: true })
  })
}

export async function checkHealth(url, fetchImpl = fetch) {
  // START_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.checkHealth
  // purpose: Check an HTTP health endpoint without reading or logging its body.
  // inputs: url - health URL; fetchImpl - injectable fetch implementation.
  // returns: true only for a 2xx response.
  // side_effects: one bounded HTTP request.
  // emitted_logs: none.
  // error_behavior: network errors and timeout resolve false.
  // END_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.checkHealth
  try {
    const response = await fetchImpl(url, { signal: AbortSignal.timeout(5_000) })
    return response.ok
  } catch (error) {
    return false
  }
}
// END_BLOCK: PREFLIGHT

// START_BLOCK: READINESS
export async function waitForReady(url, childProcess, options = {}) {
  // START_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.waitForReady
  // purpose: Poll Next readiness until exact success, child exit, or deadline.
  // inputs: url - readiness URL; childProcess - child with exitCode;
  //   options - injectable timeout, interval, fetch, clock, and sleep.
  // returns: {status:"ready"}, {status:"child_exited",code}, or {status:"timeout"}.
  // side_effects: bounded HTTP polls and sleeps.
  // emitted_logs: none.
  // error_behavior: fetch errors continue only until the fixed deadline.
  // END_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.waitForReady
  const timeoutMs = options.timeoutMs ?? READY_TIMEOUT_MS
  const intervalMs = options.intervalMs ?? 300
  const fetchImpl = options.fetchImpl ?? fetch
  const nowImpl = options.nowImpl ?? Date.now
  const sleepImpl = options.sleepImpl ?? sleep
  const childErrorImpl = options.childErrorImpl ?? (() => false)
  const deadline = nowImpl() + timeoutMs

  while (true) {
    if (childErrorImpl()) return { status: "child_exited", code: 1 }
    if (childProcess.exitCode !== null) {
      return { status: "child_exited", code: childProcess.exitCode }
    }
    if (nowImpl() >= deadline) return { status: "timeout" }

    const remainingMs = Math.max(1, deadline - nowImpl())
    try {
      const response = await fetchImpl(url, {
        signal: AbortSignal.timeout(Math.min(2_000, remainingMs)),
      })
      if (childErrorImpl()) return { status: "child_exited", code: 1 }
      if (childProcess.exitCode !== null) {
        return { status: "child_exited", code: childProcess.exitCode }
      }
      if (response.status === 200) return { status: "ready" }
    } catch (error) {
      if (childErrorImpl()) return { status: "child_exited", code: 1 }
      if (childProcess.exitCode !== null) {
        return { status: "child_exited", code: childProcess.exitCode }
      }
    }

    if (nowImpl() >= deadline) return { status: "timeout" }
    await sleepImpl(Math.min(intervalMs, Math.max(0, deadline - nowImpl())))
  }
}
// END_BLOCK: READINESS

// START_BLOCK: PROCESS_LIFECYCLE
export function terminateProcessGroup(pid, signal, options = {}) {
  // START_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.terminateProcessGroup
  // purpose: Signal the owned POSIX process group or Windows child safely.
  // inputs: pid - positive child PID; signal - Node signal; options - injected
  //   platform, process.kill implementation, and optional child implementation.
  // returns: true when the signal call succeeds, false when it throws.
  // side_effects: sends one signal; never searches for or kills unrelated PIDs.
  // emitted_logs: none.
  // error_behavior: signal errors are converted to false for bounded escalation.
  // END_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.terminateProcessGroup
  const platform = options.platform ?? process.platform
  const killImpl = options.killImpl ?? process.kill.bind(process)
  try {
    if (platform === "win32" && options.childProcess) {
      return options.childProcess.kill(signal)
    }
    killImpl(platform === "win32" ? pid : -pid, signal)
    return true
  } catch (error) {
    return false
  }
}

function childHasExited(childProcess) {
  return childProcess.exitCode !== null || childProcess.signalCode !== null
}

function waitForChildExit(childProcess, timeoutMs) {
  if (childHasExited(childProcess)) return Promise.resolve(true)
  return new Promise((resolveExit) => {
    let timer = null
    const onExit = () => {
      if (timer) clearTimeout(timer)
      childProcess.removeListener("exit", onExit)
      resolveExit(true)
    }
    timer = setTimeout(() => {
      childProcess.removeListener("exit", onExit)
      resolveExit(childHasExited(childProcess))
    }, timeoutMs)
    childProcess.once("exit", onExit)
  })
}

function restoreNextEnvForShutdown() {
  if (!snapshots) return true
  try {
    const classification = restoreGeneratedNextEnv(NEXT_ENV_PATH, snapshots.nextEnv)
    if (classification === "unsafe_user_edit") {
      warn("Unsafe next-env.d.ts edit preserved; shutdown is failing closed.")
      return false
    }
    return true
  } catch (error) {
    warn("Unable to verify or restore next-env.d.ts; shutdown is failing closed.")
    return false
  }
}

function removeProcessHandlers() {
  if (!processHandlers) return
  process.removeListener("SIGINT", processHandlers.onSigint)
  process.removeListener("SIGTERM", processHandlers.onSigterm)
  process.removeListener("uncaughtException", processHandlers.onUncaught)
  process.removeListener("unhandledRejection", processHandlers.onUnhandled)
}

function installProcessHandlers() {
  const onSigint = () => { void shutdown("SIGINT", 0) }
  const onSigterm = () => { void shutdown("SIGTERM", 0) }
  const onUncaught = (error) => {
    warn(error instanceof Error ? error.message : "Uncaught launcher error")
    void shutdown("uncaughtException", 1)
  }
  const onUnhandled = (error) => {
    warn(error instanceof Error ? error.message : "Unhandled launcher rejection")
    void shutdown("unhandledRejection", 1)
  }
  const onExit = () => {
    if (!restoreNextEnvForShutdown()) process.exitCode = 1
  }
  processHandlers = { onSigint, onSigterm, onUncaught, onUnhandled, onExit }
  process.on("SIGINT", onSigint)
  process.on("SIGTERM", onSigterm)
  process.on("uncaughtException", onUncaught)
  process.on("unhandledRejection", onUnhandled)
  process.on("exit", onExit)
}

export async function shutdown(reason, exitCode = 0) {
  // START_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.shutdown
  // purpose: Own one awaited, idempotent restore/terminate/escalate/restore sequence.
  // inputs: reason - closed lifecycle label; exitCode - requested process result.
  // returns: shared Promise resolving after bounded child exit and final restore.
  // side_effects: restores exact generated next-env, signals the owned child/group,
  //   clears lifecycle listeners/timers, and sets process.exitCode.
  // emitted_logs: prefixed fail-closed file-hygiene errors only.
  // error_behavior: restore or bounded-exit failure forces process.exitCode 1.
  // END_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.shutdown
  if (exitCode !== 0) process.exitCode = 1
  else if (process.exitCode == null) process.exitCode = 0
  if (shutdownPromise) return shutdownPromise

  shutdownPromise = (async () => {
    let clean = restoreNextEnvForShutdown()
    const ownedChild = child
    if (ownedChild?.pid && !childHasExited(ownedChild)) {
      terminateProcessGroup(ownedChild.pid, "SIGTERM", { childProcess: ownedChild })
      const termExited = await waitForChildExit(ownedChild, TERM_TIMEOUT_MS)
      if (!termExited) {
        terminateProcessGroup(ownedChild.pid, "SIGKILL", { childProcess: ownedChild })
        const killExited = await waitForChildExit(ownedChild, KILL_TIMEOUT_MS)
        if (!killExited) clean = false
      }
    }

    if (!restoreNextEnvForShutdown()) clean = false
    removeProcessHandlers()
    if (!clean) process.exitCode = 1
    return { reason, clean }
  })()
  return shutdownPromise
}
// END_BLOCK: PROCESS_LIFECYCLE

// START_BLOCK: MAIN
export async function main() {
  // START_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.main
  // purpose: Run closed preflight, start Next, verify readiness/config, and await exit.
  // inputs: canonical process environment, tracked files, services, and ports.
  // returns: Promise resolving only after the child and shutdown sequence finish.
  // side_effects: health requests, tracked snapshots, Next spawn, lifecycle handlers,
  //   exact startup restoration, and three readiness console labels.
  // emitted_logs: exact post-readiness API/URL/real-backend labels and prefixed errors.
  // error_behavior: throws pre-spawn failures; post-spawn failures use awaited shutdown.
  // END_FUNCTION_CONTRACT: F-M-PREVIEW-V2-REAL.main
  if (!await checkPort(NEXT_HOST, NEXT_PORT)) {
    throw new Error(`Port ${NEXT_PORT} is already occupied; no process was stopped.`)
  }
  if (!await checkHealth(API_HEALTH_URL)) {
    throw new Error(`Canonical API is unavailable on ${API_BASE}`)
  }
  if (!await checkHealth(SIDECAR_HEALTH_URL)) {
    throw new Error(`Canonical sidecar is unavailable on ${SIDECAR_HEALTH_URL}`)
  }

  snapshots = {
    nextEnv: readFileSnapshot(NEXT_ENV_PATH),
    tsconfig: readFileSnapshot(TSCONFIG_PATH),
  }

  child = spawn(
    "pnpm",
    ["exec", "next", "dev", "--hostname", NEXT_HOST, "--port", String(NEXT_PORT)],
    {
      cwd: ROOT,
      stdio: "inherit",
      env: buildEnv(),
      detached: process.platform !== "win32",
    },
  )
  installProcessHandlers()
  let spawnError = null
  const onSpawnError = (error) => {
    spawnError = error
    warn(error.message)
  }
  child.once("error", onSpawnError)
  const ready = await waitForReady(READINESS_URL, child, {
    childErrorImpl: () => spawnError !== null,
  })
  child.removeListener("error", onSpawnError)
  if (ready.status !== "ready") {
    const failureCode = ready.status === "child_exited" && ready.code !== 0 ? ready.code : 1
    await shutdown(ready.status, failureCode)
    return
  }

  if (!verifyStartupTsconfig(TSCONFIG_PATH, snapshots.tsconfig)) {
    warn("tsconfig.json changed during startup; exact snapshot restored.")
    await shutdown("tsconfig_startup_drift", 1)
    return
  }
  const nextEnvClassification = restoreGeneratedNextEnv(NEXT_ENV_PATH, snapshots.nextEnv)
  if (nextEnvClassification === "unsafe_user_edit") {
    warn("Unsafe next-env.d.ts edit preserved; startup is failing closed.")
    await shutdown("unsafe_next_env", 1)
    return
  }

  log(`Real API: ${API_BASE}`)
  log(ACCEPTANCE_URL)
  log("REAL backend preview; no fixture or mock API.")

  const childCode = await new Promise((resolveExit) => {
    if (childHasExited(child)) {
      resolveExit(child.exitCode)
      return
    }
    child.once("exit", (code) => resolveExit(code))
  })
  if (shutdownPromise) {
    await shutdownPromise
    return
  }
  await shutdown("unexpected_child_exit", childCode === 0 ? 1 : childCode ?? 1)
}
// END_BLOCK: MAIN

if (isDirectCli()) {
  main().catch(async (error) => {
    warn(error instanceof Error ? error.message : "Launcher failed")
    await shutdown("main_rejection", 1)
  })
}
