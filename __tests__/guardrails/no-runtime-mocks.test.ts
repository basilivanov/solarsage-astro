import { describe, expect, it } from "vitest"
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs"
import { dirname, join, normalize } from "node:path"

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
  return [
    ...source.matchAll(/(?:from\s+|import\s*(?:\(\s*)?)["']([^"']+)["']/g),
    ...source.matchAll(/require\s*\(\s*["']([^"']+)["']\s*\)/g),
  ].map((match) => match[1])
}

function stripExtension(path: string) {
  return path.replace(/\.(tsx?|jsx?)$/, "")
}

function normalizedImportPath(file: string, importPath: string) {
  if (importPath.startsWith("@/")) {
    return stripExtension(importPath.slice(2))
  }
  if (importPath.startsWith(".")) {
    return stripExtension(normalize(join(dirname(file), importPath)))
  }
  return stripExtension(importPath)
}

function isForbiddenImport(file: string, importPath: string) {
  const candidates = [importPath, normalizedImportPath(file, importPath)].map(
    stripExtension,
  )
  return candidates.some((candidate) =>
    forbidden.some((path) => candidate === path || candidate.startsWith(`${path}/`)),
  )
}

function listSourceFiles(root: string): string[] {
  if (!existsSync(root)) return []
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
          .filter((importPath) => isForbiddenImport(file, importPath))
          .map((importPath) => `${file}: imports ${importPath}`)
      })

    expect(violations).toEqual([])
  })
})
