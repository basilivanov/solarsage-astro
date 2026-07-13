# ############################################################################
# AI_HEADER: MODULE_TODAY_PREVIEW_GUARD — pure closed local-preview authorization.
# ROLE: Validates explicit scalar transport and identity facts before Today V2 selection.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-PREVIEW-GUARD
# purpose: Authorize the single development-only Today V2 preview transport
#          combination without framework, persistence, logging, or ambient state.
# owns:
#   - apps/api/app/services/today_preview_guard.py
# inputs: Immutable scalar environment, marker, transport, and Telegram identity facts.
# outputs: Immutable authorization decision with a closed safe reason.
# dependencies: Python dataclasses, enum, ipaddress, and urllib.parse modules only.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Production denial is evaluated before marker, transport, or identity facts.
#   - Authorization requires development, the exact marker, a loopback raw Host,
#     all-loopback transport, effective external port 3003, and the exact identity.
#   - Decisions never contain raw request, header, host, or identity values.
# failure_policy: Malformed, public, incomplete, or unexpected facts fail closed.
# END_MODULE_CONTRACT: M-TODAY-PREVIEW-GUARD

# START_MODULE_MAP: M-TODAY-PREVIEW-GUARD
# public_entrypoints:
#   - TodayPreviewGuardReason
#   - TodayPreviewGuardInput
#   - TodayPreviewGuardDecision
#   - authorize_today_preview
# semantic_blocks:
#   - CLOSED_CONTRACT: exact preview constants and immutable values.
#   - BOUNDED_TRANSPORT_PARSING: bounded authority and Forwarded parsing helpers.
#   - PREVIEW_AUTHORIZATION: ordered fail-closed authorization decision.
# owned_tests:
#   - apps/api/tests/test_today_preview_transport.py
# END_MODULE_MAP: M-TODAY-PREVIEW-GUARD

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from ipaddress import ip_address
from urllib.parse import urlsplit


# START_BLOCK: CLOSED_CONTRACT
TODAY_PREVIEW_HEADER_NAME = "X-SolarSage-Preview-Mode"
TODAY_PREVIEW_HEADER_VALUE = "today-v2-real"
TODAY_PREVIEW_TG_USER_ID = 999999999
TODAY_PREVIEW_TG_USERNAME = "dev_user"
TODAY_PREVIEW_PORT = 3003


class TodayPreviewGuardReason(StrEnum):
    """Closed, non-sensitive reasons for the preview authorization decision."""

    AUTHORIZED = "authorized"
    PRODUCTION_DENIED = "production_denied"
    APP_ENV_DENIED = "app_env_denied"
    MARKER_DENIED = "marker_denied"
    CLIENT_DENIED = "client_denied"
    FORWARDED_CHAIN_DENIED = "forwarded_chain_denied"
    HOST_DENIED = "host_denied"
    ORIGIN_DENIED = "origin_denied"
    PORT_DENIED = "port_denied"
    IDENTITY_DENIED = "identity_denied"


@dataclass(frozen=True, slots=True)
class TodayPreviewGuardInput:
    """Explicit scalar facts used by the pure preview guard."""

    app_env: str
    marker_value: str | None
    client_host: str | None
    host: str | None
    origin: str | None
    forwarded: str | None
    x_forwarded_for: str | None
    x_forwarded_host: str | None
    x_forwarded_port: str | None
    x_real_ip: str | None
    tg_user_id: int | None
    tg_username: str | None


@dataclass(frozen=True, slots=True)
class TodayPreviewGuardDecision:
    """Safe preview authorization result without raw request facts."""

    authorized: bool
    reason: TodayPreviewGuardReason


@dataclass(frozen=True, slots=True)
class _Authority:
    host: str
    port: int | None
# END_BLOCK: CLOSED_CONTRACT


# START_BLOCK: BOUNDED_TRANSPORT_PARSING
_MAX_AUTHORITY_LENGTH = 512
_MAX_FORWARDED_LENGTH = 4096
_MAX_CHAIN_ITEMS = 16
_MAX_PARAMETERS_PER_ITEM = 16


