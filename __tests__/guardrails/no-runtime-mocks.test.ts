import { describe, expect, it } from "vitest"
import { readdirSync, readFileSync, statSync } from "node:fs"
import { join } from "node:path"

const roots = ["app/(grace)", "components", "hooks", "lib/api", "lib/adapters", "lib/grace"]
const forbidden = [
  "lib/demo-data",
  "@/lib/demo-data",
  "lib/demo-mode",
  "@/lib/demo-mode",
  "lib/mocks",
  "@/lib/mocks",
]

function isSourceFile(path: string) {
  return (path.endsWith(".ts") || path.endsWith(".tsx")) && !path.includes(".test.")
}

function importedPaths(source: string) {
  return Array.from(
    source.matchAll(/(?:from\s+|import\s*(?:\(\s*)?)["']([^"']+)["']/g),
    (match) => match[1]
  )
}

function listSourceFiles(root: string): string[] {
  const entries = readdirSync(root)
  const files: string[] = []

  for (const entry of entries) {
    const path = join(root, entry)
    const stat = statSync(path)

    if (stat.isDirectory()) {
      files.push(...listSourceFiles(path))
      continue
    }

    if (stat.isFile() && isSourceFile(path)) {
      files.push(path)
    }
  }

  return files
}

describe("runtime mock imports", () => {
  it("are not used by product runtime paths", () => {
    const violations = roots
      .flatMap(listSourceFiles)
      .flatMap((file) => {
        const source = readFileSync(file, "utf8")
        return importedPaths(source)
          .filter((importPath) => forbidden.some((path) => importPath === path || importPath.startsWith(`${path}/`)))
          .map((importPath) => `${file}: imports ${importPath}`)
      })

    expect(violations).toEqual([])
  })
})
