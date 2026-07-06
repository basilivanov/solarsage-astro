import { describe, expect, it } from "vitest"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { execFileSync } from "node:child_process"

const root = process.cwd()

function trackedTextFiles() {
  const output = execFileSync("git", ["ls-files", "docs", "scripts"], {
    cwd: root,
    encoding: "utf8",
  })
  return output
    .split("\n")
    .filter(Boolean)
    .filter((path) => /\.(md|txt|sh|py|ts|tsx|js|json|yml|yaml)$/.test(path))
}

describe("YooKassa credential hygiene", () => {
  it("does not track real-looking live YooKassa credentials in docs or scripts", () => {
    const offenders: string[] = []

    for (const file of trackedTextFiles()) {
      const text = readFileSync(join(root, file), "utf8")
      const patterns = [
        /YOOKASSA_LIVE_SHOP_ID\s*=\s*\d{5,}/i,
        /YOOKASSA_LIVE_SECRET_KEY\s*=\s*live_[A-Za-z0-9_-]{20,}/i,
      ]
      if (patterns.some((pattern) => pattern.test(text))) {
        offenders.push(file)
      }
    }

    expect(offenders).toEqual([])
  })
})
