"""Convert HTTP requests into normalized proxy requests and forward them through the Bailian provider."""

import json
from dataclasses import dataclass
from typing import Mapping, Optional
from urllib.parse import parse_qs

from ...lib.gateway_error import GatewayError
from ...lib.http_utils import TEXT_CONTENT_TYPE, send_body
from ...lib.request_body import read_request_body
from ..providers.bailian_app_provider import call_bailian_app

_MISSING = object()


@dataclass(frozen=True)
class ProxyRequest:
    method: str
    path: str
    search: str
    headers: Mapping[str, str]
    body: Optional[bytes]
    mode: int


def _normalize_mode(value):
    try:
        mode = float(value) if not isinstance(value, bool) else None
    except (TypeError, ValueError):
        mode = None
    if mode not in (1, 2, 3):
        raise GatewayError("PARAM_INVALID", "Request mode must be 1, 2, or 3")
    return int(mode)


def _body_mode(body):
    if not body:
        return _MISSING
    try:
        parsed = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return _MISSING
    return parsed.get("mode", _MISSING) if isinstance(parsed, dict) else _MISSING


def _resolve_mode(handler, url, upstream_path, body):
    candidates = handler.headers.get_all("X-Happy-Oyster-Mode") or []
    if upstream_path == "/openapi/v1/worlds" and handler.command == "GET":
        candidates.extend(parse_qs(url.query, keep_blank_values=True).get("mode", []))
    if upstream_path == "/openapi/v1/worlds" and handler.command == "POST":
        candidates.append(_body_mode(body))
    modes = [_normalize_mode(value) for value in candidates if value is not _MISSING]
    if not modes:
        raise GatewayError(
            "PARAM_INVALID",
            "Requests require mode 1, 2, or 3 in the request or x-happy-oyster-mode",
        )
    if any(mode != modes[0] for mode in modes):
        raise GatewayError("PARAM_INVALID", "Request mode values must match")
    return modes[0]


def handle_proxy(handler, *, config, fetch_impl, url, upstream_path):
    body = read_request_body(handler)
    mode = _resolve_mode(handler, url, upstream_path, body)
    proxy_request = ProxyRequest(
        method=handler.command,
        path=upstream_path,
        search=f"?{url.query}" if url.query else "",
        headers=handler.headers,
        body=body,
        mode=mode,
    )

    upstream = call_bailian_app(proxy_request, config=config, fetch_impl=fetch_impl)
    send_body(
        handler,
        upstream.status_code,
        upstream.body,
        content_type=upstream.content_type or TEXT_CONTENT_TYPE,
    )
