# ############################################################################
# AI_HEADER: MODULE_DEPLOY_SOLARSAGE_DOCKERFILE — sidecar Docker image build recipe.
# ROLE: Builds the SolarSage sidecar image from repo-root context with shared contracts installed first.
# ############################################################################

# START_MODULE_CONTRACT: M-DEPLOY-SOLARSAGE-DOCKERFILE
# purpose: Build a Python 3.12 sidecar container with compiler tooling isolated
#   to a builder stage while runtime installs only local wheels.
# owns:
#   - apps/solarsage/Dockerfile
# inputs: repo-root Docker context containing packages/py-contracts, apps/solarsage, and grace/canon.
# outputs: Docker image exposing solarsage.app:app on container port 8001.
# dependencies: python:3.12-slim, pip, packages/py-contracts, apps/solarsage, grace/canon/*.yml.
# side_effects: package installation inside image build.
# emitted_logs: none.
# invariants:
#   - No root env/secrets are copied into the image.
#   - Compiler toolchain is absent from the runtime stage.
#   - Runtime stage contains /usr/local/lib/grace/canon for installed sidecar canon loaders.
#   - Shared package is built before the sidecar package and installed from wheels.
#   - Runtime command uses solarsage.app:app and keeps container port 8001.
# failure_policy: Docker build fails on pip install or pip check errors; runtime exits on server failure.
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
FROM python:3.12-slim AS builder

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
FROM python:3.12-slim

WORKDIR /app

RUN python -m pip install --no-cache-dir --upgrade pip

COPY --from=builder /tmp/wheels /tmp/wheels
COPY grace/canon /usr/local/lib/grace/canon
RUN python -m pip install --no-cache-dir --no-index --find-links /tmp/wheels solarsage \
    && python -m pip check \
    && rm -rf /tmp/wheels

ARG RELEASE_SHA=unknown
ENV SOLARSAGE_RELEASE_SHA=${RELEASE_SHA}
LABEL org.opencontainers.image.revision="${RELEASE_SHA}"

EXPOSE 8001

CMD ["uvicorn", "solarsage.app:app", "--host", "0.0.0.0", "--port", "8001"]
# END_BLOCK: SIDECAR_RUNTIME
