# ############################################################################
# AI_HEADER: MODULE_DEPLOY_FRONTEND_DOCKERFILE — frontend Docker image recipe
# ROLE: Builds the root Next.js production image from the repository context;
#       replaces the obsolete apps/web Vite dist + nginx recipe.
# DEPENDENCIES: node:20-slim (multi-arch digest-pinned), pnpm (corepack), Next.js production build
# GRACE_ANCHORS: [FRONTEND_IMAGE]
# ############################################################################

# START_MODULE_CONTRACT: M-DEPLOY-FRONTEND
# purpose: Deterministic Next.js production image for the canonical app stack.
# owns:
#   - apps/web/Dockerfile
# inputs:
#   - repo-root Docker context (package.json, pnpm-lock.yaml, app/, components/,
#     lib/, hooks/, public/, next.config.mjs, tsconfig.json, ...)
#   - build ARG RELEASE_SHA (image metadata label only, non-secret)
#   - build ARG PROD_API_REWRITE_BASE_URL (default http://api:8000, non-secret;
#     baked into routes-manifest at build time)
# outputs: Next.js production server image listening on container port 3002.
# dependencies: node:20-slim base (multi-arch digest-pinned), frozen pnpm lockfile.
# side_effects: pnpm install and next build inside the image build only.
# emitted_logs: none.
# invariants:
#   - Both stages are pinned by the verified multi-arch index digest, never a mutable tag.
#   - No .env, Telegram token, OpenRouter key, DB password or SSH material in
#     any layer; build uses only non-secret NEXT_PUBLIC/defaults.
#   - Build runs next build once; runtime runs next start, never pnpm dev.
#   - Runtime distDir resolves to .next-prod under NODE_ENV=production.
# failure_policy: Docker build fails on install/build errors.
# END_MODULE_CONTRACT: M-DEPLOY-FRONTEND

# START_MODULE_MAP: M-DEPLOY-FRONTEND
# public_entrypoints:
#   - docker build -f apps/web/Dockerfile .
# semantic_blocks:
#   - FRONTEND_DEPS: frozen dependency installation
#   - FRONTEND_BUILD: production next build
#   - FRONTEND_RUNTIME: minimal next start runtime
# END_MODULE_MAP: M-DEPLOY-FRONTEND

# START_BLOCK: FRONTEND_DEPS
# Base image pinned by multi-arch index digest (source tag node:20-slim,
# version 20-bookworm-slim; verified via docker buildx imagetools inspect on
# 2026-07-19). The runtime stage below uses the same pinned digest.
FROM node:20-slim@sha256:2cf067cfed83d5ea958367df9f966191a942351a2df77d6f0193e162b5febfc0 AS deps

RUN corepack enable
WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
# END_BLOCK: FRONTEND_DEPS

# START_BLOCK: FRONTEND_BUILD
FROM deps AS builder

WORKDIR /app
COPY . .

# Server-only production API rewrite base baked into routes-manifest at build
# time. Canonical Compose networking uses http://api:8000; the runtime fallback
# outside Compose (unset variable) remains http://127.0.0.1:8000.
ARG PROD_API_REWRITE_BASE_URL=http://api:8000
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PROD_API_REWRITE_BASE_URL=${PROD_API_REWRITE_BASE_URL}

ARG RELEASE_SHA=unknown
LABEL org.opencontainers.image.revision="${RELEASE_SHA}"

RUN pnpm build
# END_BLOCK: FRONTEND_BUILD

# START_BLOCK: FRONTEND_RUNTIME
# Same pinned base as the deps stage (source tag node:20-slim,
# version 20-bookworm-slim).
FROM node:20-slim@sha256:2cf067cfed83d5ea958367df9f966191a942351a2df77d6f0193e162b5febfc0

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile --prod

COPY --from=builder /app/.next-prod ./.next-prod
COPY --from=builder /app/next.config.mjs ./
COPY --from=builder /app/lib ./lib
COPY --from=builder /app/public ./public

ARG RELEASE_SHA=unknown
LABEL org.opencontainers.image.revision="${RELEASE_SHA}"

EXPOSE 3002

CMD ["./node_modules/.bin/next", "start", "-p", "3002"]
# END_BLOCK: FRONTEND_RUNTIME
