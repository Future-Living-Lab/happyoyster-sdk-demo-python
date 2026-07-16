"""Forwarded-header filtering for hop-by-hop and internal gateway-injected headers."""

HOP_BY_HOP_HEADERS = {
    "connection",
    "content-length",
    "host",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


def _is_internal_gateway_header(name):
    return name.startswith("x-dashscope-") or name.startswith("x-ho-")


def copy_forwardable_headers(headers):
    result = {}

    for name, value in headers.items():
        lower_name = name.lower()
        if value is None or value == "":
            continue
        if lower_name in HOP_BY_HOP_HEADERS:
            continue
        if _is_internal_gateway_header(lower_name):
            continue
        if lower_name in result:
            result[lower_name] = f"{result[lower_name]}, {value}"
        else:
            result[lower_name] = str(value)

    return result