def _normalize_environment(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip().lower()


def _parse_port(value: str) -> int | None:
    if not value or not value.isascii() or not value.isdecimal():
        return None
    port = int(value)
    if not 1 <= port <= 65535:
        return None
    return port


def _parse_authority(value: object) -> _Authority | None:
    if not isinstance(value, str):
        return None
    authority = value.strip()
    if not authority or len(authority) > _MAX_AUTHORITY_LENGTH:
        return None
    if "@" in authority or any(character.isspace() or ord(character) < 32 for character in authority):
        return None

    host: str
    port: int | None = None
    if authority.startswith("["):
        closing = authority.find("]")
        if closing <= 1:
            return None
        host = authority[1:closing]
        remainder = authority[closing + 1 :]
        if remainder:
            if not remainder.startswith(":"):
                return None
            port = _parse_port(remainder[1:])
            if port is None:
                return None
        try:
            parsed_ip = ip_address(host)
        except ValueError:
            return None
        if parsed_ip.version != 6:
            return None
        return _Authority(host=str(parsed_ip), port=port)

    colon_count = authority.count(":")
    if colon_count == 0:
        host = authority
    elif colon_count == 1:
        host, raw_port = authority.rsplit(":", 1)
        port = _parse_port(raw_port)
        if not host or port is None:
            return None
    else:
        try:
            parsed_ip = ip_address(authority)
        except ValueError:
            return None
        if parsed_ip.version != 6:
            return None
        return _Authority(host=str(parsed_ip), port=None)

    normalized_host = host.lower()
    if normalized_host == "localhost":
        return _Authority(host=normalized_host, port=port)
    try:
        parsed_ip = ip_address(normalized_host)
    except ValueError:
        return None
    return _Authority(host=str(parsed_ip), port=port)


def _is_loopback_authority(authority: _Authority) -> bool:
    if authority.host == "localhost":
        return True
    try:
        return ip_address(authority.host).is_loopback
    except ValueError:
        return False


def _split_bounded(value: object, delimiter: str) -> list[str] | None:
    if not isinstance(value, str) or not value or len(value) > _MAX_FORWARDED_LENGTH:
        return None
    items = [item.strip() for item in value.split(delimiter)]
    if not items or len(items) > _MAX_CHAIN_ITEMS or any(not item for item in items):
        return None
    return items


def _split_quoted(value: str, delimiter: str, *, maximum: int) -> list[str] | None:
    items: list[str] = []
    current: list[str] = []
    quoted = False
    escaped = False
    for character in value:
        if ord(character) < 32 and character != "\t":
            return None
        if escaped:
            current.append(character)
            escaped = False
            continue
        if quoted and character == "\\":
            current.append(character)
            escaped = True
            continue
        if character == '"':
            quoted = not quoted
            current.append(character)
            continue
        if character == delimiter and not quoted:
            item = "".join(current).strip()
            if not item:
                return None
            items.append(item)
            if len(items) >= maximum:
                return None
            current = []
            continue
        current.append(character)
    if quoted or escaped:
        return None
    item = "".join(current).strip()
    if not item:
        return None
    items.append(item)
    return items if len(items) <= maximum else None


def _unquote_forwarded_value(value: str) -> str | None:
    candidate = value.strip()
    if not candidate:
        return None
    if not candidate.startswith('"'):
        if '"' in candidate or "\\" in candidate or any(character.isspace() for character in candidate):
            return None
        return candidate
    if len(candidate) < 2 or not candidate.endswith('"'):
        return None
    output: list[str] = []
    escaped = False
    for character in candidate[1:-1]:
        if escaped:
            output.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == '"' or ord(character) < 32:
            return None
        else:
            output.append(character)
    if escaped:
        return None
    return "".join(output) or None


def _is_parameter_name(value: str) -> bool:
    if not value:
        return False
    allowed = "!#$%&'*+-.^_`|~"
    return all(character.isalnum() or character in allowed for character in value)


def _parse_forwarded(value: object) -> tuple[list[str], list[str]] | None:
    if not isinstance(value, str) or not value or len(value) > _MAX_FORWARDED_LENGTH:
        return None
    elements = _split_quoted(value, ",", maximum=_MAX_CHAIN_ITEMS)
    if elements is None:
        return None
    client_tokens: list[str] = []
    host_tokens: list[str] = []
    for element in elements:
        parameters = _split_quoted(
            element,
            ";",
            maximum=_MAX_PARAMETERS_PER_ITEM,
        )
        if parameters is None:
            return None
        seen: set[str] = set()
        for parameter in parameters:
            if "=" not in parameter:
                return None
            raw_name, raw_value = parameter.split("=", 1)
            name = raw_name.strip().lower()
            if not _is_parameter_name(name):
                return None
            if name not in {"for", "host"}:
                continue
            if name in seen:
                return None
            seen.add(name)
            parsed_value = _unquote_forwarded_value(raw_value)
            if parsed_value is None:
                return None
            if name == "for":
                client_tokens.append(parsed_value)
            else:
                host_tokens.append(parsed_value)
    if not client_tokens:
        return None
    return client_tokens, host_tokens


def _all_loopback_tokens(tokens: list[str]) -> bool:
    for token in tokens:
        lowered = token.lower()
        if lowered == "unknown" or lowered.startswith("_"):
            return False
        authority = _parse_authority(token)
        if authority is None or not _is_loopback_authority(authority):
            return False
    return True


def _parse_loopback_host_chain(value: object) -> list[_Authority] | None:
    tokens = _split_bounded(value, ",")
    if tokens is None:
        return None
    authorities: list[_Authority] = []
    for token in tokens:
        authority = _parse_authority(token)
        if authority is None or not _is_loopback_authority(authority):
            return None
        authorities.append(authority)
    return authorities


def _origin_is_local_preview(value: object) -> bool:
    if not isinstance(value, str) or not value or len(value) > _MAX_AUTHORITY_LENGTH:
        return False
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return False
    if parsed.scheme.lower() not in {"http", "https"}:
        return False
    if not parsed.netloc or parsed.username is not None or parsed.password is not None:
        return False
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        return False
    if parsed.hostname is None or port != TODAY_PREVIEW_PORT:
        return False
    authority = _parse_authority(parsed.hostname)
    return authority is not None and _is_loopback_authority(authority)
# END_BLOCK: BOUNDED_TRANSPORT_PARSING


# START_BLOCK: PREVIEW_AUTHORIZATION
def authorize_today_preview(
    guard_input: TodayPreviewGuardInput,
) -> TodayPreviewGuardDecision:
    # START_FUNCTION_CONTRACT: F-M-TODAY-PREVIEW-GUARD.authorize_today_preview
    # purpose: Authorize the exact closed local development Today V2 preview combination.
    # inputs: guard_input — immutable explicit environment, transport, marker, and identity facts.
    # returns: Immutable safe decision containing authorization and a closed reason only.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: Unexpected or malformed facts return a denial; no raw values are raised or returned.
    # END_FUNCTION_CONTRACT: F-M-TODAY-PREVIEW-GUARD.authorize_today_preview
    """Evaluate the preview proof in the required fail-closed order."""
    app_env = _normalize_environment(guard_input.app_env)
    if app_env == "production":
        return TodayPreviewGuardDecision(
            authorized=False,
            reason=TodayPreviewGuardReason.PRODUCTION_DENIED,
        )
    if app_env != "development":
        return TodayPreviewGuardDecision(
            authorized=False,
            reason=TodayPreviewGuardReason.APP_ENV_DENIED,
        )

    if guard_input.marker_value != TODAY_PREVIEW_HEADER_VALUE:
        return TodayPreviewGuardDecision(
            authorized=False,
            reason=TodayPreviewGuardReason.MARKER_DENIED,
        )

    client_authority = _parse_authority(guard_input.client_host)
    if client_authority is None or not _is_loopback_authority(client_authority):
        return TodayPreviewGuardDecision(
            authorized=False,
            reason=TodayPreviewGuardReason.CLIENT_DENIED,
        )

    forwarded_clients: list[str] = []
    forwarded_hosts: list[str] = []
    if guard_input.forwarded is not None:
        parsed_forwarded = _parse_forwarded(guard_input.forwarded)
        if parsed_forwarded is None:
            return TodayPreviewGuardDecision(
                authorized=False,
                reason=TodayPreviewGuardReason.FORWARDED_CHAIN_DENIED,
            )
        forwarded_clients, forwarded_hosts = parsed_forwarded
        if not _all_loopback_tokens(forwarded_clients):
            return TodayPreviewGuardDecision(
                authorized=False,
                reason=TodayPreviewGuardReason.FORWARDED_CHAIN_DENIED,
            )

    if guard_input.x_forwarded_for is not None:
        x_forwarded_clients = _split_bounded(guard_input.x_forwarded_for, ",")
        if x_forwarded_clients is None or not _all_loopback_tokens(x_forwarded_clients):
            return TodayPreviewGuardDecision(
                authorized=False,
                reason=TodayPreviewGuardReason.FORWARDED_CHAIN_DENIED,
            )

    if guard_input.x_real_ip is not None:
        real_ip_tokens = _split_bounded(guard_input.x_real_ip, ",")
        if (
            real_ip_tokens is None
            or len(real_ip_tokens) != 1
            or not _all_loopback_tokens(real_ip_tokens)
        ):
            return TodayPreviewGuardDecision(
                authorized=False,
                reason=TodayPreviewGuardReason.FORWARDED_CHAIN_DENIED,
            )

    parsed_forwarded_hosts: list[_Authority] = []
    for forwarded_host in forwarded_hosts:
        authority = _parse_authority(forwarded_host)
        if authority is None or not _is_loopback_authority(authority):
            return TodayPreviewGuardDecision(
                authorized=False,
                reason=TodayPreviewGuardReason.FORWARDED_CHAIN_DENIED,
            )
        parsed_forwarded_hosts.append(authority)

    x_forwarded_hosts: list[_Authority] = []
    if guard_input.x_forwarded_host is not None:
        parsed_hosts = _parse_loopback_host_chain(guard_input.x_forwarded_host)
        if parsed_hosts is None:
            return TodayPreviewGuardDecision(
                authorized=False,
                reason=TodayPreviewGuardReason.FORWARDED_CHAIN_DENIED,
            )
        x_forwarded_hosts = parsed_hosts

    host_authority = _parse_authority(guard_input.host)
    if guard_input.host is not None and (
        host_authority is None or not _is_loopback_authority(host_authority)
    ):
        return TodayPreviewGuardDecision(
            authorized=False,
            reason=TodayPreviewGuardReason.HOST_DENIED,
        )

    effective_host: _Authority | None
    if x_forwarded_hosts:
        effective_host = x_forwarded_hosts[0]
    elif parsed_forwarded_hosts:
        effective_host = parsed_forwarded_hosts[0]
    else:
        effective_host = host_authority
    if effective_host is None or not _is_loopback_authority(effective_host):
        return TodayPreviewGuardDecision(
            authorized=False,
            reason=TodayPreviewGuardReason.HOST_DENIED,
        )

    if guard_input.origin is not None and not _origin_is_local_preview(guard_input.origin):
        return TodayPreviewGuardDecision(
            authorized=False,
            reason=TodayPreviewGuardReason.ORIGIN_DENIED,
        )

    effective_port: int | None
    if guard_input.x_forwarded_port is not None:
        raw_forwarded_port = guard_input.x_forwarded_port.strip()
        effective_port = _parse_port(raw_forwarded_port)
    elif effective_host.port is not None:
        effective_port = effective_host.port
    elif host_authority is not None:
        effective_port = host_authority.port
    else:
        effective_port = None
    if effective_port != TODAY_PREVIEW_PORT:
        return TodayPreviewGuardDecision(
            authorized=False,
            reason=TodayPreviewGuardReason.PORT_DENIED,
        )

    exact_user_id = (
        isinstance(guard_input.tg_user_id, int)
        and not isinstance(guard_input.tg_user_id, bool)
        and guard_input.tg_user_id == TODAY_PREVIEW_TG_USER_ID
    )
    if not exact_user_id or guard_input.tg_username != TODAY_PREVIEW_TG_USERNAME:
        return TodayPreviewGuardDecision(
            authorized=False,
            reason=TodayPreviewGuardReason.IDENTITY_DENIED,
        )

    return TodayPreviewGuardDecision(
        authorized=True,
        reason=TodayPreviewGuardReason.AUTHORIZED,
    )
# END_BLOCK: PREVIEW_AUTHORIZATION
