"""Handle temporary API Key issuance requests and TTL validation."""

import json
from urllib.parse import parse_qs

from ...lib.http_utils import TEXT_CONTENT_TYPE, send_body, send_json
from ...lib.request_body import read_request_body
from .token_service import normalize_expire_in_seconds, request_temporary_api_key


def _parse_json_body(raw_body):
    if not raw_body:
        return {}

    try:
        parsed = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("request body must be valid JSON") from None
    if not isinstance(parsed, dict):
        raise ValueError("request body must be a JSON object")
    return parsed


def _pick_expire_in_seconds(url, body):
    query_value = parse_qs(url.query).get("expire_in_seconds", [None])[0]
    if query_value is not None:
        return query_value
    if body.get("expire_in_seconds") is not None:
        return body["expire_in_seconds"]
    return body.get("expireInSeconds")


def handle_temporary_api_key(handler, *, config, fetch_impl, url):
    try:
        body = _parse_json_body(read_request_body(handler))
        expire_in_seconds = normalize_expire_in_seconds(_pick_expire_in_seconds(url, body))
    except ValueError as error:
        send_json(
            handler,
            400,
            {
                "success": False,
                "errorCode": "PARAM_INVALID",
                "message": str(error),
            },
        )
        return

    upstream = request_temporary_api_key(
        expire_in_seconds=expire_in_seconds,
        config=config,
        fetch_impl=fetch_impl,
    )

    send_body(
        handler,
        upstream.status_code,
        upstream.body,
        content_type=upstream.content_type or TEXT_CONTENT_TYPE,
    )
