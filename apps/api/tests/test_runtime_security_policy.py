# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_RUNTIME_SECURITY_POLICY — Unit tests for build_runtime_security_policy
# ROLE: Unit tests for build_runtime_security_policy validations.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-RUNTIME-SECURITY-POLICY
# purpose: Verify APP_ENV normalization, CORS validations, fail-closed behavior, and loopback checks.
# owns:
#   - apps/api/tests/test_runtime_security_policy.py
# inputs: none
# outputs: test assertions
# dependencies:
#   - pytest, app.core.config.Settings, app.core.runtime_security
# side_effects: none
# invariants: none
# failure_policy: raise on failure
# END_MODULE_CONTRACT: M-TEST-RUNTIME-SECURITY-POLICY

# START_MODULE_MAP: M-TEST-RUNTIME-SECURITY-POLICY
# public_entrypoints:
#   - test_app_env_normalization
#   - test_cors_allowed_origins_validation
#   - test_deployed_fail_closed_validations
#   - test_internal_routes_policy
#   - test_loopback_rejection
#   - test_canary_safe_exceptions
# semantic_blocks: none
# owned_tests:
#   - apps/api/tests/test_runtime_security_policy.py
# END_MODULE_MAP: M-TEST-RUNTIME-SECURITY-POLICY

import pytest
from app.core.config import Settings
from app.core.runtime_security import build_runtime_security_policy

def test_app_env_normalization():
    # START_FUNCTION_CONTRACT: F-M-TEST-RUNTIME-SECURITY-POLICY.test_app_env_normalization
    # purpose: Verify normalization of various APP_ENV strings.
    # inputs: none
    # returns: none
    # side_effects: none
    # emitted_logs: none
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-RUNTIME-SECURITY-POLICY.test_app_env_normalization
    # Valid aliases
    for raw, expected in [
        ("dev", "development"),
        ("development", "development"),
        ("DEV", "development"),
        ("test", "test"),
        ("stage", "staging"),
        ("staging", "staging"),
        ("preview", "staging"),
        ("prod", "production"),
        ("production", "production"),
    ]:
        s = Settings(
            _env_file=None,
            APP_ENV=raw,
            APP_DOMAIN="localhost" if raw in ("dev", "development", "DEV") else "dev.astro.vasiliy-ivanov.ru",
            CORS_ALLOWED_ORIGINS="https://dev.astro.vasiliy-ivanov.ru" if raw in ("stage", "staging", "preview", "prod", "production") else "",
            DEV_MODE=False,
            SESSION_COOKIE_SECURE=True,
            TELEGRAM_BOT_TOKEN="real_token_here",
            GRACE_USER_SALT="a" * 32,
            DATABASE_URL="postgresql+asyncpg://astro:astro@127.0.0.1:5432/astro",
        )
        policy = build_runtime_security_policy(s)
        assert policy.environment == expected

    # Unknown APP_ENV fails
    with pytest.raises(ValueError, match="APP_ENV:invalid"):
        build_runtime_security_policy(Settings(_env_file=None, APP_ENV="unknown"))

    # Explicit empty env fails
    with pytest.raises(ValueError, match="APP_ENV:empty"):
        build_runtime_security_policy(Settings(_env_file=None, APP_ENV=""))
    with pytest.raises(ValueError, match="APP_ENV:empty"):
        build_runtime_security_policy(Settings(_env_file=None, APP_ENV="   "))


