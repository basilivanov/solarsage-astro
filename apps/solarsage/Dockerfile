# syntax=docker/dockerfile:1
# ############################################################################
# AI_HEADER: MODULE_DEPLOY_SOLARSAGE_DOCKERFILE — sidecar Docker image build recipe.
# ROLE: Builds the SolarSage sidecar image from repo-root context with shared contracts installed first.
# ############################################################################

# START_MODULE_CONTRACT: M-DEPLOY-SOLARSAGE-DOCKERFILE
# purpose: Build a Python 3.12 sidecar container with compiler tooling isolated
#   to a builder stage while runtime installs only local wheels.
# owns:
#   - apps/solarsage/Dockerfile
# inputs: repo-root Docker context containing packages/py-contracts, apps/solarsage, and grace/canon; named BuildKit context `ephemeris` with the licensed Swiss bundle (never Git/never secret).
# outputs: Docker image exposing solarsage.app:app on container port 8001 with the verified ephemeris bundle at /opt/solarsage-ephemeris/bundle.
# dependencies: python:3.12-slim (multi-arch digest-pinned), pip, packages/py-contracts, apps/solarsage, grace/canon/*.yml, pyswisseph.
# side_effects: package installation inside image build.
# emitted_logs: none.
# invariants:
#   - Both stages are pinned by the verified multi-arch index digest, never a mutable tag.
#   - No root env/secrets are copied into the image.
#   - Compiler toolchain is absent from the runtime stage.
#   - Runtime stage contains /usr/local/lib/grace/canon for installed sidecar canon loaders.
#   - Shared package is built before the sidecar package and installed from wheels.
#   - Runtime command uses solarsage.app:app and keeps container port 8001.
#   - Build FAILS CLOSED without a valid ephemeris bundle or on a Moshier probe.
# failure_policy: Docker build fails on pip install, pip check, artifact verification, or engine probe errors; runtime exits on server failure.
# END_MODULE_CONTRACT: M-DEPLOY-SOLARSAGE-DOCKERFILE

# START_MODULE_MAP: M-DEPLOY-SOLARSAGE-DOCKERFILE
# public_entrypoints:
#   - docker build -f apps/solarsage/Dockerfile .
# semantic_blocks:
#   - SIDECAR_BUILDER: wheel build with compiler toolchain.
#   - SIDECAR_RUNTIME: wheel-only runtime image and command.
# owned_tests:
#   - docker proof build/import smoke in Stage A2
# END_MODULE_MAP: M-DEPLOY-SOLARSAGE-DOCKERFILE

# START_BLOCK: SIDECAR_BUILDER
# Base image pinned by multi-arch index digest (source tag python:3.12-slim,
# version 3.12.13-slim-trixie; verified via docker buildx imagetools inspect
# on 2026-07-19). The runtime stage below uses the same pinned digest.
FROM python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de AS builder

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends g++ gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir --upgrade pip

COPY packages/py-contracts /tmp/solarsage-py-contracts
RUN python -m pip wheel --no-cache-dir --wheel-dir /tmp/wheels /tmp/solarsage-py-contracts

COPY apps/solarsage /app
RUN python -m pip wheel --no-cache-dir --wheel-dir /tmp/wheels --find-links /tmp/wheels .
# END_BLOCK: SIDECAR_BUILDER

# START_BLOCK: SIDECAR_RUNTIME
# Same pinned base as the builder stage (source tag python:3.12-slim,
# version 3.12.13-slim-trixie).
FROM python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de

WORKDIR /app

RUN python -m pip install --no-cache-dir --upgrade pip

COPY --from=builder /tmp/wheels /tmp/wheels
COPY grace/canon /usr/local/lib/grace/canon
RUN python -m pip install --no-cache-dir --no-index --find-links /tmp/wheels solarsage \
    && python -m pip check \
    && rm -rf /tmp/wheels

# START_BLOCK: EPHEMERIS_BUNDLE_GATE
# Pinned Swiss Ephemeris bundle baked into the image from a NAMED BuildKit
# context `ephemeris` (never from Git, never a secret in a layer). The single
# verifier owner (solarsage.core.ephemeris_runtime) proves manifest +
# inventory + fixed/boundary probes with returned FLG_SWIEPH; the build fails
# closed on any violation or a Moshier fallback.
COPY --from=ephemeris . /opt/solarsage-ephemeris/bundle/
RUN SOLARSAGE_APP_ENV=production SOLARSAGE_EPHEMERIS_ROOT=/opt/solarsage-ephemeris/bundle \
    python -c 'from solarsage.core.ephemeris_runtime import verify_and_configure; \
identity = verify_and_configure(); \
assert identity.engine == "swieph" and not identity.fallback, identity; \
print("ephemeris build gate OK:", identity.artifact_id)'
# Bundle is immutable at runtime: root-owned, dirs 0555, files 0444.
RUN chown -R root:root /opt/solarsage-ephemeris/bundle \
    && find /opt/solarsage-ephemeris/bundle -type d -exec chmod 0555 {} + \
    && find /opt/solarsage-ephemeris/bundle -type f -exec chmod 0444 {} +
# END_BLOCK: EPHEMERIS_BUNDLE_GATE

ARG RELEASE_SHA=unknown
ENV SOLARSAGE_RELEASE_SHA=${RELEASE_SHA}
ENV SOLARSAGE_EPHEMERIS_ROOT=/opt/solarsage-ephemeris/bundle
LABEL org.opencontainers.image.revision="${RELEASE_SHA}"

EXPOSE 8001

CMD ["uvicorn", "solarsage.app:app", "--host", "0.0.0.0", "--port", "8001"]
# END_BLOCK: SIDECAR_RUNTIME
