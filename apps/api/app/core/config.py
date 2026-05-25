# ############################################################################
# AI_HEADER: MODULE_CONFIG
# ROLE: Single source of truth for runtime configuration consumed by every module.
# DEPENDENCIES: pydantic, pydantic-settings, subprocess
# GRACE_ANCHORS: [GIT_SHA_RESOLUTION, SETTINGS_DECLARATION, SETTINGS_SINGLETON]
# ############################################################################

# START_MODULE_CONTRACT: M-CONFIG
# purpose: Single source of truth for runtime configuration (env, version,
#   domain, database URL, contract version) consumed by every module.
# owns:
#   - apps/api/app/core/config.py
#   - apps/api/app/core/__init__.py
# inputs:
#   - environment variables (APP_ENV, APP_DOMAIN, APP_VERSION, DATABASE_URL,
#     CONTRACT_VERSION) read via pydantic-settings
#   - .env file at repo root
#   - `git rev-parse --short HEAD` for git_sha resolution
# outputs:
#   - settings: Settings singleton imported by other modules
#   - settings.git_sha: short HEAD sha or "unknown"
# dependencies:
#   - pydantic, pydantic-settings
#   - subprocess (for git sha)
# side_effects:
#   - spawns `git rev-parse` once per access of git_sha (acceptable in W-1.1;
#     cached resolution is deferred work)
# invariants:
#   - never raises on missing env vars: every Field has a safe default
#   - APP_VERSION is the canonical version string surfaced via /api/health
#   - git_sha is always a string ("unknown" if git is absent or fails)
# failure_policy:
#   - git failures swallowed and replaced with "unknown"
#   - any other validation error from pydantic-settings is intentional and
#     must crash the process at import time
# non_goals:
#   - no feature flags
#   - no per-request config
#   - no telegram / solarsage / llm settings (deferred)
# END_MODULE_CONTRACT: M-CONFIG

# START_MODULE_MAP: M-CONFIG
# public_entrypoints:
#   - Settings
#   - settings
# semantic_blocks:
#   - GIT_SHA_RESOLUTION: subprocess call to `git rev-parse --short HEAD`
#   - SETTINGS_DECLARATION: Settings(BaseSettings) field declarations
#   - SETTINGS_SINGLETON: module-level `settings = Settings()` instance
# owned_tests:
#   - apps/api/tests/test_health.py (indirectly, via /api/health response)
# END_MODULE_MAP: M-CONFIG

from __future__ import annotations

import subprocess
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _resolve_git_sha() -> str:
    # START_FUNCTION_CONTRACT: M-CONFIG._resolve_git_sha
    # purpose: Return a stable build identifier surfaced via /api/health.
    # inputs: none (reads working directory _REPO_ROOT)
    # returns: short sha string, or literal "unknown" if git is unavailable
    # side_effects: spawns a subprocess (`git rev-parse --short HEAD`)
    # emitted_logs: none
    # error_behavior: catches FileNotFoundError and SubprocessError; never
    #   raises out of this function
    # END_FUNCTION_CONTRACT: M-CONFIG._resolve_git_sha

    # START_BLOCK: GIT_SHA_RESOLUTION
    env_sha: str | None = None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0:
            env_sha = result.stdout.strip()
    except (FileNotFoundError, subprocess.SubprocessError):
        env_sha = None
    return env_sha or "unknown"
    # END_BLOCK: GIT_SHA_RESOLUTION


# START_BLOCK: SETTINGS_DECLARATION
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = Field("dev", alias="APP_ENV")
    app_domain: str = Field("localhost", alias="APP_DOMAIN")
    app_version: str = Field("0.1.0", alias="APP_VERSION")

    # SQLite by default so `alembic upgrade head` works on a fresh checkout
    # without external services. Postgres URL is supplied via .env in real envs.
    database_url: str = Field(
        "sqlite+aiosqlite:///./astro_dev.db",
        alias="DATABASE_URL",
    )

    contract_version: int = Field(1, alias="CONTRACT_VERSION")

    # --- Telegram WebApp auth (W-1.2) ---
    # Bot token used as the HMAC secret seed per Telegram WebApp spec:
    # secret_key = HMAC_SHA256(key="WebAppData", msg=bot_token)
    # Empty string is the safe default for local dev / unit tests; the
    # service layer treats empty as "auth disabled" only inside `app_env=dev`
    # and refuses to verify in any other environment (see telegram_auth).
    telegram_bot_token: str = Field("", alias="TELEGRAM_BOT_TOKEN")
    # Hard ceiling on initData age. Telegram recommends rejecting payloads
    # older than 24h; we default to 24h per W-1.2 ## Decision.
    telegram_auth_max_age_seconds: int = Field(
        86400, alias="INITDATA_MAX_AGE_SECONDS"
    )

    # --- Server-side session (W-1.2 Option A: opaque cookie + sessions) ---
    session_cookie_name: str = Field("grace_session", alias="SESSION_COOKIE_NAME")
    session_ttl_seconds: int = Field(
        60 * 60 * 24 * 30, alias="SESSION_TTL_SECONDS"
    )  # 30d
    session_cookie_secure: bool = Field(True, alias="SESSION_COOKIE_SECURE")

    @property
    def git_sha(self) -> str:
        # START_FUNCTION_CONTRACT: M-CONFIG.Settings.git_sha
        # purpose: Expose the resolved short git sha as an attribute on the
        #   settings singleton so other modules (notably /api/health) do not
        #   need to know about subprocess plumbing.
        # inputs: self (Settings instance); no external arguments
        # returns: short sha string, or literal "unknown" if git is unavailable
        # side_effects: delegates to _resolve_git_sha, which spawns a
        #   subprocess on each access (no caching by design in W-1.1)
        # emitted_logs: none
        # error_behavior: never raises; _resolve_git_sha swallows git failures
        # END_FUNCTION_CONTRACT: M-CONFIG.Settings.git_sha
        return _resolve_git_sha()
# END_BLOCK: SETTINGS_DECLARATION

# START_BLOCK: SETTINGS_SINGLETON
settings = Settings()
# END_BLOCK: SETTINGS_SINGLETON
