# ############################################################################
# AI_HEADER: MODULE_RUNTIME_SECURITY — runtime security policy builder
# ROLE: Handles environment normalization, CORS origins parsing, internal routes
#       toggling, and fail-closed deployed settings validation.
# ############################################################################

# START_MODULE_CONTRACT: M-RUNTIME-SECURITY
# purpose: Normalizes APP_ENV, validates security settings, and determines CORS
#   origins and internal route availability.
# owns:
#   - apps/api/app/core/runtime_security.py
# inputs:
#   - Settings object containing app_env, app_domain, dev_mode, etc.
# outputs:
#   - RuntimeSecurityPolicy dataclass
# dependencies:
#   - dataclasses, typing, urllib.parse, ipaddress
#   - apps.api.app.core.config.Settings
# side_effects: none
# emitted_logs: none
# invariants:
#   - Any invalid or empty raw APP_ENV throws ValueError.
#   - deployed is True only for staging and production.
#   - In deployed environments, invalid settings crash startup (ValueError).
#   - Deployed billing contract: YOOKASSA_MODE exactly test|live; enabled
#     billing requires non-empty mode credentials + HTTPS return URL;
#     NATAL_REPORT_ENABLED requires YOOKASSA_ENABLED; production billing pins
#     webhook allowlist to official ranges (no override) and the trusted
#     proxy to exactly 172.31.235.1/32; recurrent requires the master switch.
# failure_policy:
#   - Throws ValueError on validation failure (never with secret values).
# END_MODULE_CONTRACT: M-RUNTIME-SECURITY

# START_MODULE_MAP: M-RUNTIME-SECURITY
# public_entrypoints:
#   - RuntimeSecurityPolicy
#   - build_runtime_security_policy
# semantic_blocks:
#   - POLICY_DECLARATION: RuntimeSecurityPolicy dataclass definition
#   - POLICY_BUILDER: build_runtime_security_policy implementation
# owned_tests:
#   - apps/api/tests/test_runtime_security_policy.py
# END_MODULE_MAP: M-RUNTIME-SECURITY

import ipaddress
import urllib.parse
from dataclasses import dataclass
from typing import Literal

from app.core.config import Settings

# START_BLOCK: POLICY_DECLARATION
@dataclass(frozen=True)
class RuntimeSecurityPolicy:
    environment: Literal["development", "test", "staging", "production"]
    deployed: bool
    cors_allowed_origins: tuple[str, ...]
    internal_routes_enabled: bool
# END_BLOCK: POLICY_DECLARATION