def test_cors_allowed_origins_validation():
    # START_FUNCTION_CONTRACT: F-M-TEST-RUNTIME-SECURITY-POLICY.test_cors_allowed_origins_validation
    # purpose: Verify validation rules for CORS allowed origins.
    # inputs: none
    # returns: none
    # side_effects: none
    # emitted_logs: none
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-RUNTIME-SECURITY-POLICY.test_cors_allowed_origins_validation
    # Empty in dev has defaults
    s = Settings(_env_file=None, APP_ENV="dev", CORS_ALLOWED_ORIGINS="", APP_DOMAIN="localhost")
    policy = build_runtime_security_policy(s)
    assert len(policy.cors_allowed_origins) == 6
    assert "http://localhost:3000" in policy.cors_allowed_origins

    # Duplicate removal
    s = Settings(_env_file=None, APP_ENV="dev", CORS_ALLOWED_ORIGINS="http://localhost:3000,http://localhost:3000", APP_DOMAIN="localhost")
    policy = build_runtime_security_policy(s)
    assert policy.cors_allowed_origins == ("http://localhost:3000",)

    # Trailing slash removal
    s = Settings(_env_file=None, APP_ENV="dev", CORS_ALLOWED_ORIGINS="http://localhost:3000/", APP_DOMAIN="localhost")
    policy = build_runtime_security_policy(s)
    assert policy.cors_allowed_origins == ("http://localhost:3000",)

    # Wildcard rejected
    with pytest.raises(ValueError, match="wildcard-forbidden"):
        build_runtime_security_policy(Settings(_env_file=None, APP_ENV="dev", CORS_ALLOWED_ORIGINS="*"))
    with pytest.raises(ValueError, match="wildcard-forbidden"):
        build_runtime_security_policy(Settings(_env_file=None, APP_ENV="dev", CORS_ALLOWED_ORIGINS="https://*.example.com"))

    # Invalid URL structures
    with pytest.raises(ValueError, match="path-query-fragment-forbidden"):
        build_runtime_security_policy(Settings(_env_file=None, APP_ENV="dev", CORS_ALLOWED_ORIGINS="http://localhost:3000/path"))
    with pytest.raises(ValueError, match="missing-scheme-or-netloc"):
        build_runtime_security_policy(Settings(_env_file=None, APP_ENV="dev", CORS_ALLOWED_ORIGINS="user:pass@host"))
    with pytest.raises(ValueError, match="invalid-port"):
        build_runtime_security_policy(Settings(_env_file=None, APP_ENV="dev", CORS_ALLOWED_ORIGINS="http://localhost:invalidport"))


