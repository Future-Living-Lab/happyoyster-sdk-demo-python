"""Environment loading, defaults, and basic validation."""

import os
import re
from dataclasses import dataclass
from typing import Mapping

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 3000
DEFAULT_REQUEST_TIMEOUT_MS = 130_000
APP_IDS = {
    1: "happyoyster-1.0-adventure",
    2: "happyoyster-1.0-directing",
    3: "happyoyster-1.0-acting",
}
API_HOST_PATTERN = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$",
    re.I,
)


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    bailian_gateway_base_urls_by_mode: Mapping[int, str]
    bailian_api_origin: str
    dashscope_api_key: str
    request_timeout_ms: int


def _parse_positive_int(name, value, fallback):
    if value is None or value == "":
        return fallback
    try:
        parsed = int(str(value))
    except ValueError:
        raise ValueError(f"{name} must be a positive integer") from None
    if parsed <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return parsed


def _require_non_blank(name, value):
    if value is None or str(value).strip() == "":
        raise ValueError(f"{name} is required")
    return str(value).strip()


def _normalize_api_host(name, api_host):
    if not API_HOST_PATTERN.fullmatch(api_host):
        raise ValueError(
            f"{name} must be a valid Bailian API Host, e.g. "
            "llm-<your-workspace-id>.cn-beijing.maas.aliyuncs.com"
        )
    return api_host, f"https://{api_host}"


def load_env(env=None):
    if env is None:
        env = os.environ

    bailian_api_host, bailian_api_origin = _normalize_api_host(
        "BAILIAN_API_HOST",
        _require_non_blank("BAILIAN_API_HOST", env.get("BAILIAN_API_HOST")),
    )
    dashscope_api_key = _require_non_blank(
        "DASHSCOPE_API_KEY", env.get("DASHSCOPE_API_KEY")
    )

    return Config(
        host=env.get("HOST") or DEFAULT_HOST,
        port=_parse_positive_int("PORT", env.get("PORT"), DEFAULT_PORT),
        bailian_gateway_base_urls_by_mode={
            mode: f"https://{bailian_api_host}/api/v2/apps/{app_id}"
            for mode, app_id in APP_IDS.items()
        },
        bailian_api_origin=bailian_api_origin,
        dashscope_api_key=dashscope_api_key,
        request_timeout_ms=_parse_positive_int(
            "REQUEST_TIMEOUT_MS",
            env.get("REQUEST_TIMEOUT_MS"),
            DEFAULT_REQUEST_TIMEOUT_MS,
        ),
    )
