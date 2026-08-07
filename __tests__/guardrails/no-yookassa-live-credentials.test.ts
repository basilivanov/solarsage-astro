import { describe, expect, it } from "vitest"
import { existsSync, readFileSync } from "node:fs"
import { join } from "node:path"
import { execFileSync } from "node:child_process"

const root = process.cwd()

function trackedTextFiles() {
  const output = execFileSync("git", ["ls-files", "-z"], {
    cwd: root,
    encoding: "buffer",
  })
  return output
    .toString("utf8")
    .split("\0")
    .filter(Boolean)
    // A local worktree may contain an uncommitted deletion. Keep the guardrail
    // usable during review diffs; the reviewer commit removes the path from
    // git ls-files, while unexpected read errors still surface below.
    .filter((path) => {
      if (!existsSync(join(root, path))) return false
      return !readFileSync(join(root, path)).includes(0)
    })
}

function findYooKassaCredentialLeaks(text: string) {
  const leaks: Array<{ key: string; value: string }> = []
  const assignment =
    /["'`]?((?:YOOKASSA_)(?:(?:LIVE|TEST)_)?(?:SHOP_ID|SECRET_KEY))["'`]?\s*(?:=|:)\s*(?:"([^"\r\n]*)"|'([^'\r\n]*)'|`([^`\r\n]*)`|([^\r\n#]*))/gi

  for (const match of text.matchAll(assignment)) {
    const key = match[1].toUpperCase()
    const rawValue = match[2] ?? match[3] ?? match[4] ?? match[5] ?? ""
    const value = rawValue
      .trim()
      .replace(/^[`"']+|[`"',}\]]+$/g, "")
      .trim()

    // Only explicit synthetic canaries are allowed. A test_ prefix is NOT a
    // safe marker: real YooKassa SANDBOX secrets also start with test_.
    if (
      value === "" ||
      /^<[^>]+>$/.test(value) ||
      /^REDACTED$/i.test(value)
    ) {
      continue
    }

    const isShopId = key.endsWith("SHOP_ID")
    const isRealLooking = isShopId
      ? /^\d{5,}$/.test(value)
      : /^(?:live_|test_)?[A-Za-z0-9_-]{24,}$/.test(value)

    if (isRealLooking) {
      leaks.push({ key, value })
    }
  }

  return leaks
}

describe("YooKassa credential hygiene", () => {
  it("detects live-looking YooKassa assignments across common text formats", () => {
    const shopKey = "YOOKASSA_SHOP_ID"
    const secretKey = "YOOKASSA_SECRET_KEY"
    const liveShopKey = "YOOKASSA_LIVE_SHOP_ID"
    const liveSecretKey = "YOOKASSA_LIVE_SECRET_KEY"
    const testShopKey = "YOOKASSA_TEST_SHOP_ID"
    const testSecretKey = "YOOKASSA_TEST_SECRET_KEY"
    const liveSecret = "live_" + "K_jp1ZvDWs89sdwLCMlvxbWIywx1Hz_mZyxPF3EjFiw"
    const sandboxSecret = "test_" + "K_jp1ZvDWs89sdwLCMlvxbWIywx1Hz_mZyxPF3EjFiw"
    const sample = [
      `${shopKey}=1317569`,
      `${secretKey}: ${liveSecret}`,
      `"${liveShopKey}": "1317569"`,
      `\`${liveSecretKey}=${liveSecret}\``,
      `${testShopKey}=1317569`,
      `${testSecretKey}: ${sandboxSecret}`,
    ].join("\n")

    expect(findYooKassaCredentialLeaks(sample)).toHaveLength(6)
  })

  it("allows only explicit placeholders, blanks and redacted canaries — never a test_ prefix", () => {
    const shopKey = "YOOKASSA_SHOP_ID"
    const secretKey = "YOOKASSA_SECRET_KEY"
    const liveShopKey = "YOOKASSA_LIVE_SHOP_ID"
    const liveSecretKey = "YOOKASSA_LIVE_SECRET_KEY"
    const testShopKey = "YOOKASSA_TEST_SHOP_ID"
    const testSecretKey = "YOOKASSA_TEST_SECRET_KEY"
    const allowed = [
      `${shopKey}=<set-in-secret-store>`,
      `${secretKey}=REDACTED`,
      `${liveShopKey}=`,
      `${liveSecretKey}=<placeholder>`,
      `${testShopKey}=<set-in-secret-store>`,
      `${testSecretKey}=`,
      `${testSecretKey}=REDACTED`,
    ].join("\n")
    expect(findYooKassaCredentialLeaks(allowed)).toEqual([])

    // A test_-prefixed REAL-looking sandbox secret must now fail: the old
    // blanket test_ whitelist accepted exactly this shape.
    const sandboxSecret = "test_" + "K_jp1ZvDWs89sdwLCMlvxbWIywx1Hz_mZyxPF3EjFiw"
    const rejected = [
      `${testSecretKey}=${sandboxSecret}`,
      `${liveSecretKey}=${sandboxSecret}`,
    ].join("\n")
    expect(findYooKassaCredentialLeaks(rejected)).toHaveLength(2)
  })

  it("does not track real-looking YooKassa credentials in tracked text files", () => {
    const offenders: string[] = []

    for (const file of trackedTextFiles()) {
      const text = readFileSync(join(root, file), "utf8")
      if (findYooKassaCredentialLeaks(text).length > 0) {
        offenders.push(file)
      }
    }

    expect(offenders).toEqual([])
  })
})
