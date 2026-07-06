import { describe, expect, it } from "vitest"
import { readFileSync } from "node:fs"
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
    .filter((path) => !readFileSync(join(root, path)).includes(0))
}

function findYooKassaCredentialLeaks(text: string) {
  const leaks: Array<{ key: string; value: string }> = []
  const assignment =
    /["'`]?((?:YOOKASSA_)(?:LIVE_)?(?:SHOP_ID|SECRET_KEY))["'`]?\s*(?:=|:)\s*(?:"([^"\r\n]*)"|'([^'\r\n]*)'|`([^`\r\n]*)`|([^\r\n#]*))/gi

  for (const match of text.matchAll(assignment)) {
    const key = match[1].toUpperCase()
    const rawValue = match[2] ?? match[3] ?? match[4] ?? match[5] ?? ""
    const value = rawValue
      .trim()
      .replace(/^[`"']+|[`"',}\]]+$/g, "")
      .trim()

    if (
      value === "" ||
      /^<[^>]+>$/.test(value) ||
      /^REDACTED$/i.test(value) ||
      /^test_/i.test(value)
    ) {
      continue
    }

    const isShopId = key.endsWith("SHOP_ID")
    const isLiveLooking = isShopId
      ? /^\d{5,}$/.test(value)
      : /^(?:live_)?[A-Za-z0-9_-]{24,}$/.test(value)

    if (isLiveLooking) {
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
    const liveSecret = "live_" + "K_jp1ZvDWs89sdwLCMlvxbWIywx1Hz_mZyxPF3EjFiw"
    const sample = [
      `${shopKey}=1317569`,
      `${secretKey}: ${liveSecret}`,
      `"${liveShopKey}": "1317569"`,
      `\`${liveSecretKey}=${liveSecret}\``,
    ].join("\n")

    expect(findYooKassaCredentialLeaks(sample)).toHaveLength(4)
  })

  it("allows placeholders, blanks, redacted values, and sandbox examples", () => {
    const shopKey = "YOOKASSA_SHOP_ID"
    const secretKey = "YOOKASSA_SECRET_KEY"
    const liveShopKey = "YOOKASSA_LIVE_SHOP_ID"
    const liveSecretKey = "YOOKASSA_LIVE_SECRET_KEY"
    const sample = [
      `${shopKey}=<set-in-secret-store>`,
      `${secretKey}=REDACTED`,
      `${liveShopKey}=`,
      `${liveSecretKey}=test_K_jp1ZvDWs89sdwLCMlvxbWIywx1Hz_mZyxPF3EjFiw`,
    ].join("\n")

    expect(findYooKassaCredentialLeaks(sample)).toEqual([])
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
