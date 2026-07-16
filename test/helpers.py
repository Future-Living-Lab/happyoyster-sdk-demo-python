"""Shared test helpers: embedded test server and injectable fake upstream fetch."""

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from src.app import create_request_handler
from src.config import Config
from src.lib.upstream_client import UpstreamResponse


class SilentLogger:
    def info(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


def test_config():
    return Config(
        host="127.0.0.1",
        port=0,
        bailian_gateway_base_url="https://example.test/api/v2/apps/happyoyster-1.0",
        bailian_api_origin="https://example.test",
        dashscope_api_key="sk-test",
        request_timeout_ms=1_000,
    )


def json_response(data, status_code=200):
    return UpstreamResponse(
        status_code=status_code,
        body=json.dumps(data, separators=(",", ":")).encode("utf-8"),
        content_type="application/json",
    )


class RecordingFetch:
    """Record upstream call parameters; can return fixed responses or raise errors."""

    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def __call__(self, url, *, method, headers, body, timeout_ms):
        self.calls.append(
            {
                "url": url,
                "method": method,
                "headers": headers,
                "body": body,
                "timeout_ms": timeout_ms,
            }
        )
        if self.error is not None:
            raise self.error
        return self.response

    @property
    def last_call(self):
        return self.calls[-1]


def start_test_server(fetch_impl):
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        create_request_handler(
            config=test_config(), fetch_impl=fetch_impl, logger=SilentLogger()
        ),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    return server, base_url


def stop_test_server(server):
    server.shutdown()
    server.server_close()


def http_request(url, method="GET", body=None, headers=None):
    request = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        with error:
            return error.code, error.read()