def test_deployed_fail_closed_validations():
    # START_FUNCTION_CONTRACT: F-M-TEST-RUNTIME-SECURITY-POLICY.test_deployed_fail_closed_validations
    # purpose: Verify that missing or invalid settings cause ValueError in staging/production.
    # inputs: none
    # returns: none
    # side_effects: none
    # emitted_logs: none
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-RUNTIME-SECURITY-POLICY.test_deployed_fail_closed_validations
    # Deployed staging/production requires HTTPS origins, exact APP_DOMAIN origin, etc.
    base_settings_dict = {
        "_env_file": None,
        "APP_ENV": "staging",
        "APP_DOMAIN": "dev.astro.vasiliy-ivanov.ru",
        "CORS_ALLOWED_ORIGINS": "https://dev.astro.vasiliy-ivanov.ru",
        "DEV_MODE": False,
        "SESSION_COOKIE_SECURE": True,
        "TELEGRAM_BOT_TOKEN": "some_token_here",
        "GRACE_USER_SALT": "a" * 32,
        "DATABASE_URL": "postgresql+asyncpg://astro:astro@127.0.0.1:5432/astro",
    }

    # Staging accepted
    s = Settings(**base_settings_dict)
    policy = build_runtime_security_policy(s)
    assert policy.deployed is True
    assert policy.environment == "staging"

    # Production accepted
    prod_dict = base_settings_dict.copy()
    prod_dict["APP_ENV"] = "production"
    s = Settings(**prod_dict)
    policy = build_runtime_security_policy(s)
    assert policy.deployed is True
    assert policy.environment == "production"

    # Fail: empty APP_DOMAIN
    bad = base_settings_dict.copy()
    bad["APP_DOMAIN"] = ""
    with pytest.raises(ValueError, match="APP_DOMAIN:empty-deployed"):
        build_runtime_security_policy(Settings(**bad))

    # Fail: localhost APP_DOMAIN
    bad = base_settings_dict.copy()
    bad["APP_DOMAIN"] = "localhost"
    with pytest.raises(ValueError, match="APP_DOMAIN:loopback-deployed"):
        build_runtime_security_policy(Settings(**bad))

    # Fail: CORS empty
    bad = base_settings_dict.copy()
    bad["CORS_ALLOWED_ORIGINS"] = ""
    with pytest.raises(ValueError, match="CORS_ALLOWED_ORIGINS:empty-deployed"):
        build_runtime_security_policy(Settings(**bad))

    # Fail: HTTP origin in CORS
    bad = base_settings_dict.copy()
    bad["CORS_ALLOWED_ORIGINS"] = "http://dev.astro.vasiliy-ivanov.ru"
    with pytest.raises(ValueError, match="http-forbidden-deployed"):
        build_runtime_security_policy(Settings(**bad))

    # Fail: localhost CORS origin in deployed
    bad = base_settings_dict.copy()
    bad["CORS_ALLOWED_ORIGINS"] = "https://dev.astro.vasiliy-ivanov.ru,https://localhost"
    with pytest.raises(ValueError, match="origin\\[\\d+\\]:loopback-forbidden-deployed"):
        build_runtime_security_policy(Settings(**bad))

    # Fail: loopback CORS origin in deployed
    bad = base_settings_dict.copy()
    bad["CORS_ALLOWED_ORIGINS"] = "https://dev.astro.vasiliy-ivanov.ru,https://127.0.0.2"
    with pytest.raises(ValueError, match="origin\\[\\d+\\]:loopback-forbidden-deployed"):
        build_runtime_security_policy(Settings(**bad))

    # Fail: Missing own domain in CORS
    bad = base_settings_dict.copy()
    bad["CORS_ALLOWED_ORIGINS"] = "https://other.domain.com"
    with pytest.raises(ValueError, match="CORS_ALLOWED_ORIGINS:own-origin-missing"):
        build_runtime_security_policy(Settings(**bad))

    # Fail: DEV_MODE=true
    bad = base_settings_dict.copy()
    bad["DEV_MODE"] = True
    with pytest.raises(ValueError, match="DEV_MODE:true-deployed"):
        build_runtime_security_policy(Settings(**bad))

    # Fail: SESSION_COOKIE_SECURE=false
    bad = base_settings_dict.copy()
    bad["SESSION_COOKIE_SECURE"] = False
    with pytest.raises(ValueError, match="SESSION_COOKIE_SECURE:false-deployed"):
        build_runtime_security_policy(Settings(**bad))

    # Fail: empty TELEGRAM_BOT_TOKEN
    bad = base_settings_dict.copy()
    bad["TELEGRAM_BOT_TOKEN"] = ""
    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN:empty-deployed"):
        build_runtime_security_policy(Settings(**bad))

    # Fail: short salt
    bad = base_settings_dict.copy()
    bad["GRACE_USER_SALT"] = "short"
    with pytest.raises(ValueError, match="GRACE_USER_SALT:too-short-deployed"):
        build_runtime_security_policy(Settings(**bad))

    # Fail: SQLite DATABASE_URL
    bad = base_settings_dict.copy()
    bad["DATABASE_URL"] = "sqlite+aiosqlite:///./astro_dev.db"
    with pytest.raises(ValueError, match="DATABASE_URL:sqlite-deployed"):
        build_runtime_security_policy(Settings(**bad))


def test_internal_routes_policy():
    # START_FUNCTION_CONTRACT: F-M-TEST-RUNTIME-SECURITY-POLICY.test_internal_routes_policy
    # purpose: Verify that internal routes are only enabled for local development.
    # inputs: none
    # returns: none
    # side_effects: none
    # emitted_logs: none
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-RUNTIME-SECURITY-POLICY.test_internal_routes_policy
    # Enabled only in development, dev_mode=True, app_domain=localhost/127.0.0.1/::1
    s = Settings(_env_file=None, APP_ENV="dev", DEV_MODE=True, APP_DOMAIN="localhost")
    policy = build_runtime_security_policy(s)
    assert policy.internal_routes_enabled is True

    # Disabled if dev_mode=False
    s = Settings(_env_file=None, APP_ENV="dev", DEV_MODE=False, APP_DOMAIN="localhost")
    policy = build_runtime_security_policy(s)
    assert policy.internal_routes_enabled is False

    # Disabled if domain is not local
    s = Settings(_env_file=None, APP_ENV="dev", DEV_MODE=True, APP_DOMAIN="dev.astro.vasiliy-ivanov.ru")
    with pytest.raises(ValueError, match="Public development deployment is forbidden"):
        build_runtime_security_policy(s)


