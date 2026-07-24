# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_NGINX_PROMO_PRIVACY
# ROLE: Static assertion test suite for Nginx privacy log format and promo location config.
# DEPENDENCIES: pytest, pathlib
# GRACE_ANCHORS: [TEST_NGINX_PROMO_PRIVACY]
# WAVE: W-NAMED-PROMO-CAMPAIGN
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-NGINX-PROMO-PRIVACY
# purpose: Validate static Nginx configuration invariants for transport privacy (no raw request/query/referer in logs, strict-origin Referrer-Policy) and promo volumetric rate limiting (120r/m, burst=60 nodelay, 1k body size).
# owns:
#   - apps/api/tests/test_nginx_promo_privacy.py
# inputs: infra/nginx/astro.vasiliy-ivanov.ru.conf
# outputs: pytest execution assertions
# dependencies: none
# side_effects: none (reads static config file)
# failure_policy: raise assertions
# END_MODULE_CONTRACT: M-TEST-NGINX-PROMO-PRIVACY

# START_MODULE_MAP: M-TEST-NGINX-PROMO-PRIVACY
# public_entrypoints:
#   - test_nginx_log_format_privacy
#   - test_nginx_server_blocks_use_named_privacy_format
#   - test_nginx_referrer_policy_strict_origin
#   - test_nginx_promo_location_anchored_and_rate_limited
#   - test_nginx_promo_location_body_cap_1k
#   - test_nginx_promo_location_canonical_proxy_headers
#   - test_nginx_generic_api_and_frontend_remain
# owned_tests:
#   - apps/api/tests/test_nginx_promo_privacy.py
# END_MODULE_MAP: M-TEST-NGINX-PROMO-PRIVACY

from pathlib import Path
import re
import pytest

CONF_PATH = Path(__file__).resolve().parents[3] / "infra" / "nginx" / "astro.vasiliy-ivanov.ru.conf"


@pytest.fixture
def conf_content() -> str:
    assert CONF_PATH.is_file(), f"Nginx config not found at {CONF_PATH}"
    return CONF_PATH.read_text(encoding="utf-8")


def test_nginx_log_format_privacy(conf_content: str) -> None:
    # 1. log_format astro_privacy must be defined
    assert "log_format astro_privacy" in conf_content

    # Extract log_format definition line(s)
    log_fmt_match = re.search(r"log_format\s+astro_privacy\s+([^;]+);", conf_content, re.MULTILINE)
    assert log_fmt_match is not None
    log_fmt_str = log_fmt_match.group(1)

    # Must contain request method, uri, server_protocol
    assert "$request_method" in log_fmt_str
    assert "$uri" in log_fmt_str
    assert "$server_protocol" in log_fmt_str

    # FORBIDDEN variables in privacy log format
    for forbidden in ("$request", "$request_uri", "$args", "$query_string", "$http_referer"):
        var_pattern = r"\\" + forbidden + r"\b"
        assert not re.search(var_pattern, log_fmt_str), f"Forbidden variable {forbidden} found in log_format astro_privacy"


def test_nginx_server_blocks_use_named_privacy_format(conf_content: str) -> None:
    # Count occurrences of access_log ... astro_privacy
    access_logs = re.findall(r"access_log\s+[\w/\.]+\s+astro_privacy;", conf_content)
    assert len(access_logs) >= 2, "Both server blocks (HTTP and HTTPS) must use astro_privacy access_log"


def test_nginx_referrer_policy_strict_origin(conf_content: str) -> None:
    assert 'Referrer-Policy "strict-origin"' in conf_content
    assert "strict-origin-when-cross-origin" not in conf_content


def test_nginx_promo_location_anchored_and_rate_limited(conf_content: str) -> None:
    # Volumetric rate limit zone
    assert "limit_req_zone $binary_remote_addr zone=promo_limit:10m rate=120r/m;" in conf_content
    assert "limit_req_status 429;" in conf_content

    # Location pattern anchored
    assert r"location ~ ^/api/promo/(preview|redeem)$" in conf_content
    assert "limit_req zone=promo_limit burst=60 nodelay;" in conf_content


def test_nginx_promo_location_body_cap_1k(conf_content: str) -> None:
    promo_block = re.search(
        r"location\s+~\s+\^/api/promo/\(preview\|redeem\)\$\s*\{([^}]+)\}",
        conf_content,
    )
    assert promo_block is not None
    block_str = promo_block.group(1)
    assert "client_max_body_size 1k;" in block_str


def test_nginx_promo_location_canonical_proxy_headers(conf_content: str) -> None:
    promo_block = re.search(
        r"location\s+~\s+\^/api/promo/\(preview\|redeem\)\$\s*\{([^}]+)\}",
        conf_content,
    )
    assert promo_block is not None
    block_str = promo_block.group(1)

    assert "proxy_pass http://127.0.0.1:8000;" in block_str
    assert "proxy_http_version 1.1;" in block_str
    assert "proxy_read_timeout 300s;" in block_str
    assert "proxy_send_timeout 300s;" in block_str
    assert "proxy_set_header Host $host;" in block_str
    assert "proxy_set_header X-Real-IP $remote_addr;" in block_str
    assert "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;" in block_str
    assert "proxy_set_header X-Forwarded-Proto $scheme;" in block_str
    assert "proxy_pass_header Set-Cookie;" in block_str


def test_nginx_generic_api_and_frontend_remain(conf_content: str) -> None:
    assert "location /api/ {" in conf_content
    assert "proxy_pass http://127.0.0.1:8000;" in conf_content
    assert "location / {" in conf_content
    assert "proxy_pass http://127.0.0.1:3002;" in conf_content
    assert "client_max_body_size 5m;" in conf_content


def test_nginx_dotfile_block_regex_matches_literal_dot(conf_content: str) -> None:
    # The dotfile deny rule must use a literal-dot regex (/\.), not an escaped
    # backslash (/\\.), which would never match hidden paths.
    assert r"location ~ /\.(?!well-known) {" in conf_content
    assert r"/\\.(?!well-known)" not in conf_content
