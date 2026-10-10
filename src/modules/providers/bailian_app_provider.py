"""Call the Bailian app gateway, constructing only customer-side requests."""

from ...lib.upstream_client import fetch_upstream
from .header_utils import copy_forwardable_headers

FALLBACK_USER_AGENT = "happyoyster-sdk-demo-python"


def _build_openapi_path(path):
    return f"/{path.lstrip('/')}"


def _build_headers(proxy_request, config):
    headers = copy_forwardable_headers(proxy_request.headers)
    headers.pop("x-happy-oyster-mode", None)

    headers["authorization"] = f"Bearer {config.dashscope_api_key}"
    headers["accept-encoding"] = "identity"

    if proxy_request.body and "content-type" not in headers:
        headers["content-type"] = "application/json"

    if "user-agent" not in headers:
        headers["user-agent"] = FALLBACK_USER_AGENT

    return headers


def call_bailian_app(proxy_request, *, config, fetch_impl=None):
    return fetch_upstream(
        origin=config.bailian_gateway_base_urls_by_mode[proxy_request.mode],
        path=_build_openapi_path(proxy_request.path),
        search=proxy_request.search,
        method=proxy_request.method,
        headers=_build_headers(proxy_request, config),
        body=proxy_request.body,
        timeout_ms=config.request_timeout_ms,
        fetch_impl=fetch_impl,
    )