def test_loopback_rejection():
    # START_FUNCTION_CONTRACT: F-M-TEST-RUNTIME-SECURITY-POLICY.test_loopback_rejection
    # purpose: Verify that IPv4 and IPv6 loopback addresses are rejected as APP_DOMAIN in deployed envs.
    # inputs: none
    # returns: none
    # side_effects: none
    # emitted_logs: none
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-RUNTIME-SECURITY-POLICY.test_loopback_rejection
    # IPv4 loopbacks
    for ip in ("127.0.0.1", "127.0.0.2", "127.255.255.255"):
        bad = {
            "_env_file": None,
            "APP_ENV": "staging",
            "APP_DOMAIN": ip,
            "CORS_ALLOWED_ORIGINS": f"https://{ip}",
            "DEV_MODE": False,
            "SESSION_COOKIE_SECURE": True,
            "TELEGRAM_BOT_TOKEN": "token",
            "GRACE_USER_SALT": "a" * 32,
            "DATABASE_URL": "postgresql+asyncpg://astro:astro@127.0.0.1:5432/astro",
        }
        with pytest.raises(ValueError, match="APP_DOMAIN:loopback-deployed"):
            build_runtime_security_policy(Settings(**bad))

    # IPv6 loopback
    bad_v6 = {
        "_env_file": None,
        "APP_ENV": "staging",
        "APP_DOMAIN": "::1",
        "CORS_ALLOWED_ORIGINS": "https://[::1]",
        "DEV_MODE": False,
        "SESSION_COOKIE_SECURE": True,
        "TELEGRAM_BOT_TOKEN": "token",
        "GRACE_USER_SALT": "a" * 32,
        "DATABASE_URL": "postgresql+asyncpg://astro:astro@127.0.0.1:5432/astro",
    }
    with pytest.raises(ValueError, match="APP_DOMAIN:loopback-deployed"):
        build_runtime_security_policy(Settings(**bad_v6))


def test_canary_safe_exceptions():
    # START_FUNCTION_CONTRACT: F-M-TEST-RUNTIME-SECURITY-POLICY.test_canary_safe_exceptions
    # purpose: Verify that configuration secrets/values are not leaked in exception messages.
    # inputs: none
    # returns: none
    # side_effects: none
    # emitted_logs: none
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-RUNTIME-SECURITY-POLICY.test_canary_safe_exceptions
    canary = "SECRET_CANARY_VALUE_THAT_SHOULD_NOT_LEAK"

    # 1. Invalid APP_ENV with canary
    s = Settings(_env_file=None, APP_ENV=canary)
    with pytest.raises(ValueError) as excinfo:
        build_runtime_security_policy(s)
    assert canary not in str(excinfo.value)

    # 2. Invalid CORS origin with canary
    s2 = Settings(
        _env_file=None,
        APP_ENV="staging",
        APP_DOMAIN="astro.example.com",
        CORS_ALLOWED_ORIGINS=f"https://{canary}.com",
        DEV_MODE=False,
        SESSION_COOKIE_SECURE=True,
        TELEGRAM_BOT_TOKEN="token",
        GRACE_USER_SALT="a" * 32,
        DATABASE_URL="postgresql+asyncpg://astro:astro@127.0.0.1:5432/astro",
    )
    with pytest.raises(ValueError) as excinfo:
        build_runtime_security_policy(s2)
    assert canary not in str(excinfo.value)


