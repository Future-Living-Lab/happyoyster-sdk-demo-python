"""Use the main API Key to call Bailian POST /api/v1/tokens and issue a temporary API Key."""

from urllib.parse import quote

from ...lib.upstream_client import fetch_upstream
from ..providers.bailian_app_provider import FALLBACK_USER_AGENT

_EXPIRE_ERROR = "expire_in_seconds must be an integer between 1 and 1800"


def normalize_expire_in_seconds(value):
    if value is None or value == "":
        return None

    if isinstance(value, bool):
        raise ValueError(_EXPIRE_ERROR)
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, float):
        if not value.is_integer():
            raise ValueError(_EXPIRE_ERROR)
        parsed = int(value)
    elif isinstance(value, str):
        try:
            parsed = int(value)
        except ValueError:
            raise ValueError(_EXPIRE_ERROR) from None
    else:
        raise ValueError(_EXPIRE_ERROR)

    if not 1 <= parsed <= 1800:
        raise ValueError(_EXPIRE_ERROR)
    return parsed


def _create_token_search(expire_in_seconds):
    if expire_in_seconds is None:
        return ""
    return f"?expire_in_seconds={quote(str(expire_in_seconds), safe='')}"


def request_temporary_api_key(*, expire_in_seconds, config, fetch_impl=None):
    return fetch_upstream(
        origin=config.bailian_api_origin,
        path="/api/v1/tokens",
        search=_create_token_search(expire_in_seconds),
        method="POST",
        headers={
            "authorization": f"Bearer {config.dashscope_api_key}",
            "user-agent": FALLBACK_USER_AGENT,
        },
        timeout_ms=config.request_timeout_ms,
        fetch_impl=fetch_impl,
    )
