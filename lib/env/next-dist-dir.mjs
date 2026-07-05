export function resolveNextDistDir(env = process.env) {
  const explicit = env.NEXT_DIST_DIR?.trim()
  if (explicit) return explicit
  return env.NODE_ENV === "production" ? ".next-prod" : ".next"
}