def _deployed_settings(**overrides):
    """Valid deployed (production) baseline for billing-policy tests."""
    base = {
        "_env_file": None,
        "APP_ENV": "production",
        "APP_DOMAIN": "astro.vasiliy-ivanov.ru",
        "CORS_ALLOWED_ORIGINS": "https://astro.vasiliy-ivanov.ru",
        "DEV_MODE": False,
        "SESSION_COOKIE_SECURE": True,
        "TELEGRAM_BOT_TOKEN": "real_token_here",
        "GRACE_USER_SALT": "a" * 32,
        "DATABASE_URL": "postgresql+asyncpg://astro:astro@127.0.0.1:5432/astro",
        "YOOKASSA_MODE": "test",
        "YOOKASSA_TRUSTED_PROXY_CIDRS": "172.31.235.1/32",
    }
    base.update(overrides)
    return Settings(**base)


def test_billing_off_keeps_empty_credentials_valid():
    policy = build_runtime_security_policy(_deployed_settings())
    assert policy.environment == "production"
    # Recurrent without master is rejected even with billing off.
    with pytest.raises(ValueError, match="YOOKASSA_RECURRENT:without-master"):
        build_runtime_security_policy(
            _deployed_settings(YOOKASSA_RECURRENT_ENABLED=True)
        )


def test_billing_mode_must_be_exact_test_or_live():
    with pytest.raises(ValueError, match="YOOKASSA_MODE:invalid-deployed"):
        build_runtime_security_policy(_deployed_settings(YOOKASSA_MODE="sandbox"))
    with pytest.raises(ValueError, match="YOOKASSA_MODE:invalid-deployed"):
        build_runtime_security_policy(_deployed_settings(YOOKASSA_MODE="TEST"))
    policy = build_runtime_security_policy(_deployed_settings(YOOKASSA_MODE="live"))
    assert policy.environment == "production"


def test_billing_enabled_requires_credentials_and_https_return_url():
    enabled = {
        "YOOKASSA_ENABLED": True,
        "YOOKASSA_TEST_SHOP_ID": "shop-synthetic",
        "YOOKASSA_TEST_SECRET_KEY": "synthetic-secret",
        "YOOKASSA_RETURN_URL": "https://astro.vasiliy-ivanov.ru/profile",
    }
    policy = build_runtime_security_policy(_deployed_settings(**enabled))
    assert policy.environment == "production"

    with pytest.raises(ValueError, match="YOOKASSA_SHOP_ID:empty-billing"):
        build_runtime_security_policy(_deployed_settings(**{**enabled, "YOOKASSA_TEST_SHOP_ID": "  "}))
    with pytest.raises(ValueError, match="YOOKASSA_SECRET_KEY:empty-billing"):
        build_runtime_security_policy(_deployed_settings(**{**enabled, "YOOKASSA_TEST_SECRET_KEY": ""}))
    with pytest.raises(ValueError, match="YOOKASSA_RETURN_URL:invalid-billing"):
        build_runtime_security_policy(_deployed_settings(**{**enabled, "YOOKASSA_RETURN_URL": "http://astro.vasiliy-ivanov.ru"}))
    with pytest.raises(ValueError, match="YOOKASSA_RETURN_URL:invalid-billing"):
        build_runtime_security_policy(_deployed_settings(**{**enabled, "YOOKASSA_RETURN_URL": ""}))
    # Invalid port must not slip through urlparse (host:notaport).
    with pytest.raises(ValueError, match="YOOKASSA_RETURN_URL:invalid-billing"):
        build_runtime_security_policy(
            _deployed_settings(**{**enabled, "YOOKASSA_RETURN_URL": "https://astro.vasiliy-ivanov.ru:notaport/path"})
        )
    # Userinfo is forbidden (no credentials in the return URL).
    with pytest.raises(ValueError, match="YOOKASSA_RETURN_URL:invalid-billing"):
        build_runtime_security_policy(
            _deployed_settings(**{**enabled, "YOOKASSA_RETURN_URL": "https://user:pass@astro.vasiliy-ivanov.ru"})
        )
    # Path and query are valid.
    policy = build_runtime_security_policy(
        _deployed_settings(**{**enabled, "YOOKASSA_RETURN_URL": "https://astro.vasiliy-ivanov.ru/profile?from=pay"})
    )
    assert policy.environment == "production"
    # The error text never carries the offending URL.
    try:
        build_runtime_security_policy(
            _deployed_settings(**{**enabled, "YOOKASSA_RETURN_URL": "https://user:secret@astro.vasiliy-ivanov.ru"})
        )
        raise AssertionError("expected invalid-billing")
    except ValueError as exc:
        assert "user:secret" not in str(exc)
        assert "astro.vasiliy-ivanov.ru" not in str(exc)

    # Live mode picks the LIVE credential pair, not the test pair.
    with pytest.raises(ValueError, match="YOOKASSA_SHOP_ID:empty-billing"):
        build_runtime_security_policy(_deployed_settings(**{**enabled, "YOOKASSA_MODE": "live"}))


