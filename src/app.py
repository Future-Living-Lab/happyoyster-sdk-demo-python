"""Composition root: wrap routing with an error boundary and minimal access logs."""

import logging
import time
from http.server import BaseHTTPRequestHandler

from .lib.gateway_error import GatewayError
from .lib.http_utils import send_gateway_error
from .lib.upstream_client import UpstreamRequestError
from .routes import route_request

HANDLED_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD")


def _to_error_payload(error):
    if isinstance(error, GatewayError):
        return error.code, str(error), error.data
    if isinstance(error, UpstreamRequestError):
        return "UPSTREAM_ERROR", "Upstream OpenAPI request failed", {}
    return "INTERNAL_ERROR", "Internal server error", {}


def create_request_handler(*, config, fetch_impl=None, logger=None):
    log = logger or logging.getLogger("happyoyster-sdk-demo")

    class RequestHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _dispatch(self):
            started_at = time.monotonic()
            self._status_code = None
            try:
                route_request(self, config=config, fetch_impl=fetch_impl)
            except Exception as error:  # noqa: BLE001 - centralized error boundary
                log.error("request failed: %r", error)
                try:
                    code, message, data = _to_error_payload(error)
                    send_gateway_error(self, code, message, data)
                except Exception:
                    # The response has already been partially written, so close the connection instead of sending an unstable error envelope.
                    self.close_connection = True
            finally:
                latency_ms = round((time.monotonic() - started_at) * 1000)
                log.info(
                    "%s %s %s %sms",
                    self.command,
                    self.path,
                    self._status_code if self._status_code is not None else "-",
                    latency_ms,
                )

        # Capture status codes for access logs and suppress BaseHTTPRequestHandler default logs.
        def log_request(self, code="-", size="-"):
            self._status_code = code

        def log_error(self, format, *args):  # noqa: A002 - base class signature
            log.error(format, *args)

        def log_message(self, format, *args):  # noqa: A002 - base class signature
            pass

    for method in HANDLED_METHODS:
        setattr(RequestHandler, f"do_{method}", RequestHandler._dispatch)

    return RequestHandler
