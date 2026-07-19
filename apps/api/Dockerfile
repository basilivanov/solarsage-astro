# ############################################################################
# AI_HEADER: MODULE_DEPLOY_API_DOCKERFILE — API Docker image build recipe.
# ROLE: Builds the FastAPI API image from repo-root context with shared contracts installed first.
# ############################################################################

# START_MODULE_CONTRACT: M-DEPLOY-API-DOCKERFILE
# purpose: Build a Python 3.12 API container that installs the local
#   solarsage-contracts package before installing the API package.
# owns:
#   - apps/api/Dockerfile
# inputs: repo-root Docker context containing packages/py-contracts, apps/api, and grace/canon.
# outputs: Docker image exposing installed app.main:app on container port 8000.
# dependencies: python:3.12-slim (multi-arch digest-pinned), pip, packages/py-contracts, apps/api, grace/canon.
# side_effects: package installation inside image build; no Alembic migration on
#   ordinary container start (migrate is a separate one-shot compose profile).
# emitted_logs: none.
# invariants:
#   - Base image is pinned by the verified multi-arch index digest, never a mutable tag.
#   - No root env/secrets are copied into the image.
#   - Shared package is installed before the API package.
#   - Runtime imports the installed API package, not the shallow /app source copy.
#   - Runtime command keeps container API port 8000.
#   - RELEASE_SHA is received as a non-secret build ARG/env and OCI label.
# failure_policy: Docker build fails on pip install or pip check errors; runtime exits on server failure.
# END_MODULE_CONTRACT: M-DEPLOY-API-DOCKERFILE

# START_MODULE_MAP: M-DEPLOY-API-DOCKERFILE
# public_entrypoints:
#   - docker build -f apps/api/Dockerfile .
# semantic_blocks:
#   - API_IMAGE: shared-first Python image build and runtime command.
# owned_tests:
#   - docker proof build/import smoke in Stage A2
# END_MODULE_MAP: M-DEPLOY-API-DOCKERFILE

# START_BLOCK: API_IMAGE
# Base image pinned by multi-arch index digest (source tag python:3.12-slim,
# version 3.12.13-slim-trixie; verified via docker buildx imagetools inspect
# on 2026-07-19).
FROM python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de

WORKDIR /app

RUN python -m pip install --no-cache-dir --upgrade pip

COPY packages/py-contracts /tmp/solarsage-py-contracts
RUN python -m pip install --no-cache-dir /tmp/solarsage-py-contracts

COPY apps/api /app
RUN python -m pip install --no-cache-dir . \
    && python -m pip check \
    && rm -rf /app/app /app/astro_api.egg-info
COPY grace/canon /usr/local/lib/grace/canon

ARG RELEASE_SHA=unknown
ENV RELEASE_SHA=${RELEASE_SHA}
LABEL org.opencontainers.image.revision="${RELEASE_SHA}"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# END_BLOCK: API_IMAGE