def test_natal_report_requires_billing_in_deployed_env():
    with pytest.raises(ValueError, match="NATAL_REPORT_ENABLED:requires-billing"):
        build_runtime_security_policy(_deployed_settings(NATAL_REPORT_ENABLED=True))
    policy = build_runtime_security_policy(
        _deployed_settings(
            NATAL_REPORT_ENABLED=True,
            YOOKASSA_ENABLED=True,
            YOOKASSA_TEST_SHOP_ID="shop-synthetic",
            YOOKASSA_TEST_SECRET_KEY="synthetic-secret",
            YOOKASSA_RETURN_URL="https://astro.vasiliy-ivanov.ru/profile",
        )
    )
    assert policy.environment == "production"


def test_production_billing_pins_webhook_allowlist_and_trusted_proxy():
    enabled = {
        "YOOKASSA_ENABLED": True,
        "YOOKASSA_TEST_SHOP_ID": "shop-synthetic",
        "YOOKASSA_TEST_SECRET_KEY": "synthetic-secret",
        "YOOKASSA_RETURN_URL": "https://astro.vasiliy-ivanov.ru/profile",
    }
    # Override of the official webhook ranges is forbidden in production.
    with pytest.raises(ValueError, match="YOOKASSA_WEBHOOK_IP_ALLOWLIST:nonempty-production"):
        build_runtime_security_policy(
            _deployed_settings(**{**enabled, "YOOKASSA_WEBHOOK_IP_ALLOWLIST": "185.71.76.0/27"})
        )
    # Trusted proxy must be EXACTLY the canonical gateway /32.
    with pytest.raises(ValueError, match="YOOKASSA_TRUSTED_PROXY_CIDRS:non-canonical-production"):
        build_runtime_security_policy(
            _deployed_settings(**{**enabled, "YOOKASSA_TRUSTED_PROXY_CIDRS": ""})
        )
    with pytest.raises(ValueError, match="YOOKASSA_TRUSTED_PROXY_CIDRS:non-canonical-production"):
        build_runtime_security_policy(
            _deployed_settings(**{**enabled, "YOOKASSA_TRUSTED_PROXY_CIDRS": "172.31.235.0/24"})
        )
    with pytest.raises(ValueError, match="YOOKASSA_TRUSTED_PROXY_CIDRS:non-canonical-production"):
        build_runtime_security_policy(
            _deployed_settings(**{**enabled, "YOOKASSA_TRUSTED_PROXY_CIDRS": "10.0.0.0/8"})
        )
    with pytest.raises(ValueError, match="YOOKASSA_TRUSTED_PROXY_CIDRS:invalid"):
        build_runtime_security_policy(
            _deployed_settings(**{**enabled, "YOOKASSA_TRUSTED_PROXY_CIDRS": "not-a-cidr"})
        )
    # Staging does NOT pin the production gateway.
    staging = _deployed_settings(
        APP_ENV="staging",
        YOOKASSA_TRUSTED_PROXY_CIDRS="127.0.0.1/32,::1/128",
        **enabled,
    )
    policy = build_runtime_security_policy(staging)
    assert policy.environment == "staging"
