
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


class Settings(BaseSettings):
    """Sidecar configuration."""

    # Server
    host: str = "127.0.0.1"
    port: int = 18091

    # Ephemeris
    ephemeris_path: str = "/opt/sweph/ephe"

    # Versioning
    calculation_version: str = "ss-1.0.0"
    git_sha: str = "dev"  # Override in production

    model_config = SettingsConfigDict(
        env_prefix="SOLARSAGE_",
        case_sensitive=False,
    )


settings = Settings()
