"""Dispatch /server-api/*, 404, and 405 routes, mapping them to upstream /openapi/v1/* paths."""

from urllib.parse import urlsplit

from .lib.http_utils import method_not_allowed, not_found
from .modules.proxy.proxy_controller import handle_proxy
from .modules.tokens.token_controller import handle_temporary_api_key

SERVER_API_ROUTES = {
    ("GET", "/server-api/worlds"): "/openapi/v1/worlds",
    ("POST", "/server-api/worlds"): "/openapi/v1/worlds",
    ("GET", "/server-api/worlds/build-status"): "/openapi/v1/worlds/build-status",
    ("GET", "/server-api/worlds/detail"): "/openapi/v1/worlds/detail",
    ("POST", "/server-api/worlds/delete"): "/openapi/v1/worlds/delete",
    ("POST", "/server-api/travel-credential"): "/openapi/v1/worlds/get-travel-credential",
    ("GET", "/server-api/travels"): "/openapi/v1/travels",
    ("GET", "/server-api/travels/artifacts"): "/openapi/v1/travels/artifacts",
    ("POST", "/server-api/travels/update-script"): "/openapi/v1/travels/update-script",
}

SERVER_API_PATHS = {path for _, path in SERVER_API_ROUTES} | {"/server-api/temp-api-key"}


def route_request(handler, *, config, fetch_impl):
    url = urlsplit(handler.path)
    upstream_path = SERVER_API_ROUTES.get((handler.command, url.path))

    if handler.command == "POST" and url.path == "/server-api/temp-api-key":
        handle_temporary_api_key(handler, config=config, fetch_impl=fetch_impl, url=url)
        return

    if upstream_path:
        handle_proxy(
            handler,
            config=config,
            fetch_impl=fetch_impl,
            url=url,
            upstream_path=upstream_path,
        )
        return

    if url.path in SERVER_API_PATHS:
        method_not_allowed(handler)
        return

    not_found(handler)