# START_BLOCK: POLICY_BUILDER
def build_runtime_security_policy(settings: Settings) -> RuntimeSecurityPolicy:
    # START_FUNCTION_CONTRACT: F-M-RUNTIME-SECURITY.build_runtime_security_policy
    # purpose: Parse, validate and build a strict runtime security policy.
    # inputs: settings — Settings instance.
    # returns: RuntimeSecurityPolicy — the validated immutable policy.
    # side_effects: none
    # emitted_logs: none
    # error_behavior: Throws ValueError on any security-critical policy violation.
    # END_FUNCTION_CONTRACT: F-M-RUNTIME-SECURITY.build_runtime_security_policy

    # 1. Normalize APP_ENV
    raw_env = settings.app_env
    if raw_env is None:
        raw_env = "development"

    if not isinstance(raw_env, str):
        raise ValueError("APP_ENV:invalid")

    trimmed_env = raw_env.strip()
    if trimmed_env == "":
        raise ValueError("APP_ENV:empty")

    trimmed_env_lower = trimmed_env.lower()

    if trimmed_env_lower in ("dev", "development"):
        canonical_env: Literal["development", "test", "staging", "production"] = "development"
    elif trimmed_env_lower == "test":
        canonical_env = "test"
    elif trimmed_env_lower in ("stage", "staging", "preview"):
        canonical_env = "staging"
    elif trimmed_env_lower in ("prod", "production"):
        canonical_env = "production"
    else:
        raise ValueError("APP_ENV:invalid")

    deployed = canonical_env in ("staging", "production")

    # 2. Parse and validate CORS origins
    raw_origins = settings.cors_allowed_origins
    parsed_origins: list[str] = []

    if raw_origins:
        # Split by comma
        for orig in raw_origins.split(","):
            orig = orig.strip()
            if not orig:
                continue

            # Check for trailing slash and strip if present
            if orig.endswith("/") and len(orig) > 8: # keep scheme intact
                orig = orig.rstrip("/")

            parsed_origins.append(orig)

    # Remove duplicates preserving deterministic order
    seen = set()
    deduped_origins = []
    for orig in parsed_origins:
        if orig not in seen:
            seen.add(orig)
            deduped_origins.append(orig)

    # Check for wildcards
    for idx, orig in enumerate(deduped_origins):
        if "*" in orig:
            raise ValueError(f"origin[{idx}]:wildcard-forbidden")

    # Validate each origin is scheme://host[:port]
    for idx, orig in enumerate(deduped_origins):
        parsed = urllib.parse.urlparse(orig)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"origin[{idx}]:missing-scheme-or-netloc")
        if parsed.path or parsed.query or parsed.params or parsed.fragment:
            raise ValueError(f"origin[{idx}]:path-query-fragment-forbidden")
        if "@" in parsed.netloc:
            raise ValueError(f"origin[{idx}]:userinfo-forbidden")
        # Wildcard host check
        if parsed.hostname and (parsed.hostname.startswith("*") or parsed.hostname.endswith("*")):
            raise ValueError(f"origin[{idx}]:wildcard-hostname-forbidden")
        # Trailing slash is already stripped, but netloc shouldn't have trailing characters
        if orig.endswith("/"):
            raise ValueError(f"origin[{idx}]:trailing-slash-forbidden")

        # Access parsed.port explicitly to catch malformed port issues (throws ValueError if port is invalid)
        try:
            _ = parsed.port
        except ValueError as e:
            raise ValueError(f"origin[{idx}]:invalid-port") from e

    # 3. Deployed validations
    domain = settings.app_domain.strip() if settings.app_domain else ""
    if deployed:
        if not domain:
            raise ValueError("APP_DOMAIN:empty-deployed")

        # Check if domain is localhost, loopback, contains scheme/path, or wildcard
        if domain.lower() in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("APP_DOMAIN:loopback-deployed")

        # Check for scheme/path/wildcard in APP_DOMAIN
        if "://" in domain or "/" in domain or "*" in domain:
            raise ValueError("APP_DOMAIN:invalid-format")

        # Precise loopback check
        try:
            parsed_ip = ipaddress.ip_address(domain)
        except ValueError:
            parsed_ip = None
        if parsed_ip is not None and parsed_ip.is_loopback:
            raise ValueError("APP_DOMAIN:loopback-deployed")

        # CORS origins in deployed environment
        if not deduped_origins:
            raise ValueError("CORS_ALLOWED_ORIGINS:empty-deployed")

        # Must only be https, and no localhost/loopback origins in deployed env
        for idx, orig in enumerate(deduped_origins):
            parsed = urllib.parse.urlparse(orig)
            if parsed.scheme != "https":
                raise ValueError(f"origin[{idx}]:http-forbidden-deployed")

            # Check for loopback/localhost in CORS origin hostname
            hostname = parsed.hostname or ""
            if hostname.lower() in ("localhost", "127.0.0.1", "::1"):
                raise ValueError(f"origin[{idx}]:loopback-forbidden-deployed")
            try:
                parsed_host_ip = ipaddress.ip_address(hostname)
            except ValueError:
                parsed_host_ip = None
            if parsed_host_ip is not None and parsed_host_ip.is_loopback:
                raise ValueError(f"origin[{idx}]:loopback-forbidden-deployed")

        # Must contain https://{APP_DOMAIN}
        expected_origin = f"https://{domain}"
        if expected_origin not in deduped_origins:
            raise ValueError("CORS_ALLOWED_ORIGINS:own-origin-missing")

        # DEV_MODE must be false
        if settings.dev_mode:
            raise ValueError("DEV_MODE:true-deployed")

        # SESSION_COOKIE_SECURE must be true
        if not settings.session_cookie_secure:
            raise ValueError("SESSION_COOKIE_SECURE:false-deployed")

        # TELEGRAM_BOT_TOKEN must not be empty
        if not settings.telegram_bot_token.strip():
            raise ValueError("TELEGRAM_BOT_TOKEN:empty-deployed")

        # GRACE_USER_SALT must be at least 32 characters
        if len(settings.grace_user_salt) < 32:
            raise ValueError("GRACE_USER_SALT:too-short-deployed")

        # DATABASE_URL must not be SQLite
        db_url = settings.database_url.lower()
        if "sqlite" in db_url:
            raise ValueError("DATABASE_URL:sqlite-deployed")

        # START_BLOCK: BILLING_POLICY
        # Billing (YooKassa) fail-closed runtime contract. Error codes NEVER
        # carry secret values.
        # Mode is exactly test|live — no silent fallback.
        if settings.yookassa_mode not in ("test", "live"):
            raise ValueError("YOOKASSA_MODE:invalid-deployed")
        if settings.yookassa_enabled:
            # Chosen mode credentials must be present and the return URL a
            # valid HTTPS URL. (Billing OFF keeps empty values valid.)
            if not settings.yookassa_shop_id.strip():
                raise ValueError("YOOKASSA_SHOP_ID:empty-billing")
            if not settings.yookassa_secret_key.strip():
                raise ValueError("YOOKASSA_SECRET_KEY:empty-billing")
            return_url = settings.yookassa_return_url.strip()
            parsed_return = urllib.parse.urlparse(return_url)
            if parsed_return.scheme != "https" or not parsed_return.netloc:
                raise ValueError("YOOKASSA_RETURN_URL:invalid-billing")
        # The natal full report is sold only through billing: the feature
        # flag requires the master switch in deployed env.
        if settings.natal_report_enabled and not settings.yookassa_enabled:
            raise ValueError("NATAL_REPORT_ENABLED:requires-billing")
        if canonical_env == "production" and settings.yookassa_enabled:
            # Webhook source policy is pinned in production: official
            # YooKassa ranges only (no override) and exactly the canonical
            # trusted proxy gateway /32.
            if settings.yookassa_webhook_ip_allowlist.strip():
                raise ValueError("YOOKASSA_WEBHOOK_IP_ALLOWLIST:nonempty-production")
            try:
                proxy_nets = {
                    ipaddress.ip_network(c.strip(), strict=False)
                    for c in settings.yookassa_trusted_proxy_cidrs.split(",")
                    if c.strip()
                }
            except ValueError as exc:
                raise ValueError("YOOKASSA_TRUSTED_PROXY_CIDRS:invalid") from exc
            if proxy_nets != {ipaddress.ip_network("172.31.235.1/32")}:
                raise ValueError("YOOKASSA_TRUSTED_PROXY_CIDRS:non-canonical-production")
        # END_BLOCK: BILLING_POLICY
    else:
        # Development environment domain restriction:
        # Development mode is only allowed on localhost/loopback domain. Public development is forbidden.
        if canonical_env == "development":
            is_local_domain = domain.lower() in ("localhost", "127.0.0.1", "::1")
            if not is_local_domain:
                try:
                    parsed_ip = ipaddress.ip_address(domain)
                    is_local_domain = parsed_ip.is_loopback
                except ValueError:
                    is_local_domain = False
            if not is_local_domain:
                raise ValueError("Public development deployment is forbidden. APP_DOMAIN must be localhost/loopback in development.")

    # Local development default origins
    if not deployed and canonical_env != "test" and not deduped_origins:
        deduped_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3002",
            "http://127.0.0.1:3002",
            "http://localhost:3003",
            "http://127.0.0.1:3003",
        ]

    # Recurrent charging is a child of the master switch, in ANY env:
    # recurrent=true without billing enabled is an invalid runtime config.
    if settings.yookassa_recurrent_enabled and not settings.yookassa_enabled:
        raise ValueError("YOOKASSA_RECURRENT:without-master")

    # 4. Internal routes policy
    # internal_routes_enabled = True only when:
    # canonical environment == development AND DEV_MODE == true AND APP_DOMAIN is localhost/127.0.0.1/::1
    is_local_domain = domain.lower() in ("localhost", "127.0.0.1", "::1")
    if not is_local_domain:
        try:
            parsed_ip = ipaddress.ip_address(domain)
            is_local_domain = parsed_ip.is_loopback
        except ValueError:
            is_local_domain = False

    internal_routes_enabled = (
        canonical_env == "development"
        and settings.dev_mode
        and is_local_domain
    )

    return RuntimeSecurityPolicy(
        environment=canonical_env,
        deployed=deployed,
        cors_allowed_origins=tuple(deduped_origins),
        internal_routes_enabled=internal_routes_enabled,
    )
# END_BLOCK: POLICY_BUILDER
