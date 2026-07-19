
# ############################################################################
# AI_HEADER: MODULE_CORE_CONFIG
# ROLE: Sidecar calculation
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ######################################### START_MODULE_CONTRACT
# purpose: Module: config.py
# owns:
#   - apps/solarsage/solarsage/core/config.py
# inputs: Function args
# outputs: Return values
# dependencies: local modules
# side_effects: n/a (pure)
# emitted_logs: n/a (pure)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
# AI_HEADER
# module: M-SIDECAR-CONFIG
# wave: W-3.1
# purpose: Sidecar settings (ephemeris path, port, calculation version)

from pydantic_settings import BaseSettings, SettingsConfigDict

from solarsage_contracts.versions import CALCULATION_VERSION


class Settings(BaseSettings):
    """Sidecar configuration."""

    # Server
    host: str = "127.0.0.1"
    port: int = 18091

    # Ephemeris
    # Canonical pinned artifact root (per doc 80 layout: <root>/{ephe,manifest.json,manifest.sha256}).
    ephemeris_root: str = "/opt/solarsage-ephemeris/current"
    # Legacy data dir used ONLY by the explicit non-production moshier mode.
    ephemeris_path: str = "/opt/sweph/ephe"
    # Explicit test-only switch: accept Moshier instead of the pinned Swiss
    # artifact. NEVER honored under app_env=production (fail-closed).
    ephemeris_allow_moshier: bool = False
    app_env: str = "development"

    # Versioning — default is the shared canonical contract version; env may
    # only override in non-production tooling.
    calculation_version: str = CALCULATION_VERSION
    git_sha: str = "dev"  # Override in production
    # Immutable release identity supplied by the container environment
    # (SOLARSAGE_RELEASE_SHA, full 40-hex commit SHA). "unknown" outside the
    # canonical app stack.
    release_sha: str = "unknown"

    model_config = SettingsConfigDict(
        env_prefix="SOLARSAGE_",
        case_sensitive=False,
    )


settings = Settings()
