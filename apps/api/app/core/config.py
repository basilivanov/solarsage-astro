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
#     CONTRACT_VERSION, CORS_ALLOWED_ORIGINS, GRACE_USER_SALT and P5 day-pregen
#     settings) read via pydantic-settings
#   - .env file at repo root
#   - `git rev-parse --short HEAD` for git_sha resolution
# outputs:
#   - settings: Settings singleton imported by other modules
#   - settings.day_pregen_*: positive typed nightly pre-generation limits
#   - settings.git_sha: short HEAD sha or "unknown"
#   - settings.cors_allowed_origins: comma-separated exact origins
#   - settings.grace_user_salt: salt for logging privacy
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
#   - apps/api/tests/test_today_pregen_service.py (P5 setting validation)
# END_MODULE_MAP: M-CONFIG

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[4]


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

    # Immutable release identity supplied by the OCI image/container environment
    # (full 40-hex commit SHA). "unknown" outside the canonical app stack.
    release_sha: str = Field("unknown", alias="RELEASE_SHA")

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
    # Canonical bot username used for public t.me links (referral inviteUrl,
    # share fallback). Public, non-secret; production must be AstroGrace_Bot.
    bot_username: str = Field("AstroGrace_Bot", alias="BOT_USERNAME")
    # Secret token Telegram sends in X-Telegram-Bot-Api-Secret-Token on each
    # webhook call. Empty means the webhook endpoint rejects every request
    # (fail-closed); set via TELEGRAM_WEBHOOK_SECRET in production only.
    telegram_webhook_secret: str = Field("", alias="TELEGRAM_WEBHOOK_SECRET")
    # Hard ceiling on initData age. Telegram recommends rejecting payloads
    # older than 24h; we default to 24h per W-1.2 ## Decision.
    telegram_auth_max_age_seconds: int = Field(
        86400, alias="INITDATA_MAX_AGE_SECONDS"
    )

    # --- Server-side session (W-1.2 Option A: opaque cookie + sessions) ---
    session_cookie_name: str = Field("grace_session_v2", alias="SESSION_COOKIE_NAME")
    session_ttl_seconds: int = Field(
        60 * 60 * 24 * 30, alias="SESSION_TTL_SECONDS"
    )  # 30d
    session_cookie_secure: bool = Field(True, alias="SESSION_COOKIE_SECURE")

    # --- SolarSage sidecar (W-3.4) ---
    solarsage_url: str = Field("http://127.0.0.1:18091", alias="SOLARSAGE_URL")

    # --- LLM (W-5.1) ---
    # Provider: "anthropic" | "openrouter"
    llm_provider: str = Field("openrouter", alias="LLM_PROVIDER")

    # API Keys
    anthropic_api_key: str = Field("", alias="ANTHROPIC_API_KEY")
    openrouter_api_key: str = Field("", alias="OPENROUTER_API_KEY")

    # Model configuration
    llm_model: str = Field("openai/gpt-4.1-nano", alias="LLM_MODEL")
    llm_fallback_model: str = Field(
        "google/gemma-4-31b-it", alias="LLM_FALLBACK_MODEL"
    )
    llm_max_tokens: int = Field(500, alias="LLM_MAX_TOKENS")

    # --- Today bounded narrative (P6) ---
    today_narrative_model_pregen: str = Field(
        "deepseek/deepseek-v4-flash", alias="TODAY_NARRATIVE_MODEL_PREGEN"
    )
    today_narrative_model_ondemand: str = Field(
        "openai/gpt-4.1-nano", alias="TODAY_NARRATIVE_MODEL_ONDEMAND"
    )
    today_narrative_fallback_models: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["google/gemma-4-31b-it"],
        alias="TODAY_NARRATIVE_FALLBACK_MODELS",
    )
    today_narrative_pregen_max_output_tokens: int = Field(
        3000, gt=0, alias="TODAY_NARRATIVE_PREGEN_MAX_OUTPUT_TOKENS"
    )
    today_narrative_max_output_tokens: int = Field(
        2000, alias="TODAY_NARRATIVE_MAX_OUTPUT_TOKENS"
    )
    today_narrative_timeout_seconds: int = Field(
        45, alias="TODAY_NARRATIVE_TIMEOUT_SECONDS"
    )
    today_narrative_prompt_version: str = Field(
        "today-narrative-v6", alias="TODAY_NARRATIVE_PROMPT_VERSION"
    )
    today_sphere_natal_prompt_version: str = Field(
        "sphere-natal-v1", alias="TODAY_SPHERE_NATAL_PROMPT_VERSION"
    )
    today_llm_on_demand_concurrency: int = Field(
        3, alias="TODAY_LLM_ON_DEMAND_CONCURRENCY"
    )

    @field_validator("today_narrative_fallback_models", mode="before")
    @classmethod
    def _parse_today_narrative_fallback_models(cls, value: object) -> list[str]:
        # START_FUNCTION_CONTRACT: F-M-CONFIG._parse_today_narrative_fallback_models
        # purpose: Parse the ordered comma-separated Today narrative fallback model list.
        # inputs: value — environment string or an already typed list/tuple.
        # returns: model identifiers in configured order; an explicit None yields an empty list.
        # side_effects: none.
        # error_behavior: raises ValueError for unsupported input shapes.
        # END_FUNCTION_CONTRACT: F-M-CONFIG._parse_today_narrative_fallback_models
        # The runtime contract is a comma-separated env value while the
        # application consumes a typed ordered model list.
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, (list, tuple)):
            return [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if value is None:
            return []
        raise ValueError("TODAY_NARRATIVE_FALLBACK_MODELS must be comma-separated")

    # --- Nightly Today convergence pre-generation (P5) ---
    # All values are positive by contract so the one-shot job fails closed
    # before it queries the cohort when an environment is misconfigured.
    day_pregen_active_days: int = Field(14, gt=0, alias="DAY_PREGEN_ACTIVE_DAYS")
    day_pregen_llm_active_days: int = Field(
        7, gt=0, alias="DAY_PREGEN_LLM_ACTIVE_DAYS"
    )
    day_pregen_concurrency: int = Field(3, gt=0, alias="DAY_PREGEN_CONCURRENCY")
    day_pregen_max_users: int = Field(500, gt=0, alias="DAY_PREGEN_MAX_USERS")
    day_pregen_deterministic_deadline_seconds: int = Field(
        10, gt=0, alias="DAY_PREGEN_DETERMINISTIC_DEADLINE_SECONDS"
    )
    day_pregen_llm_deadline_seconds: int = Field(
        45, gt=0, alias="DAY_PREGEN_LLM_DEADLINE_SECONDS"
    )

    # OpenRouter specific settings
    openrouter_base_url: str = Field(
        "https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL"
    )
    openrouter_app_name: str = Field("solarsage-astro", alias="OPENROUTER_APP_NAME")
    openrouter_site_url: str = Field("", alias="OPENROUTER_SITE_URL")

    # --- Dev mode (W-2.2) ---
    # When true, enables /api/auth/dev endpoint for local development without Telegram
    dev_mode: bool = Field(False, alias="DEV_MODE")

    # --- Security Hardening ---
    cors_allowed_origins: str = Field("", alias="CORS_ALLOWED_ORIGINS")
    grace_user_salt: str = Field("", alias="GRACE_USER_SALT")

    # --- Feature flags ---
    # W-NATAL-FULL Wave 4: natal full report generation endpoints.
    # Disabled by default; enable when LLM prompts are validated and tested.
    natal_report_enabled: bool = Field(False, alias="NATAL_REPORT_ENABLED")

    # --- V2 scoring feature flags (W5) ---
    solarsage_v2_enabled: bool = Field(False, alias="SOLARSAGE_V2_ENABLED")
    solarsage_v2_dual_run: bool = Field(True, alias="SOLARSAGE_V2_DUAL_RUN")
    solarsage_v2_frontend_enabled: bool = Field(False, alias="SOLARSAGE_V2_FRONTEND_ENABLED")
    solarsage_audit_artifacts_enabled: bool = Field(False, alias="SOLARSAGE_AUDIT_ARTIFACTS_ENABLED")

    # --- Feedback broadcast feature flag ---
    feedback_broadcast_enabled: bool = Field(False, alias="FEEDBACK_BROADCAST_ENABLED")
    feedback_broadcast_hours: str = Field("20", alias="FEEDBACK_BROADCAST_HOURS")

    # --- YooKassa (secrets live only in env files, never in git) ---
    yookassa_enabled: bool = Field(False, alias="YOOKASSA_ENABLED")
    yookassa_mode: str = Field("test", alias="YOOKASSA_MODE")  # "test" | "live"
    yookassa_test_shop_id: str = Field("", alias="YOOKASSA_TEST_SHOP_ID")
    yookassa_test_secret_key: str = Field("", alias="YOOKASSA_TEST_SECRET_KEY")
    yookassa_live_shop_id: str = Field("", alias="YOOKASSA_LIVE_SHOP_ID")
    yookassa_live_secret_key: str = Field("", alias="YOOKASSA_LIVE_SECRET_KEY")
    yookassa_return_url: str = Field("", alias="YOOKASSA_RETURN_URL")
    yookassa_recurrent_enabled: bool = Field(False, alias="YOOKASSA_RECURRENT_ENABLED")
    # W2-VALENCE: server-only flags (shadow first; selection via Release B)
    today_valence_v1_enabled: bool = Field(False, alias="TODAY_VALENCE_V1_ENABLED")
    today_valence_v1_dual_run: bool = Field(False, alias="TODAY_VALENCE_V1_DUAL_RUN")

    # Comma-separated CIDR allowlist override for the webhook source check
    # (tests/dev only; production default = official YooKassa ranges).
    yookassa_webhook_ip_allowlist: str = Field("", alias="YOOKASSA_WEBHOOK_IP_ALLOWLIST")
    # Comma-separated CIDRs of TRUSTED proxies (our own nginx) whose
    # X-Real-IP / X-Forwarded-For headers may be believed for the webhook
    # source check. Default loopback only; anything else fails closed.
    yookassa_trusted_proxy_cidrs: str = Field(
        "127.0.0.1/32,::1/128", alias="YOOKASSA_TRUSTED_PROXY_CIDRS"
    )

    @property
    def yookassa_shop_id(self) -> str:
        return self.yookassa_live_shop_id if self.yookassa_mode == "live" else self.yookassa_test_shop_id

    @property
    def yookassa_secret_key(self) -> str:
        return self.yookassa_live_secret_key if self.yookassa_mode == "live" else self.yookassa_test_secret_key

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
