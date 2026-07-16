"""Convert HTTP requests into normalized proxy requests and forward them through the Bailian provider."""

from dataclasses import dataclass
from typing import Mapping, Optional

from ...lib.http_utils import TEXT_CONTENT_TYPE, send_body
from ...lib.request_body import read_request_body
from ..providers.bailian_app_provider import call_bailian_app

@dataclass(frozen=True)
class ProxyRequest:
    method: str
    path: str
    search: str
    headers: Mapping[str, str]
    body: Optional[bytes]


def handle_proxy(handler, *, config, fetch_impl, url, upstream_path):
    body = read_request_body(handler)
    proxy_request = ProxyRequest(
        method=handler.command,
        path=upstream_path,
        search=f"?{url.query}" if url.query else "",
        headers=handler.headers,
        body=body,
    )

    upstream = call_bailian_app(proxy_request, config=config, fetch_impl=fetch_impl)
    send_body(
        handler,
        upstream.status_code,
        upstream.body,
        content_type=upstream.content_type or TEXT_CONTENT_TYPE,
    )
