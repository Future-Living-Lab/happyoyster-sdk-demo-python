"""Generic upstream request, timeout, and error wrapping utilities."""

import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional


class UpstreamRequestError(Exception):
    """Raised when an upstream request does not receive an HTTP response, such as network failures or timeouts."""

    def __init__(self, message, cause=None):
        super().__init__(message)
        self.cause = cause


@dataclass
class UpstreamResponse:
    status_code: int
    body: bytes
    content_type: Optional[str] = None


def default_fetch(url, *, method, headers, body, timeout_ms):
    request = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout_ms / 1000) as response:
            return UpstreamResponse(
                status_code=response.status,
                body=response.read(),
                content_type=response.headers.get("content-type"),
            )
    except urllib.error.HTTPError as error:
        # 4xx / 5xx are valid upstream responses and are passed through unchanged.
        with error:
            return UpstreamResponse(
                status_code=error.code,
                body=error.read(),
                content_type=error.headers.get("content-type"),
            )


def fetch_upstream(
    *,
    origin,
    path,
    search="",
    method="GET",
    headers=None,
    body=None,
    timeout_ms,
    fetch_impl=None,
):
    fetch = fetch_impl or default_fetch
    url = f"{origin}{path}{search}"

    try:
        return fetch(url, method=method, headers=headers or {}, body=body, timeout_ms=timeout_ms)
    except Exception as error:
        raise UpstreamRequestError("Upstream request failed", error) from error
