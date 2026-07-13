// ############################################################################
// AI_HEADER: TEST_PREVIEW_V2_REAL — behavioral tests for the strict launcher.
// ROLE: Proves the launcher's closed config, file, readiness, and process rules
//   with temporary files, ephemeral ports, and injected side effects.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-PREVIEW-V2-REAL
// purpose: Verify the real-preview launcher behavior without starting Next,
//   contacting canonical services, or sending real process signals.
// owns:
//   - __tests__/scripts/preview-v2-real.test.ts
// inputs:
//   - scripts/preview-v2-real.mjs exports
//   - package.json, .gitignore, tsconfig.json, and launcher source
// outputs:
//   - Vitest assertions for the Stage 1.W0 unit matrix
// dependencies:
//   - vitest
//   - node:http, node:fs, node:os, node:path, node:url
// side_effects:
//   - creates and removes temporary directories
//   - briefly binds ephemeral loopback ports
// emitted_logs:
//   - none
// invariants:
//   - no fixed service port is bound
//   - no real process is signalled
//   - no application/backend/generated/contract file is modified
// failure_policy:
//   - every behavioral mismatch fails its owning test
// END_MODULE_CONTRACT: M-TEST-PREVIEW-V2-REAL

// START_MODULE_MAP: M-TEST-PREVIEW-V2-REAL
// public_entrypoints:
//   - Vitest test cases
// semantic_blocks:
//   - CLI_AND_ENV: exact URL, import safety, and child environment
//   - PORT_AND_HEALTH: ephemeral bind and injected health behavior
//   - FILE_HYGIENE: snapshots, exact declaration classifier, and restoration
//   - READINESS: success, child exit, and bounded deadline
//   - PROCESS_SIGNALS: POSIX group and Windows child behavior
//   - TRACKED_CONFIG: exact-once config and forbidden-source guards
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-PREVIEW-V2-REAL

import { chmodSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs"
import http from "node:http"
import { tmpdir } from "node:os"
import { join, resolve } from "node:path"
import { pathToFileURL } from "node:url"
import { describe, expect, it, vi } from "vitest"

import {
  ACCEPTANCE_URL,
  buildEnv,
  buildGeneratedNextEnv,
  checkHealth,
  checkPort,
  classifyNextEnv,
  isDirectCli,
  readFileSnapshot,
  restoreGeneratedNextEnv,
  terminateProcessGroup,
  verifyStartupTsconfig,
  waitForReady,
} from "../../scripts/preview-v2-real.mjs"

const SNAPSHOT_LF = [
  '/// <reference types="next" />',
  '/// <reference types="next/image-types/global" />',
  'import "./.next/types/routes.d.ts";',
  "// NOTE: This file should not be edited",
  "// see https://nextjs.org/docs/app/api-reference/config/typescript for more information.",
  "",
].join("\n")

function withTempDir(run: (directory: string) => void): void {
  const directory = mkdtempSync(join(tmpdir(), "preview-v2-real-"))
  try {
    run(directory)
  } finally {
    rmSync(directory, { recursive: true, force: true })
  }
}

describe("CLI_AND_ENV", () => {
  it("uses the exact acceptance URL, pathname, and sole why=1 query", () => {
    const url = new URL(ACCEPTANCE_URL)
    expect(url.origin).toBe("http://127.0.0.1:3003")
    expect(url.pathname).toBe("/day/2026-07-08")
    expect([...url.searchParams.entries()]).toEqual([["why", "1"]])
  })

  it("overrides a malicious ambient mock base with canonical API 8000", () => {
    const ambient = { NODE_ENV: "development" as const, DEV_API_REWRITE_BASE_URL: "http://127.0.0.1:18092" }
    expect(buildEnv(ambient).DEV_API_REWRITE_BASE_URL).toBe("http://127.0.0.1:8000")
    expect(ambient.DEV_API_REWRITE_BASE_URL).toBe("http://127.0.0.1:18092")
  })

  it("sets exact development, dist, and telemetry values", () => {
    const env = buildEnv({ NODE_ENV: "production", NEXT_TELEMETRY_DISABLED: "0" })
    expect(env.NODE_ENV).toBe("development")
    expect(env.NEXT_DIST_DIR).toBe(".next-v2-real-preview")
    expect(env.NEXT_TELEMETRY_DISABLED).toBe("1")
  })

  it("imports without running main and resolves only absolute or relative direct CLI paths", async () => {
    const scriptPath = resolve("scripts/preview-v2-real.mjs")
    const scriptUrl = pathToFileURL(scriptPath).href
    const beforeSignals = {
      sigint: process.listenerCount("SIGINT"),
      sigterm: process.listenerCount("SIGTERM"),
    }
    expect(isDirectCli(scriptUrl, scriptPath)).toBe(true)
    expect(isDirectCli(scriptUrl, "scripts/preview-v2-real.mjs")).toBe(true)
    expect(isDirectCli(`${scriptUrl}?vitest-import=1`, scriptPath)).toBe(false)
    const imported = await import("../../scripts/preview-v2-real.mjs")
    expect(imported.ACCEPTANCE_URL).toBe(ACCEPTANCE_URL)
    expect(process.listenerCount("SIGINT")).toBe(beforeSignals.sigint)
    expect(process.listenerCount("SIGTERM")).toBe(beforeSignals.sigterm)
  })
})

describe("PORT_AND_HEALTH", () => {
  it("binds and closes a free ephemeral port", async () => {
    await expect(checkPort("127.0.0.1", 0)).resolves.toBe(true)
  })

  it("reports an occupied ephemeral port and leaves its occupant alive", async () => {
    const server = http.createServer()
    await new Promise<void>((resolveListen, rejectListen) => {
      server.once("error", rejectListen)
      server.listen(0, "127.0.0.1", resolveListen)
    })
    try {
      const address = server.address()
      if (!address || typeof address === "string") throw new Error("Expected TCP address")
      await expect(checkPort("127.0.0.1", address.port)).resolves.toBe(false)
      expect(server.listening).toBe(true)
    } finally {
      await new Promise<void>((resolveClose, rejectClose) => {
        server.close((error) => error ? rejectClose(error) : resolveClose())
      })
    }
  })

  it("accepts a 2xx health response", async () => {
    const fetchImpl = vi.fn(async () => new Response(null, { status: 204 }))
    await expect(checkHealth("http://health.invalid", fetchImpl)).resolves.toBe(true)
    expect(fetchImpl).toHaveBeenCalledOnce()
  })

  it("rejects a non-2xx health response", async () => {
    const fetchImpl = vi.fn(async () => new Response(null, { status: 503 }))
    await expect(checkHealth("http://health.invalid", fetchImpl)).resolves.toBe(false)
  })

  it("rejects a health network error", async () => {
    const fetchImpl = vi.fn(async () => { throw new Error("network timeout") })
    await expect(checkHealth("http://health.invalid", fetchImpl)).resolves.toBe(false)
  })
})

describe("FILE_HYGIENE", () => {
  it("snapshots exact UTF-8 bytes/text and permission bits", () => {
    withTempDir((directory) => {
      const filePath = join(directory, "tracked.txt")
      const content = "точный текст\r\n"
      writeFileSync(filePath, content, "utf8")
      chmodSync(filePath, 0o640)
      const snapshot = readFileSnapshot(filePath)
      expect(snapshot.bytes.equals(Buffer.from(content, "utf8"))).toBe(true)
      expect(snapshot.text).toBe(content)
      expect(snapshot.mode).toBe(0o640)
    })
  })

  it("fails closed when a required snapshot file is missing", () => {
    withTempDir((directory) => {
      expect(() => readFileSnapshot(join(directory, "missing.txt"))).toThrow()
    })
  })

  it("classifies only the exact LF generated declaration", () => {
    const generated = buildGeneratedNextEnv(SNAPSHOT_LF)
    expect(classifyNextEnv(SNAPSHOT_LF, SNAPSHOT_LF)).toBe("unchanged")
    expect(classifyNextEnv(SNAPSHOT_LF, generated)).toBe("generated")
    expect(generated.split("\n").filter(Boolean)).toHaveLength(5)
  })

  it("preserves CRLF and final-newline style in the exact classifier", () => {
    const snapshot = SNAPSHOT_LF.replaceAll("\n", "\r\n")
    const generated = buildGeneratedNextEnv(snapshot)
    expect(generated).toContain("\r\n")
    expect(generated.endsWith("\r\n")).toBe(true)
    expect(classifyNextEnv(snapshot, generated)).toBe("generated")
  })

  it("preserves an absent final newline in the exact classifier", () => {
    const snapshot = SNAPSHOT_LF.slice(0, -1)
    const generated = buildGeneratedNextEnv(snapshot)
    expect(generated.endsWith("\n")).toBe(false)
    expect(classifyNextEnv(snapshot, generated)).toBe("generated")
  })

  it("classifies an arbitrary extra line as unsafe", () => {
    const generated = `${buildGeneratedNextEnv(SNAPSHOT_LF)}console.log("edit")\n`
    expect(classifyNextEnv(SNAPSHOT_LF, generated)).toBe("unsafe_user_edit")
  })

  it("classifies the non-dev real-preview route import as unsafe", () => {
    const nonDevPath = buildGeneratedNextEnv(SNAPSHOT_LF).replace("/dev/types/routes.d.ts", "/types/routes.d.ts")
    expect(classifyNextEnv(SNAPSHOT_LF, nonDevPath)).toBe("unsafe_user_edit")
  })

  it("classifies a declaration importing another dev dist as unsafe", () => {
    const wrongDist = buildGeneratedNextEnv(SNAPSHOT_LF).replace(".next-v2-real-preview", ".next-other")
    expect(classifyNextEnv(SNAPSHOT_LF, wrongDist)).toBe("unsafe_user_edit")
  })

  it("restores exact snapshot bytes and original permission bits", () => {
    withTempDir((directory) => {
      const filePath = join(directory, "next-env.d.ts")
      writeFileSync(filePath, buildGeneratedNextEnv(SNAPSHOT_LF), "utf8")
      chmodSync(filePath, 0o600)
      const snapshot = { bytes: Buffer.from(SNAPSHOT_LF), text: SNAPSHOT_LF, mode: 0o640 }
      expect(restoreGeneratedNextEnv(filePath, snapshot)).toBe("generated")
      expect(readFileSync(filePath).equals(snapshot.bytes)).toBe(true)
      expect(statSync(filePath).mode & 0o777).toBe(0o640)
    })
  })

  it("preserves unsafe user content without changing bytes or mode", () => {
    withTempDir((directory) => {
      const filePath = join(directory, "next-env.d.ts")
      const unsafe = `${SNAPSHOT_LF}// user-owned edit\n`
      writeFileSync(filePath, unsafe, "utf8")
      chmodSync(filePath, 0o600)
      const snapshot = { bytes: Buffer.from(SNAPSHOT_LF), text: SNAPSHOT_LF, mode: 0o640 }
      expect(restoreGeneratedNextEnv(filePath, snapshot)).toBe("unsafe_user_edit")
      expect(readFileSync(filePath, "utf8")).toBe(unsafe)
      expect(statSync(filePath).mode & 0o777).toBe(0o600)
    })
  })

  it("passes equal tsconfig bytes without a runtime write", () => {
    withTempDir((directory) => {
      const filePath = join(directory, "tsconfig.json")
      const bytes = Buffer.from('{"compilerOptions":{}}\n')
      writeFileSync(filePath, bytes)
      const writeFileImpl = vi.fn()
      const chmodImpl = vi.fn()
      expect(verifyStartupTsconfig(filePath, { bytes, text: bytes.toString("utf8"), mode: 0o644 }, { writeFileImpl, chmodImpl })).toBe(true)
      expect(writeFileImpl).not.toHaveBeenCalled()
      expect(chmodImpl).not.toHaveBeenCalled()
    })
  })

  it("restores startup tsconfig drift exactly and fails the verification", () => {
    withTempDir((directory) => {
      const filePath = join(directory, "tsconfig.json")
      const snapshotBytes = Buffer.from('{"compilerOptions":{}}\n')
      writeFileSync(filePath, '{"compilerOptions":{"strict":true}}\n', "utf8")
      chmodSync(filePath, 0o600)
      const snapshot = { bytes: snapshotBytes, text: snapshotBytes.toString("utf8"), mode: 0o640 }
      expect(verifyStartupTsconfig(filePath, snapshot)).toBe(false)
      expect(readFileSync(filePath).equals(snapshotBytes)).toBe(true)
      expect(statSync(filePath).mode & 0o777).toBe(0o640)
    })
  })
})

describe("READINESS", () => {
  it("returns ready on an exact successful poll", async () => {
    const fetchImpl = vi.fn(async () => new Response(null, { status: 200 }))
    await expect(waitForReady("http://ready.invalid", { exitCode: null }, { fetchImpl, timeoutMs: 10 })).resolves.toEqual({ status: "ready" })
    expect(fetchImpl).toHaveBeenCalledOnce()
  })

  it("returns the child exit code before polling", async () => {
    const fetchImpl = vi.fn(async () => new Response(null, { status: 200 }))
    await expect(waitForReady("http://ready.invalid", { exitCode: 17 }, { fetchImpl, timeoutMs: 10 })).resolves.toEqual({ status: "child_exited", code: 17 })
    expect(fetchImpl).not.toHaveBeenCalled()
  })

  it("returns a closed child-exited result for an injected spawn error", async () => {
    const fetchImpl = vi.fn(async () => new Response(null, { status: 200 }))
    await expect(waitForReady("http://ready.invalid", { exitCode: null }, {
      childErrorImpl: () => true,
      fetchImpl,
      timeoutMs: 10,
    })).resolves.toEqual({ status: "child_exited", code: 1 })
    expect(fetchImpl).not.toHaveBeenCalled()
  })

  it("terminates polling at the injected deadline", async () => {
    let now = 1_000
    const fetchImpl = vi.fn(async () => new Response(null, { status: 503 }))
    const sleepImpl = vi.fn(async (milliseconds: number) => { now += milliseconds })
    await expect(waitForReady("http://ready.invalid", { exitCode: null }, {
      fetchImpl,
      nowImpl: () => now,
      sleepImpl,
      timeoutMs: 25,
      intervalMs: 10,
    })).resolves.toEqual({ status: "timeout" })
    expect(fetchImpl).toHaveBeenCalledTimes(3)
    expect(now).toBe(1_025)
  })
})

describe("PROCESS_SIGNALS", () => {
  it("signals the negative POSIX process-group PID", () => {
    const killImpl = vi.fn()
    expect(terminateProcessGroup(12_345, "SIGTERM", { platform: "linux", killImpl })).toBe(true)
    expect(killImpl).toHaveBeenCalledWith(-12_345, "SIGTERM")
  })

  it("signals the positive Windows child path without group kill", () => {
    const killImpl = vi.fn()
    const childProcess = { kill: vi.fn(() => true) }
    expect(terminateProcessGroup(12_345, "SIGKILL", { platform: "win32", killImpl, childProcess })).toBe(true)
    expect(childProcess.kill).toHaveBeenCalledWith("SIGKILL")
    expect(killImpl).not.toHaveBeenCalled()
  })
})

describe("TRACKED_CONFIG", () => {
  it("owns the exact package launcher script once", () => {
    const packageText = readFileSync("package.json", "utf8")
    const packageJson = JSON.parse(packageText)
    expect(packageJson.scripts["preview:v2:real"]).toBe("node scripts/preview-v2-real.mjs")
    expect(packageText.match(/"preview:v2:real"/g)).toHaveLength(1)
  })

  it("owns the exact real-preview gitignore entry once", () => {
    const lines = readFileSync(".gitignore", "utf8").split(/\r?\n/)
    expect(lines.filter((line) => line === ".next-v2-real-preview/")).toHaveLength(1)
  })

  it("owns both real-preview tsconfig globs exactly once", () => {
    const config = JSON.parse(readFileSync("tsconfig.json", "utf8"))
    const include: string[] = config.include
    expect(include.filter((entry) => entry === ".next-v2-real-preview/types/**/*.ts")).toHaveLength(1)
    expect(include.filter((entry) => entry === ".next-v2-real-preview/dev/types/**/*.ts")).toHaveLength(1)
  })

  it("contains no functional mock server, manual API, shell exec, or interception", () => {
    const source = readFileSync("scripts/preview-v2-real.mjs", "utf8")
    const functionalLines = source.split(/\r?\n/).filter((line) => !line.trimStart().startsWith("//"))
    const functionalSource = functionalLines.join("\n")
    expect(functionalSource).not.toContain("18092")
    expect(functionalSource).not.toMatch(/\buvicorn\b/)
    expect(functionalSource).not.toContain("page.route")
    expect(functionalSource).not.toMatch(/\bexec(?:File|Sync)?\s*\(/)
    expect(functionalSource).not.toMatch(/\brequire\s*\(/)
  })
})
